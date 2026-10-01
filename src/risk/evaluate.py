from __future__ import annotations

import json

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import average_precision_score, balanced_accuracy_score, brier_score_loss, roc_auc_score

from src.common import CLINICAL, HORIZONS, command, config, resolve, sha256, write_json
from src.risk.predict import predict
from src.risk.train import study_frame


def metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    if len(labels) == 0:
        return {"subjects": 0, "roc_auc": None, "average_precision": None, "brier": None}
    both = len(set(labels)) == 2
    observed, predicted = calibration_curve(labels, probabilities, n_bins=5, strategy="quantile")
    positive, negative = labels == 1, labels == 0
    classification = probabilities >= threshold
    return {
        "subjects": len(labels),
        "events": int(positive.sum()),
        "negatives": int(negative.sum()),
        "roc_auc": float(roc_auc_score(labels, probabilities)) if both else None,
        "average_precision": float(average_precision_score(labels, probabilities)) if both else None,
        "brier": float(brier_score_loss(labels, probabilities)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, classification)) if both else None,
        "sensitivity": float(classification[positive].mean()) if positive.any() else None,
        "specificity": float((~classification[negative]).mean()) if negative.any() else None,
        "threshold": threshold,
        "calibration_curve": {"observed": observed.tolist(), "predicted": predicted.tolist()},
    }


def evaluate(cfg: dict, model_kind: str, matched: bool = False) -> dict:
    matched = matched or model_kind == "clinical_fastsurfer"
    frame = study_frame(cfg, matched)
    name = model_kind + ("_matched" if model_kind == "clinical" and matched else "")
    path = resolve(cfg["artifact_dir"]) / f"{name}.json"
    bundle = json.loads(path.read_text())
    for filename, expected in bundle["source_hashes"].items():
        if sha256(resolve(cfg["processed_dir"]) / filename) != expected:
            raise ValueError("Study source changed after training")
    if bundle["cohort"] != frame[["patient_id", "scan_id", "split"]].to_dict("records"):
        raise ValueError("Evaluation cohort differs from fitted study")
    outputs = []
    for row in frame.to_dict("records"):
        request = {
            "patient_id": row["patient_id"],
            "baseline": {f: None if np.isnan(row[f]) else row[f] for f in CLINICAL},
        }
        if model_kind == "clinical_fastsurfer":
            from src.fastsurfer.feature_map import ANATOMY, FEATURE_SET

            request.update(
                fastsurfer_features={f: row[f] for f in ANATOMY},
                qc="passed",
                scan_id=row["scan_id"],
                fastsurfer_version=row["fastsurfer_version"],
                feature_set_version=FEATURE_SET,
            )
        outputs.append(predict(request, name, artifact_dir=resolve(cfg["artifact_dir"])))
    result = {
        "model": name,
        "model_sha256": sha256(path),
        "split_metrics": {},
        "support": bundle["support"],
        "clinical_fastsurfer_matched": matched,
        "calibration": "uncalibrated",
        "warnings": bundle["warnings"],
        "confidence_intervals": "not estimated; small event support",
    }
    for split in ("validation", "test"):
        result["split_metrics"][split] = {}
        for horizon in HORIZONS:
            head = bundle["heads"][str(horizon)]
            if head is None:
                result["split_metrics"][split][str(horizon)] = {"status": "unavailable"}
                continue
            indices = frame.index[(frame["split"] == split) & frame[f"y{horizon}"].notna()]
            labels = frame.loc[indices, f"y{horizon}"].to_numpy(dtype=int)
            probabilities = np.array([outputs[i].probabilities[str(horizon)] for i in indices], dtype=float)
            if not np.isfinite(probabilities).all():
                raise ValueError("Evaluation inference returned unavailable/nonfinite predictions")
            result["split_metrics"][split][str(horizon)] = metrics(labels, probabilities, head["threshold"])
    write_json(resolve(cfg["artifact_dir"]) / f"{name}_evaluation.json", result)
    return result


if __name__ == "__main__":
    args = command(model=True)
    print(evaluate(config(args.config), args.model, args.matched))
