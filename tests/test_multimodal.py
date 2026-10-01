from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from ml.multimodal import DemographicPreprocessor, MultimodalClassifier, feature_names
from scripts.train_longitudinal_model import SubjectRecord, stratified_split, write_manifest
from scripts.train_multimodal_model import (
    choose_validation_threshold,
    load_saved_split,
    metric_summary,
    train_epoch,
    validate_volume,
)


def demographic_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Age": [60, 70, 80],
            "EDUC": [10, 12, 16],
            "SES": [1, np.nan, 3],
            "MMSE": [28, 25, 22],
            "eTIV": [1400, 1500, 1600],
            "nWBV": [0.8, 0.7, 0.6],
            "ASF": [1, 1.1, 1.2],
            "MR Delay": [0, 300, 900],
            "Visit": [1, 2, 3],
            "M/F": ["M", "F", "F"],
            "Hand": ["R", "R", "R"],
            "CDR": [0, 0.5, 1],
            "Group": ["Nondemented", "Converted", "Demented"],
            "Subject ID": ["s1"] * 3,
            "MRI ID": ["v1", "v2", "v3"],
        }
    )


def test_preprocessing_uses_only_training_statistics_and_roundtrips():
    training = demographic_frame()
    processor = DemographicPreprocessor.fit(training)
    heldout = training.copy()
    heldout["Age"] = 999
    before = processor.to_dict()
    processor.transform(heldout)
    assert processor.to_dict() == before
    assert processor.means[0] == 70
    result = processor.transform(training)
    names = feature_names()
    assert result[1, names.index("SES")] == pytest.approx(0)
    assert result[1, names.index("missing_SES")] == 1
    restored = DemographicPreprocessor.from_dict(before)
    np.testing.assert_array_equal(restored.transform(training), result)


def test_target_fields_and_identifiers_never_enter_features():
    frame = demographic_frame()
    processor = DemographicPreprocessor.fit(frame)
    changed = frame.copy()
    for name in ("CDR", "Group", "Subject ID", "MRI ID"):
        changed[name] = "different-label-or-identifier"
    np.testing.assert_array_equal(processor.transform(frame), processor.transform(changed))
    assert not set(("CDR", "Group", "Subject ID", "MRI ID")) & set(feature_names())
    assert "Visit" in feature_names()


def test_all_missing_constant_and_unknown_categories_are_explicit():
    frame = demographic_frame()
    frame["SES"] = np.nan
    frame["Age"] = 65
    processor = DemographicPreprocessor.fit(frame)
    frame.loc[0, "M/F"] = np.nan
    frame.loc[1, "Hand"] = "unknown"
    result = processor.transform(frame)
    assert np.isfinite(result).all()
    names = feature_names()
    assert result[0, names.index("M/F_missing")] == 1
    assert result[1, names.index("Hand_other")] == 1
    assert (result[:, names.index("missing_SES")] == 1).all()


@pytest.mark.parametrize("value", [float("inf"), "malformed"])
def test_invalid_measurements_fail_instead_of_becoming_missing(value):
    frame = demographic_frame().astype({"Age": object})
    frame.loc[0, "Age"] = value
    with pytest.raises((ValueError, TypeError)):
        DemographicPreprocessor.fit(frame)


def test_saved_split_rejects_subject_leakage_missing_visits_and_label_changes(tmp_path: Path):
    records = []
    for index in range(56):
        target = int(index < 10)
        visits = tuple(
            (f"v{index}_{step}", step * 100, Path("unused.hdr"), float(target * step)) for step in range(3)
        )
        records.append(SubjectRecord(f"s{index:03d}", visits, target))
    path = tmp_path / "split.csv"
    write_manifest(stratified_split(records), path)
    original = pd.read_csv(path)
    split = load_saved_split(records, path)
    assert {name: len(items) for name, items in split.items()} == {"train": 40, "validation": 8, "test": 8}
    for kind in ("leakage", "missing", "changed_label"):
        changed = original.copy()
        if kind == "leakage":
            changed.loc[0, "split"] = "train" if changed.loc[0, "split"] != "train" else "test"
        elif kind == "missing":
            changed = changed.iloc[1:]
        else:
            changed.loc[0, "cdr"] += 0.5
        changed.to_csv(path, index=False)
        with pytest.raises(ValueError):
            load_saved_split(records, path)


def test_padding_cannot_change_predictions_and_both_modalities_have_gradients():
    torch.manual_seed(17)
    torch.set_num_threads(2)
    model = MultimodalClassifier()
    volumes = torch.rand(2, 3, 1, 16, 16, 16, requires_grad=True)
    demos = torch.rand(2, 3, len(feature_names()), requires_grad=True)
    lengths = torch.tensor([1, 3])
    model.eval()
    logits = model(volumes, demos, lengths)
    changed_volumes, changed_demos = volumes.detach().clone(), demos.detach().clone()
    changed_volumes[0, 1:] = 999
    changed_demos[0, 1:] = -999
    torch.testing.assert_close(model(changed_volumes, changed_demos, lengths), logits)
    logits.sum().backward()
    assert volumes.grad[0, 1:].count_nonzero() == 0
    assert demos.grad[0, 1:].count_nonzero() == 0
    for branch in (model.encoder, model.demographics, model.lstm, model.head):
        assert sum(float(parameter.grad.abs().sum()) for parameter in branch.parameters()) > 0


def test_minibatches_update_weights_and_include_every_subject_and_visit():
    torch.manual_seed(5)
    records, cache, demos = [], {}, {}
    for index in range(3):
        visit_id = f"v{index}"
        records.append(SubjectRecord(f"s{index}", ((visit_id, 0, Path("unused"), 0.0),), index % 2))
        cache[visit_id] = np.random.default_rng(index).random((64, 64, 64), dtype=np.float32)
        demos[visit_id] = np.ones(len(feature_names()), dtype=np.float32) * (index + 1)
    model = MultimodalClassifier()
    before = model.encoder.layers[0].weight.detach().clone()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    row = train_epoch(model, optimizer, torch.nn.BCEWithLogitsLoss(), records, cache, demos, 2, 23)
    assert sorted(row["subject_ids_seen"]) == ["s0", "s1", "s2"]
    assert row["optimizer_steps"] == 2
    assert row["training_visits_seen"] == 3
    assert not torch.equal(before, model.encoder.layers[0].weight)


def test_metrics_and_validation_threshold_with_known_rankings():
    good = metric_summary([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    assert good["roc_auc"] == good["f1"] == good["balanced_accuracy"] == 1
    majority = metric_summary([0, 0, 0, 1], [0.1] * 4)
    assert majority["accuracy"] == 0.75
    assert majority["sensitivity_recall"] == 0
    assert majority["balanced_accuracy"] == majority["roc_auc"] == 0.5
    assert metric_summary([0, 1], [0.5, 0.5])["roc_auc"] == 0.5
    threshold = choose_validation_threshold([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4])
    assert threshold == 0.3


def test_invalid_cache_is_rejected():
    with pytest.raises(ValueError):
        validate_volume(np.zeros((64, 64, 64), dtype=np.float32))
    with pytest.raises(ValueError):
        validate_volume(np.ones((8, 8, 8), dtype=np.float32))
