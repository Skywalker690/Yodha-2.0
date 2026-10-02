"""Feature/reference leakage and checkpoint compatibility regressions."""

import copy
import json

import numpy as np
import pytest
import torch

from ml.anatomy.features import VERSION, fit_reference, validate_reference_split, z_score
from ml.anatomy.forecasting import load_models
from ml.anatomy.model import FeatureScaler
from ml.anatomy.structural import RegularizedMixedEffects, StructuralExample, history_features
from tests.test_anatomy import measured


def histories(count=12):
    result = {}
    for index in range(count):
        visits = [measured(0), measured(200, value=3900), measured(800, value=3700)]
        for visit in visits:
            visit.observed_metadata.update(Age=72.0, nWBV=0.72 + index * 0.002, Visit=1.0, CDR=0.0, MMSE=25.0)
        result[f"train{index}"] = visits
    return result


def test_reference_uses_training_baselines_without_ten_subject_cutoff():
    training = histories(3)
    split = dict.fromkeys(training, "train")
    profile = fit_reference(training, split)
    assert profile["reference_subjects"] == 3
    assert profile["bins"][2]["n"] == 3
    assert profile["heldout_reference_overlap_possible"] is False
    visit = training["train0"][-1]
    expected = (visit.observed_metadata["nWBV"] - profile["bins"][2]["mean"]) / profile["bins"][2][
        "sample_std"
    ]
    assert z_score(visit, profile)["z_score"] == pytest.approx(expected)
    visit.observed_metadata.update(CDR=2.0, nWBV=0.9, EDUC=99.0, SES=99.0)
    assert fit_reference(training, split) == profile  # Later data never fit reference.
    with pytest.raises(ValueError, match="held-out"):
        fit_reference(training, {**split, "train1": "test"})
    with pytest.raises(ValueError, match="held-out"):
        validate_reference_split(profile, {**split, "train1": "test"})
    training["train2"][0].observed_metadata["CDR"] = 1.0
    assert fit_reference(training, split)["reference_subjects"] == 2


def test_unavailable_score_never_uses_raw_nwbv_and_extra_demographics_are_inert():
    training = histories(2)
    profile = fit_reference(training, dict.fromkeys(training, "train"))
    history = training["train0"][:2]
    history[-1].observed_metadata["Age"] = 62
    first, names = history_features(history, 731, False, reference=profile)
    assert np.isnan(first[names.index("nwbv_age_z")])
    assert z_score(history[-1], profile)["status"] == "insufficient_reference"
    assert not set(names) & {
        "Age",
        "nWBV",
        "EDUC",
        "SES",
        "sex_F0_M1",
        "hand_R0_L1",
        "eTIV",
        "ASF",
        "CDR",
        "Group",
    }
    assert first[names.index("elapsed_scan_days_1_most_recent_first")] == 200
    for visit in history:
        visit.observed_metadata.update(
            EDUC=99.0, SES=99.0, eTIV=999.0, ASF=999.0, **{"M/F": "M", "Hand": "L"}
        )
    second, _ = history_features(history, 731, False, reference=profile)
    np.testing.assert_equal(first, second)
    scaler = FeatureScaler.fit(np.stack([first, second]))
    assert scaler.transform(first)[len(names) + names.index("nwbv_age_z")] == 1
    assert scaler.transform(first)[names.index("nwbv_age_z")] == 0
    history[-1].observed_metadata["Age"] = 99
    assert z_score(history[-1], profile)["status"] == "unsupported_age"
    history[-1].observed_metadata["nWBV"] = -1.0
    assert z_score(history[-1], profile)["status"] == "invalid_input"


def test_singleton_and_zero_spread_remain_unavailable():
    training = histories(2)
    split = dict.fromkeys(training, "train")
    training["train1"][0].observed_metadata["nWBV"] = training["train0"][0].observed_metadata["nWBV"]
    profile = fit_reference(training, split)
    result = z_score(training["train0"][-1], profile)
    assert result["status"] == "invalid_reference_spread" and result["z_score"] is None
    assert result["reference_bin"]["n"] == 2 and result["reference_bin"]["sample_std_fraction"] == 0
    singleton = fit_reference({"train0": training["train0"]}, split)
    assert z_score(training["train0"][-1], singleton)["status"] == "insufficient_reference"


def test_reference_and_inputs_roundtrip_reject_older_checkpoints(tmp_path):
    training = histories()
    split = dict.fromkeys(training, "train")
    examples = [StructuralExample(subject, visits[:2], visits[-1]) for subject, visits in training.items()]
    model = RegularizedMixedEffects().fit(examples, split)
    saved = model.to_dict()
    restored = RegularizedMixedEffects.from_dict(saved)
    assert saved["feature_contract"] == VERSION
    assert restored.predict("new", training["train0"][:2], 600) == model.predict(
        "new", training["train0"][:2], 600
    )
    old = copy.deepcopy(saved)
    del old["feature_contract"]
    with pytest.raises(ValueError, match="older structural checkpoint"):
        RegularizedMixedEffects.from_dict(old)
    torch.save({"version": "conditioned-pull-cnn-v1"}, tmp_path / "with_scores.pt")
    with pytest.raises(ValueError, match="older.*spatial checkpoint"):
        load_models(tmp_path)


def test_training_cli_binds_the_explicit_frozen_reference(tmp_path, monkeypatch):
    import sys
    from ml.anatomy import training as implementation
    from scripts.train_anatomy import main

    subjects = histories(3)
    profile = fit_reference(subjects, dict.fromkeys(subjects, "train"))
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps(profile))
    called = {}

    def capture(*args, **kwargs):
        called.update(kwargs)
        return {"release_failures": []}

    monkeypatch.setattr(implementation, "train", capture)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train_anatomy",
            "train",
            "--study",
            str(tmp_path / "study.json"),
            "--run",
            str(tmp_path / "candidate"),
            "--reference",
            str(reference),
            "--allow-partial-cohort",
        ],
    )
    main()
    assert called["reference"] == profile and called["allow_partial_cohort"] is True
