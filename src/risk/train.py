from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

from src.common import (
    CLINICAL,
    HORIZONS,
    TARGET,
    VERSION,
    command,
    config,
    read_table,
    resolve,
    sha256,
    write_json,
)
from src.fastsurfer.feature_map import ANATOMY, FEATURE_SET
from src.risk.baseline import fit_head, score


def study_frame(cfg: dict, matched: bool) -> pd.DataFrame:
    directory = resolve(cfg["processed_dir"])
    frames = [read_table(directory / name) for name in ("baseline.csv", "labels.csv", "split.csv")]
    if not all(set(f["patient_id"]) == set(frames[0]["patient_id"]) for f in frames):
        raise ValueError("Cohort/label/split coverage differs")
    frame = (
        frames[0]
        .merge(frames[1], on="patient_id", validate="one_to_one")
        .merge(frames[2], on="patient_id", validate="one_to_one")
    )
    if not frame["split"].isin(["train", "validation", "test"]).all():
        raise ValueError("Invalid split assignments")
    if matched:
        features = read_table(directory / "fastsurfer_features.csv")
        features = features[(features["qc"] == "passed") & (features["feature_set_version"] == FEATURE_SET)]
        frame = frame.merge(features, on=["patient_id", "scan_id"], validate="one_to_one")
        if len(frame) == 0:
            raise ValueError("No visually reviewed matched FastSurfer cases")
        if frame["fastsurfer_version"].nunique() != 1 or frame[list(ANATOMY)].isna().any().any():
            raise ValueError("Mixed processing versions or missing anatomy")
    return frame.sort_values("patient_id").reset_index(drop=True)


def train(cfg: dict, model_kind: str, matched: bool = False) -> dict:
    if cfg.get("target") != TARGET:
        raise ValueError("Unsupported endpoint; do not repurpose diagnosis labels")
    matched = matched or model_kind == "clinical_fastsurfer"
    frame = study_frame(cfg, matched)
    fields = list(CLINICAL) + (list(ANATOMY) if model_kind == "clinical_fastsurfer" else [])
    if not (frame["cdr"] == 0).all():
        raise ValueError("Baseline CDR eligibility violated")
    matrix = frame[fields].to_numpy(dtype=float)
    if np.isinf(matrix).any():
        raise ValueError("Nonfinite predictors")
    bundle = {
        "version": VERSION,
        "target": TARGET,
        "model_kind": model_kind,
        "fields": fields,
        "preprocessing_version": "median-standard-logistic-v1",
        "seed": int(cfg["seed"]),
        "monotonic_method": "cumulative_max_known_horizons_v1",
        "heads": {},
        "support": {},
        "cohort": frame[["patient_id", "scan_id", "split"]].to_dict("records"),
        "fastsurfer_version": str(frame["fastsurfer_version"].iloc[0]) if matched else None,
        "feature_set_version": FEATURE_SET if matched else None,
        "warnings": [
            "Research prototype, not a diagnosis or strict MCI-to-Alzheimer forecast.",
            "Sparse observation timing is not biological onset; unknown horizons excluded.",
            "Small OASIS cohort; holdouts may overlap previously inspected studies.",
            "Probabilities are uncalibrated; cumulative-max adjustment is not calibration.",
        ],
        "source_hashes": {
            name: sha256(resolve(cfg["processed_dir"]) / name)
            for name in ("baseline.csv", "labels.csv", "split.csv")
        },
    }
    if matched:
        bundle["source_hashes"]["fastsurfer_features.csv"] = sha256(
            resolve(cfg["processed_dir"]) / "fastsurfer_features.csv"
        )
    for horizon in HORIZONS:
        column = f"y{horizon}"
        if not frame[column].dropna().isin([0, 1]).all():
            raise ValueError("Labels must be 0/1/unknown")
        counts = {}
        for split in ("train", "validation", "test"):
            labels = frame.loc[frame["split"] == split, column]
            counts[split] = {
                "events": int((labels == 1).sum()),
                "negatives": int((labels == 0).sum()),
                "unknown": int(labels.isna().sum()),
                "subjects": len(labels),
            }
        bundle["support"][str(horizon)] = counts
        enough = all(
            counts["train"][c] >= cfg["min_train_per_class"]
            and counts["validation"][c] >= cfg["min_validation_per_class"]
            for c in ("events", "negatives")
        )
        if not enough:
            bundle["heads"][str(horizon)] = None
            continue
        train_mask = (frame["split"] == "train") & frame[column].notna()
        val_mask = (frame["split"] == "validation") & frame[column].notna()
        head = fit_head(
            matrix[train_mask],
            frame.loc[train_mask, column].to_numpy(dtype=int),
            float(cfg["regularization_c"]),
            int(cfg["seed"]),
        )
        probability = score(head, matrix[val_mask])
        labels = frame.loc[val_mask, column].to_numpy(dtype=int)
        candidates = sorted(set([0.5, *probability.tolist()]))
        head["threshold"] = max(candidates, key=lambda t: balanced_accuracy_score(labels, probability >= t))
        head["fit_subjects"] = frame.loc[train_mask, "patient_id"].tolist()
        bundle["heads"][str(horizon)] = head
    # Select thresholds on the same monotonic output the application displays.
    # Never use test outcomes; null heads do not create artificial zeros.
    cumulative = np.zeros(len(frame))
    for horizon in HORIZONS:
        head = bundle["heads"][str(horizon)]
        if head is None:
            continue
        cumulative = np.maximum(cumulative, score(head, matrix))
        val_mask = (frame["split"] == "validation") & frame[f"y{horizon}"].notna()
        labels = frame.loc[val_mask, f"y{horizon}"].to_numpy(dtype=int)
        probability = cumulative[val_mask]
        candidates = sorted(set([0.5, *probability.tolist()]))
        head["threshold"] = max(candidates, key=lambda t: balanced_accuracy_score(labels, probability >= t))
    name = model_kind + ("_matched" if model_kind == "clinical" and matched else "")
    path = resolve(cfg["artifact_dir"]) / f"{name}.json"
    if path.exists():
        raise ValueError("Model artifact already exists; use a fresh versioned artifact directory")
    write_json(path, bundle)
    return {
        "model": name,
        "subjects": len(frame),
        "available_horizons": [h for h, v in bundle["heads"].items() if v],
        "support": bundle["support"],
    }


if __name__ == "__main__":
    args = command(model=True)
    print(train(config(args.config), args.model, args.matched))
