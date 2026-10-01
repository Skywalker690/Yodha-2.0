"""Evaluate the saved longitudinal checkpoint on the untouched subject split."""

from __future__ import annotations

import json
from pathlib import Path

import torch

from scripts.train_longitudinal_model import (
    SEED,
    LongitudinalClassifier,
    batch_records,
    cache_volumes,
    load_subjects,
    stratified_split,
)


def roc_auc(targets: list[int], probabilities: list[float]) -> float | None:
    positives = [score for target, score in zip(targets, probabilities) if target == 1]
    negatives = [score for target, score in zip(targets, probabilities) if target == 0]
    if not positives or not negatives:
        return None
    wins = sum(score > negative for score in positives for negative in negatives)
    ties = sum(score == negative for score in positives for negative in negatives)
    return float((wins + 0.5 * ties) / (len(positives) * len(negatives)))


def summarize(targets: list[int], probabilities: list[float], threshold: float = 0.5) -> dict:
    predictions = [int(probability >= threshold) for probability in probabilities]
    tp = sum(target == 1 and prediction == 1 for target, prediction in zip(targets, predictions))
    tn = sum(target == 0 and prediction == 0 for target, prediction in zip(targets, predictions))
    fp = sum(target == 0 and prediction == 1 for target, prediction in zip(targets, predictions))
    fn = sum(target == 1 and prediction == 0 for target, prediction in zip(targets, predictions))
    sensitivity = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    precision = tp / (tp + fp) if tp + fp else None
    balanced = (sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None
    return {
        "subjects": len(targets),
        "positive_subjects": sum(targets),
        "threshold": threshold,
        "confusion_matrix": {"true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn},
        "accuracy": (tp + tn) / len(targets) if targets else None,
        "precision": precision,
        "sensitivity_recall": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": balanced,
        "roc_auc": roc_auc(targets, probabilities),
        "probabilities": probabilities,
        "targets": targets,
    }


def main() -> None:
    output_dir = Path("data/training")
    records = load_subjects(Path("dataset/oasis_longitudinal_demographics-8d83e569fa2e2d30.xlsx"), Path("dataset"))
    split = stratified_split(records)
    cache = cache_volumes(records, output_dir / "volume_cache")
    checkpoint = torch.load(output_dir / "longitudinal_model.pt", map_location="cpu", weights_only=False)
    model = LongitudinalClassifier()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    with torch.no_grad():
        volumes, lengths, target_tensor = batch_records(split["test"], cache)
        probabilities = torch.sigmoid(model(volumes, lengths)).tolist()
    targets = target_tensor.int().tolist()
    baseline = summarize(targets, [0.0] * len(targets))
    result = {
        "seed": SEED,
        "checkpoint_epoch": checkpoint["best_epoch"],
        "target": checkpoint["target"],
        "architecture": checkpoint["architecture"],
        "split": {"train": 40, "validation": 8, "test": 8},
        "trained_model": summarize(targets, probabilities),
        "majority_class_baseline": baseline,
        "interpretation": "Research-only evaluation on eight held-out subjects; not clinical validation.",
    }
    (output_dir / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
