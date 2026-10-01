"""Train the small longitudinal research model on a deterministic subject split.

This is an experiment runner, not a clinical training pipeline. The target is an
observed subject-level CDR increase from first to last available visit.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import torch
from torch import nn

from ml.preprocessing import prepare
from ml.encoder import SpatialEncoder
from ml.temporal_model import TemporalModel


SEED = 20261001
TARGET_NAME = "observed_cdr_increase"


@dataclass(frozen=True)
class SubjectRecord:
    subject_id: str
    visits: tuple[tuple[str, int, Path, float], ...]
    target: int


def _find_volume(root: Path, mri_id: str) -> Path:
    candidates = sorted(root.glob(f"OAS2_RAW_PART*/{mri_id}/RAW/mpr-*.nifti.hdr"))
    if not candidates:
        raise FileNotFoundError(f"Missing paired MRI for {mri_id}")
    return next((path for path in candidates if path.name == "mpr-1.nifti.hdr"), candidates[0])


def load_subjects(metadata_path: Path, dataset_root: Path) -> list[SubjectRecord]:
    frame = pd.read_excel(metadata_path) if metadata_path.suffix.lower() == ".xlsx" else pd.read_csv(metadata_path)
    frame = frame.sort_values(["Subject ID", "MR Delay"])
    records: list[SubjectRecord] = []
    for subject_id, group in frame.groupby("Subject ID", sort=True):
        if len(group) < 3:
            continue
        visits = tuple(
            (
                str(row["MRI ID"]),
                int(row["MR Delay"]),
                _find_volume(dataset_root, str(row["MRI ID"])),
                float(row["CDR"]),
            )
            for _, row in group.iterrows()
        )
        records.append(
            SubjectRecord(
                subject_id=str(subject_id).strip(),
                visits=visits,
                target=int(visits[-1][3] > visits[0][3]),
            )
        )
    return records


def stratified_split(records: list[SubjectRecord]) -> dict[str, list[SubjectRecord]]:
    rng = random.Random(SEED)
    by_target: dict[int, list[SubjectRecord]] = {0: [], 1: []}
    for record in records:
        by_target[record.target].append(record)
    for group in by_target.values():
        rng.shuffle(group)
    split: dict[str, list[SubjectRecord]] = {"train": [], "validation": [], "test": []}
    for target, group in by_target.items():
        if len(group) < 3:
            raise ValueError("Each target class needs at least three subjects for a stratified split")
        # Preserve at least two positive examples in each holdout while filling
        # the requested 40/8/8 totals with the larger negative class.
        holdout_count = 2 if target == 1 else 6
        split["validation"].extend(group[:holdout_count])
        split["test"].extend(group[holdout_count : holdout_count * 2])
        split["train"].extend(group[holdout_count * 2 :])
    rng.shuffle(split["train"])
    rng.shuffle(split["validation"])
    rng.shuffle(split["test"])
    if {r.subject_id for items in split.values() for r in items} != {r.subject_id for r in records}:
        raise ValueError("Split does not cover every subject exactly once")
    if any(len(items) != expected for items, expected in zip(split.values(), (40, 8, 8))):
        raise ValueError(f"Expected a 40/8/8 split, got {[len(items) for items in split.values()]}")
    return split


def write_manifest(split: dict[str, list[SubjectRecord]], path: Path) -> None:
    rows = []
    for name, records in split.items():
        for record in records:
            for index, (visit_id, days, mri_path, cdr) in enumerate(record.visits):
                rows.append(
                    {
                        "subject_id": record.subject_id,
                        "visit_id": visit_id,
                        "visit_index": index,
                        "days_from_baseline": days,
                        "mri_path": str(mri_path.resolve()),
                        "cdr": cdr,
                        "target": record.target,
                        "split": name,
                    }
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).sort_values(["split", "subject_id", "days_from_baseline"]).to_csv(path, index=False)


def cache_volumes(records: list[SubjectRecord], cache_dir: Path) -> dict[str, np.ndarray]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache: dict[str, np.ndarray] = {}
    all_visits = [(visit_id, path) for record in records for visit_id, _, path, _ in record.visits]
    for index, (visit_id, path) in enumerate(all_visits, start=1):
        cache_path = cache_dir / f"{visit_id}.npy"
        if cache_path.exists():
            cache[visit_id] = np.load(cache_path, allow_pickle=False)
            continue
        # Validate the source before preparing it; the source pair remains immutable.
        nib.load(str(path))
        volume = prepare(path, allow_pair=True).volume.astype(np.float32, copy=False)
        np.save(cache_path, volume)
        cache[visit_id] = volume
        print(f"Cached {index}/{len(all_visits)} volumes: {visit_id}", flush=True)
    return cache


class LongitudinalClassifier(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = SpatialEncoder(feature_dim=32)
        self.temporal = TemporalModel(feature_dim=32, hidden_dim=16)

    def forward(self, volumes: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        batch, steps = volumes.shape[:2]
        features = self.encoder(volumes.reshape(batch * steps, 1, 64, 64, 64))
        sequence = features.reshape(batch, steps, -1)
        hidden, _ = self.temporal.lstm(sequence)
        positions = (lengths - 1).clamp_min(0).view(-1, 1, 1).expand(-1, 1, hidden.shape[-1])
        final_hidden = hidden.gather(1, positions).squeeze(1)
        return self.temporal.head(final_hidden).squeeze(-1)


def batch_records(records: list[SubjectRecord], cache: dict[str, np.ndarray]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    max_steps = max(len(record.visits) for record in records)
    volumes = np.zeros((len(records), max_steps, 1, 64, 64, 64), dtype=np.float32)
    lengths = []
    targets = []
    for row, record in enumerate(records):
        lengths.append(len(record.visits))
        targets.append(record.target)
        for column, (visit_id, _, _, _) in enumerate(record.visits):
            volumes[row, column, 0] = cache[visit_id]
    return torch.from_numpy(volumes), torch.tensor(lengths, dtype=torch.long), torch.tensor(targets, dtype=torch.float32)


def evaluate(model: nn.Module, records: list[SubjectRecord], cache: dict[str, np.ndarray]) -> dict[str, float]:
    model.eval()
    with torch.no_grad():
        volumes, lengths, targets = batch_records(records, cache)
        probabilities = torch.sigmoid(model(volumes, lengths))
        predictions = (probabilities >= 0.5).float()
        loss = nn.functional.binary_cross_entropy(probabilities, targets)
    return {
        "loss": float(loss),
        "accuracy": float((predictions == targets).float().mean()),
        "positive_subjects": int(targets.sum()),
        "subjects": len(records),
    }


def train(split: dict[str, list[SubjectRecord]], cache: dict[str, np.ndarray], output_dir: Path, epochs: int) -> dict:
    torch.manual_seed(SEED)
    torch.set_num_threads(min(8, max(1, torch.get_num_threads())))
    model = LongitudinalClassifier()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    positives = sum(record.target for record in split["train"])
    negatives = len(split["train"]) - positives
    if not positives or not negatives:
        raise ValueError("Training split must contain both target classes")
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([negatives / positives]))
    best_loss = float("inf")
    best_epoch = 0
    best_state = None
    stale_epochs = 0
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        volumes, lengths, targets = batch_records(split["train"], cache)
        optimizer.zero_grad(set_to_none=True)
        logits = model(volumes, lengths)
        loss = criterion(logits, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        metrics = {
            "epoch": epoch,
            "train_loss": float(loss.detach()),
            "validation": evaluate(model, split["validation"], cache),
        }
        history.append(metrics)
        print(
            f"epoch={epoch:03d} train_loss={metrics['train_loss']:.4f} "
            f"val_loss={metrics['validation']['loss']:.4f} "
            f"val_accuracy={metrics['validation']['accuracy']:.3f}",
            flush=True,
        )
        if metrics["validation"]["loss"] < best_loss:
            best_loss = metrics["validation"]["loss"]
            best_epoch = epoch
            best_state = {key: value.cpu().clone() for key, value in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= 5:
                print(f"early_stop=validation_loss_no_improvement_for_{stale_epochs}_epochs", flush=True)
                break
    if best_state is None:
        raise RuntimeError("Training produced no checkpoint")
    model.load_state_dict(best_state)
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "seed": SEED,
            "target": TARGET_NAME,
            "architecture": "SpatialEncoder(32)+LSTM(16)",
            "input_shape": [64, 64, 64],
            "best_epoch": best_epoch,
        },
        output_dir / "longitudinal_model.pt",
    )
    return {
        "seed": SEED,
        "target": TARGET_NAME,
        "architecture": "SpatialEncoder(32)+LSTM(16)",
        "split_sizes": {name: len(records) for name, records in split.items()},
        "split_targets": {name: sum(record.target for record in records) for name, records in split.items()},
        "best_epoch": best_epoch,
        "best_validation_loss": best_loss,
        "validation": evaluate(model, split["validation"], cache),
        "test": evaluate(model, split["test"], cache),
        "history": history,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=Path("dataset/oasis_longitudinal_demographics-8d83e569fa2e2d30.xlsx"))
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/training"))
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    if args.epochs < 1:
        raise SystemExit("--epochs must be positive")
    records = load_subjects(args.metadata, args.dataset_root)
    split = stratified_split(records)
    write_manifest(split, args.output_dir / "subject_split.csv")
    cache = cache_volumes(records, args.output_dir / "volume_cache")
    metrics = train(split, cache, args.output_dir, args.epochs)
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in metrics.items() if key != "history"}, indent=2))


if __name__ == "__main__":
    main()
