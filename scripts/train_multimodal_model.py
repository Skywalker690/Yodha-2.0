"""Audited, bounded-memory MRI + demographic retraining on the saved subject split."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from ml.data import read_metadata
from ml.multimodal import (
    EXCLUDED_FEATURES,
    MODEL_VERSION,
    DemographicPreprocessor,
    MultimodalClassifier,
    feature_names,
)
from ml.preprocessing import STANDARD_SHAPE, prepare
from scripts.evaluate_longitudinal_model import summarize
from scripts.train_longitudinal_model import SEED, SubjectRecord, batch_records, load_subjects

SPLIT_SIZES = {"train": 40, "validation": 8, "test": 8}
PREPROCESSING = {
    "version": "canonical-percentile-resize-64-v1",
    "shape": list(STANDARD_SHAPE),
    "orientation": "RAS",
    "percentiles": [1, 99.5],
    "resize": "trilinear-align_corners_false",
    "registered": False,
}
LIMITATIONS = [
    "Research experiment; no clinical validation.",
    "Target is retrospective first-to-last observed CDR increase, using all available visits.",
    "Endpoint MRI/MMSE/brain-volume measurements are available to this model; it is not a future-risk forecast.",
    "Only six positive training subjects and two positives per holdout; estimates are very uncertain.",
    "The test cohort was evaluated in earlier experiments and is a reused holdout, not independent validation.",
    "Class-weighted sigmoid scores are uncalibrated model scores, not disease probabilities.",
    "64-cube shape normalization is not anatomical registration or hippocampus segmentation.",
]


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_saved_split(records: list[SubjectRecord], manifest_path: Path) -> dict[str, list[SubjectRecord]]:
    """Verify assignments, target, ordering and complete visit coverage against the frozen CSV."""
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "visit_id", "visit_index", "days_from_baseline", "target", "split", "cdr"}
    if not required.issubset(manifest.columns) or manifest[list(required)].isna().any().any():
        raise ValueError("Saved subject manifest is missing required fields/values")
    if manifest["visit_id"].duplicated().any():
        raise ValueError("Duplicate MRI visit in subject manifest")
    if (manifest.groupby("subject_id")["split"].nunique() != 1).any():
        raise ValueError("Subject leakage across splits")
    if not set(manifest["split"]).issubset(SPLIT_SIZES):
        raise ValueError("Unknown subject split")
    expected_records = {record.subject_id: record for record in records}
    if len(expected_records) != len(records) or set(manifest["subject_id"]) != set(expected_records):
        raise ValueError("Saved manifest and eligible subject cohort differ")
    split: dict[str, list[SubjectRecord]] = {name: [] for name in SPLIT_SIZES}
    for subject_id, rows in manifest.groupby("subject_id", sort=True):
        record = expected_records[subject_id]
        rows = rows.sort_values("days_from_baseline")
        if rows["visit_id"].tolist() != [visit[0] for visit in record.visits]:
            raise ValueError(f"Incomplete or reordered visits for {subject_id}")
        if rows["visit_index"].tolist() != list(range(len(record.visits))):
            raise ValueError(f"Invalid visit sequence index for {subject_id}")
        if rows["days_from_baseline"].tolist() != [visit[1] for visit in record.visits]:
            raise ValueError(f"Changed visit chronology for {subject_id}")
        if any(b[1] <= a[1] for a, b in zip(record.visits, record.visits[1:])):
            raise ValueError(f"Duplicate or invalid scan dates for {subject_id}")
        if rows["cdr"].tolist() != [visit[3] for visit in record.visits]:
            raise ValueError(f"CDR labels changed for {subject_id}")
        if set(rows["target"]) != {record.target}:
            raise ValueError(f"Invalid target for {subject_id}")
        split[rows.iloc[0]["split"]].append(record)
    for name, items in split.items():
        if len(items) != SPLIT_SIZES[name] or {item.target for item in items} != {0, 1}:
            raise ValueError(f"Invalid size or class coverage for {name}")
    return split


def validate_volume(volume: np.ndarray) -> None:
    if volume.shape != STANDARD_SHAPE or volume.dtype != np.float32:
        raise ValueError("Training cache must contain float32 64-cube volumes")
    if not np.isfinite(volume).all() or volume.min() < 0 or volume.max() > 1 or np.ptp(volume) <= 0:
        raise ValueError("Training volume must be finite, varied and bounded to [0,1]")


def cache_verified_volumes(
    records: list[SubjectRecord],
    cache_dir: Path,
    dataset_root: Path,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache, sources = {}, []
    root = dataset_root.resolve()
    visits = [visit for record in records for visit in record.visits]
    for index, (visit_id, _, path, _) in enumerate(visits, 1):
        paths = [path.resolve(), path.with_suffix(".img").resolve()]
        if any(not source.is_relative_to(root) or not source.is_file() for source in paths):
            raise ValueError(f"MRI pair must exist inside dataset root: {visit_id}")
        fingerprints = {str(source.relative_to(root)): sha256_file(source) for source in paths}
        signature = hashlib.sha256(
            json.dumps(
                {"source": fingerprints, "preprocessing": PREPROCESSING},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        cached_path = cache_dir / f"{signature}.npy"
        if cached_path.exists():
            volume = np.load(cached_path, allow_pickle=False)
        else:
            volume = prepare(path, allow_pair=True).volume.astype(np.float32)
            validate_volume(volume)
            np.save(cached_path, volume, allow_pickle=False)
        validate_volume(volume)
        cache[visit_id] = volume
        sources.append({"visit_id": visit_id, "source_sha256": fingerprints, "cache_key": signature})
        if index % 20 == 0 or index == len(visits):
            print(f"Verified MRI cache: {index}/{len(visits)}", flush=True)
    return cache, sources


def multimodal_batch(
    records: list[SubjectRecord],
    cache: dict[str, np.ndarray],
    demos: dict[str, np.ndarray],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    volumes, lengths, targets = batch_records(records, cache)
    demographics = np.zeros((len(records), volumes.shape[1], len(feature_names())), dtype=np.float32)
    for row, record in enumerate(records):
        for column, (visit_id, _, _, _) in enumerate(record.visits):
            demographics[row, column] = demos[visit_id]
    return volumes, torch.from_numpy(demographics), lengths, targets


def metric_summary(targets: list[int], scores: list[float], threshold: float = 0.5) -> dict[str, Any]:
    result = summarize(targets, scores, threshold)
    cm = result["confusion_matrix"]
    denominator = 2 * cm["true_positive"] + cm["false_positive"] + cm["false_negative"]
    result["f1"] = 2 * cm["true_positive"] / denominator if denominator else None
    probabilities = np.clip(np.asarray(scores), 1e-7, 1 - 1e-7)
    labels = np.asarray(targets)
    result["brier_score"] = float(np.mean((probabilities - labels) ** 2))
    result["binary_cross_entropy"] = float(
        np.mean(
            -labels * np.log(probabilities) - (1 - labels) * np.log(1 - probabilities),
        )
    )
    return result


def choose_validation_threshold(targets: list[int], scores: list[float]) -> float:
    """Maximize validation balanced accuracy; tie-break toward the default 0.5."""
    candidates = {0.0, 0.5, 1.0, *scores}
    return max(
        sorted(candidates),
        key=lambda threshold: (
            metric_summary(targets, scores, threshold)["balanced_accuracy"],
            -abs(threshold - 0.5),
        ),
    )


def predict(
    model: MultimodalClassifier,
    records: list[SubjectRecord],
    cache: dict[str, np.ndarray],
    demos: dict[str, np.ndarray],
    batch_size: int,
) -> tuple[list[int], list[float]]:
    targets, scores = [], []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(records), batch_size):
            volumes, demographics, lengths, labels = multimodal_batch(
                records[start : start + batch_size], cache, demos
            )
            logits = model(volumes, demographics, lengths)
            if not torch.isfinite(logits).all():
                raise RuntimeError("Non-finite model predictions")
            targets.extend(labels.int().tolist())
            scores.extend(logits.sigmoid().tolist())
    return targets, scores


def train_epoch(
    model: MultimodalClassifier,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    records: list[SubjectRecord],
    cache: dict[str, np.ndarray],
    demos: dict[str, np.ndarray],
    batch_size: int,
    seed: int,
) -> dict[str, Any]:
    model.train()
    ordered = records.copy()
    random.Random(seed).shuffle(ordered)
    seen, total_loss, updates = [], 0.0, 0
    for start in range(0, len(ordered), batch_size):
        items = ordered[start : start + batch_size]
        volumes, demographics, lengths, targets = multimodal_batch(items, cache, demos)
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(volumes, demographics, lengths), targets)
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite training loss")
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        total_loss += float(loss.detach()) * len(items)
        seen.extend(record.subject_id for record in items)
        updates += 1
    if len(seen) != len(records) or set(seen) != {record.subject_id for record in records}:
        raise RuntimeError("Epoch did not train on every subject exactly once")
    return {
        "train_loss": total_loss / len(records),
        "optimizer_steps": updates,
        "subject_ids_seen": seen,
        "training_visits_seen": sum(len(record.visits) for record in records),
    }


def save_checkpoint(path: Path, model: nn.Module, extra: dict[str, Any]) -> None:
    temporary = path.with_suffix(".pt.tmp")
    torch.save({"model_state_dict": model.state_dict(), **extra}, temporary)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata", type=Path, default=Path("dataset/oasis_longitudinal_demographics-8d83e569fa2e2d30.xlsx")
    )
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset"))
    parser.add_argument("--split-manifest", type=Path, default=Path("data/training/subject_split.csv"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path("data/training_multimodal/verified_volume_cache")
    )
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--min-epochs", type=int, default=15)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    args = parser.parse_args()
    if min(args.epochs, args.min_epochs, args.patience, args.batch_size, args.threads) < 1:
        parser.error("Epochs, patience, batch size and threads must be positive")
    if args.min_epochs > args.epochs or not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("Minimum epochs must fit the epoch budget and learning rate must be positive/finite")
    started = time.perf_counter()
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(args.threads)
    output_dir = args.output_dir or Path("data/training_multimodal/runs") / datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Use a fresh output directory to preserve previous experiments")
    frame = read_metadata(args.metadata)
    if (frame["CDR"] < 0).any() or not np.isfinite(frame["CDR"].astype(float)).all():
        raise ValueError("CDR target measurements must be finite and nonnegative")
    records = load_subjects(args.metadata, args.dataset_root)
    split = load_saved_split(records, args.split_manifest)
    visit_ids = {visit[0] for record in records for visit in record.visits}
    selected = frame[frame["MRI ID"].isin(visit_ids)].copy()
    if len(selected) != len(visit_ids):
        raise ValueError("MRI/metadata join lost visits")
    training_ids = {record.subject_id for record in split["train"]}
    training_frame = selected[selected["Subject ID"].isin(training_ids)]
    preprocessor = DemographicPreprocessor.fit(training_frame)
    transformed = preprocessor.transform(selected)
    demos = dict(zip(selected["MRI ID"], transformed))
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_manifest = output_dir / "subject_split.csv"
    saved_manifest.write_bytes(args.split_manifest.read_bytes())
    counts = {
        name: {
            "subjects": len(items),
            "visits": sum(len(record.visits) for record in items),
            "positive_subjects": sum(record.target for record in items),
        }
        for name, items in split.items()
    }
    provenance = {
        "model_version": MODEL_VERSION,
        "seed": SEED,
        "target": "observed_cdr_increase",
        "architecture": "SpatialEncoder(32)+demographic-MLP(16)+packed-LSTM(16)",
        "feature_names": feature_names(),
        "excluded_input_fields": list(EXCLUDED_FEATURES),
        "demographic_preprocessor": preprocessor.to_dict(),
        "image_preprocessing": PREPROCESSING,
        "split_sha256": sha256_file(saved_manifest),
        "metadata_sha256": sha256_file(args.metadata),
        "split_counts": counts,
        "preprocessing_fit_subject_ids": sorted(training_ids),
        "preprocessing_fit_visits": len(training_frame),
        "missing_measurements": selected.isna().sum().astype(int).to_dict(),
        "training_config": {
            "maximum_epochs": args.epochs,
            "minimum_epochs": args.min_epochs,
            "patience": args.patience,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": 0.0001,
            "cpu_threads": args.threads,
            "checkpoint_selection": "minimum class-weighted validation BCE",
        },
        "software": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "limitations": LIMITATIONS,
    }
    write_json(output_dir / "provenance.json", provenance)
    write_json(output_dir / "preprocessing.json", preprocessor.to_dict())
    print(
        f"Run directory: {output_dir}\nSplit: {json.dumps(counts)}\nDemographic inputs: {len(feature_names())}",
        flush=True,
    )
    cache, source_provenance = cache_verified_volumes(records, args.cache_dir, args.dataset_root)
    write_json(output_dir / "mri_sources.json", source_provenance)
    torch.set_num_threads(args.threads)  # prepare() uses two threads for individual-volume preprocessing.
    # Importing optional preprocessing libraries must not change model initialization
    # between a cold cache and a reused cache run.
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    model = MultimodalClassifier()
    initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.0001)
    positive_count = counts["train"]["positive_subjects"]
    positive_weight = (len(split["train"]) - positive_count) / positive_count
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(positive_weight))
    best_loss, best_epoch, stale, history = float("inf"), 0, 0, []
    for epoch in range(1, args.epochs + 1):
        epoch_started = time.perf_counter()
        row = train_epoch(
            model, optimizer, criterion, split["train"], cache, demos, args.batch_size, SEED + epoch
        )
        val_targets, val_scores = predict(model, split["validation"], cache, demos, args.batch_size)
        validation = metric_summary(val_targets, val_scores)
        p, y = np.clip(np.asarray(val_scores), 1e-7, 1 - 1e-7), np.asarray(val_targets)
        validation_loss = float(np.mean(-positive_weight * y * np.log(p) - (1 - y) * np.log(1 - p)))
        row.update(
            {
                "epoch": epoch,
                "validation": validation,
                "weighted_validation_loss": validation_loss,
                "seconds": time.perf_counter() - epoch_started,
            }
        )
        history.append(row)
        if validation_loss < best_loss - 1e-5:
            best_loss, best_epoch, stale = validation_loss, epoch, 0
            save_checkpoint(
                output_dir / "multimodal_model.pt",
                model,
                {
                    **provenance,
                    "best_epoch": epoch,
                    "best_weighted_validation_loss": best_loss,
                },
            )
        else:
            stale += 1
        save_checkpoint(
            output_dir / "last_checkpoint.pt",
            model,
            {
                **provenance,
                "epoch": epoch,
                "optimizer_state_dict": optimizer.state_dict(),
                "rng_state": torch.get_rng_state(),
                "best_epoch": best_epoch,
                "stale_epochs": stale,
            },
        )
        write_json(output_dir / "history.json", history)
        print(
            f"epoch={epoch:03d} train_loss={row['train_loss']:.4f} weighted_val={validation_loss:.4f} "
            f"val_auc={validation['roc_auc']:.3f} trained_subjects={len(row['subject_ids_seen'])} "
            f"steps={row['optimizer_steps']} seconds={row['seconds']:.1f}",
            flush=True,
        )
        if epoch >= args.min_epochs and stale >= args.patience:
            print(f"Early stop after epoch {epoch}; best checkpoint epoch {best_epoch}", flush=True)
            break
    checkpoint = torch.load(output_dir / "multimodal_model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
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
        raise RuntimeError("A model branch failed to update during training")
    val_targets, val_scores = predict(model, split["validation"], cache, demos, args.batch_size)
    threshold = choose_validation_threshold(val_targets, val_scores)
    evaluation, predictions = {}, []
    for name in SPLIT_SIZES:
        targets, scores = predict(model, split[name], cache, demos, args.batch_size)
        evaluation[name] = {
            "at_0.5": metric_summary(targets, scores),
            "at_validation_threshold": metric_summary(targets, scores, threshold),
        }
        for record, target, score in zip(split[name], targets, scores):
            predictions.append(
                {
                    "subject_id": record.subject_id,
                    "split": name,
                    "visits": len(record.visits),
                    "target": target,
                    "model_score": score,
                    "prediction_0.5": int(score >= 0.5),
                    "prediction_validation_threshold": int(score >= threshold),
                }
            )
    pd.DataFrame(predictions).to_csv(output_dir / "predictions.csv", index=False)
    test_targets = evaluation["test"]["at_0.5"]["targets"]
    result = {
        "model_version": MODEL_VERSION,
        "target": provenance["target"],
        "split_counts": counts,
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "optimizer_steps": sum(row["optimizer_steps"] for row in history),
        "validation_selected_threshold": threshold,
        "threshold_fit_split": "validation",
        "trainable_branch_weight_changes_l2": branch_changes,
        "evaluation": evaluation,
        "majority_baseline": metric_summary(test_targets, [positive_count / 40] * len(test_targets)),
        "elapsed_seconds": time.perf_counter() - started,
        "limitations": LIMITATIONS,
    }
    # Checkpoint inference round-trip (including serialized preprocessing) must agree.
    reloaded = MultimodalClassifier()
    reloaded.load_state_dict(checkpoint["model_state_dict"])
    restored_preprocessor = DemographicPreprocessor.from_dict(checkpoint["demographic_preprocessor"])
    np.testing.assert_array_equal(restored_preprocessor.transform(selected), transformed)
    _, reloaded_scores = predict(reloaded, split["test"], cache, demos, args.batch_size)
    np.testing.assert_array_equal(reloaded_scores, evaluation["test"]["at_0.5"]["probabilities"])
    checkpoint["decision_threshold"] = threshold
    save_checkpoint(
        output_dir / "multimodal_model.pt",
        model,
        {k: v for k, v in checkpoint.items() if k != "model_state_dict"},
    )
    write_json(output_dir / "metrics.json", result)
    write_json(output_dir / "status.json", {"status": "completed", "checkpoint_roundtrip": "passed"})
    print(
        json.dumps(
            {
                "status": "completed",
                "run_directory": str(output_dir),
                "best_epoch": best_epoch,
                "test": evaluation["test"],
                "baseline": result["majority_baseline"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
