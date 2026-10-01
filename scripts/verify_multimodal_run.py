"""Read-only audit of a completed multimodal run against raw sources and saved artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ml.data import read_metadata
from ml.multimodal import DemographicPreprocessor, MultimodalClassifier, feature_names
from scripts.train_longitudinal_model import SEED, load_subjects
from scripts.train_multimodal_model import (
    cache_verified_volumes,
    choose_validation_threshold,
    load_saved_split,
    predict,
    sha256_file,
)


def verify_run(run_dir: Path, metadata: Path, root: Path, cache_dir: Path) -> dict:
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
    source_audit = json.loads((run_dir / "mri_sources.json").read_text(encoding="utf-8"))
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed":
        raise ValueError("Run did not complete")
    if sha256_file(metadata) != provenance["metadata_sha256"]:
        raise ValueError("Source workbook has changed")
    manifest = run_dir / "subject_split.csv"
    if sha256_file(manifest) != provenance["split_sha256"]:
        raise ValueError("Saved split manifest has changed")
    split = load_saved_split(load_subjects(metadata, root), manifest)
    training_ids = {record.subject_id for record in split["train"]}
    if set(provenance["preprocessing_fit_subject_ids"]) != training_ids:
        raise ValueError("Demographic preprocessing fitted on the wrong subjects")
    training_visits = sum(len(record.visits) for record in split["train"])
    if provenance["preprocessing_fit_visits"] != training_visits:
        raise ValueError("Preprocessing omitted training visits")
    if len(history) != metrics["epochs_completed"]:
        raise ValueError("Epoch history is incomplete")
    for index, row in enumerate(history, 1):
        if row["epoch"] != index or len(row["subject_ids_seen"]) != 40:
            raise ValueError("Epoch subject coverage is incomplete")
        if set(row["subject_ids_seen"]) != training_ids or row["training_visits_seen"] != training_visits:
            raise ValueError("Wrong subjects or missing visits in training coverage")
    expected_best = min(history, key=lambda row: row["weighted_validation_loss"])["epoch"]
    if expected_best != metrics["best_epoch"]:
        raise ValueError("Selected epoch disagrees with validation history")
    if sum(row["optimizer_steps"] for row in history) != metrics["optimizer_steps"]:
        raise ValueError("Optimizer step count does not match history")
    frame = read_metadata(metadata)
    visit_ids = {visit[0] for items in split.values() for record in items for visit in record.visits}
    frame = frame[frame["MRI ID"].isin(visit_ids)]
    fitted = DemographicPreprocessor.fit(frame[frame["Subject ID"].isin(training_ids)])
    if fitted.to_dict() != provenance["demographic_preprocessor"]:
        raise ValueError("Serialized statistics do not equal training-only statistics")
    checkpoint = torch.load(run_dir / "multimodal_model.pt", map_location="cpu", weights_only=True)
    if checkpoint["best_epoch"] != expected_best or checkpoint["feature_names"] != feature_names():
        raise ValueError("Checkpoint schema/epoch does not match artifacts")
    if checkpoint["demographic_preprocessor"] != fitted.to_dict():
        raise ValueError("Checkpoint contains wrong demographic statistics")
    batch_size = provenance["training_config"]["batch_size"]
    torch.set_num_threads(provenance["training_config"]["cpu_threads"])
    restored = DemographicPreprocessor.from_dict(checkpoint["demographic_preprocessor"])
    demographics = dict(zip(frame["MRI ID"], restored.transform(frame)))
    records = [record for items in split.values() for record in items]
    # Every source hash is compared again, confirming the MRI pairs are unchanged.
    cache, current_sources = cache_verified_volumes(records, cache_dir, root)
    by_visit = {row["visit_id"]: row for row in source_audit}
    if by_visit != {row["visit_id"]: row for row in current_sources}:
        raise ValueError("Raw MRI or cache provenance changed")
    model = MultimodalClassifier()
    model.load_state_dict(checkpoint["model_state_dict"])
    predictions = pd.read_csv(run_dir / "predictions.csv")
    validation_targets, validation_scores = predict(
        model, split["validation"], cache, demographics, batch_size
    )
    expected_threshold = choose_validation_threshold(validation_targets, validation_scores)
    if expected_threshold != checkpoint["decision_threshold"]:
        raise ValueError("Decision threshold is not reproduced from validation data")
    for name, items in split.items():
        targets, scores = predict(model, items, cache, demographics, batch_size)
        saved = predictions[predictions["split"] == name]
        if saved["subject_id"].tolist() != [record.subject_id for record in items]:
            raise ValueError("Prediction subjects do not match the frozen split")
        np.testing.assert_array_equal(saved["target"].to_numpy(), targets)
        np.testing.assert_allclose(saved["model_score"].to_numpy(), scores, atol=1e-12, rtol=0)
        np.testing.assert_array_equal(metrics["evaluation"][name]["at_0.5"]["probabilities"], scores)
    torch.manual_seed(SEED)
    initial = MultimodalClassifier().state_dict()
    branch_changes = {
        branch: float(
            sum(
                torch.sum((value - initial[name]) ** 2).item()
                for name, value in model.state_dict().items()
                if name.startswith(branch + ".")
            )
            ** 0.5
        )
        for branch in ("encoder", "demographics", "lstm", "head")
    }
    if any(change <= 0 for change in branch_changes.values()):
        raise ValueError("A trainable branch was not trained")
    for branch, change in branch_changes.items():
        if not np.isclose(change, metrics["trainable_branch_weight_changes_l2"][branch]):
            raise ValueError("Weight-change audit does not reproduce")
    return {
        "status": "passed",
        "training_subjects": len(training_ids),
        "training_visits": training_visits,
        "epochs_audited": len(history),
        "optimizer_updates": metrics["optimizer_steps"],
        "raw_mri_pairs_verified": len(current_sources),
        "reproduced_subject_predictions": len(predictions),
        "demographic_features": len(feature_names()),
        "branch_weight_changes_l2": branch_changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument(
        "--metadata", type=Path, default=Path("dataset/oasis_longitudinal_demographics-8d83e569fa2e2d30.xlsx")
    )
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset"))
    parser.add_argument(
        "--cache-dir", type=Path, default=Path("data/training_multimodal/verified_volume_cache")
    )
    args = parser.parse_args()
    print(json.dumps(verify_run(args.run_dir, args.metadata, args.dataset_root, args.cache_dir), indent=2))


if __name__ == "__main__":
    main()
