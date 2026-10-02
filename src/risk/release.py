"""Explicit artifact promotion and fail-closed, CPU-only serving checks."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from src.common import HORIZONS, ROOT, TARGET, VERSION, sha256, write_json
from src.contracts import PredictionResult
from src.risk.predict import predict, unavailable

FILES = (
    "clinical_fastsurfer.json",
    "clinical_fastsurfer_evaluation.json",
    "clinical_matched.json",
    "clinical_matched_evaluation.json",
)


def assess(directory: Path, processed_dir: Path) -> list[str]:
    """Verify fixed evidence gates, not a claim of adequate clinical validation."""
    try:
        model, evaluation, reference, reference_eval = [
            json.loads((directory / name).read_text(encoding="utf-8")) for name in FILES
        ]
        from src.common import CLINICAL, CLINICAL_UNITS
        from src.fastsurfer.feature_map import ANATOMY, FEATURE_SET

        if (
            model["version"] != VERSION
            or model["target"] != TARGET
            or model["model_kind"] != "clinical_fastsurfer"
            or model["fields"] != [*CLINICAL, *ANATOMY]
            or reference["fields"] != list(CLINICAL)
            or model.get("clinical_units") != CLINICAL_UNITS
            or reference.get("clinical_units") != CLINICAL_UNITS
            or model.get("anatomy_units") != "mm3"
            or model["feature_set_version"] != FEATURE_SET
            or reference["model_kind"] != "clinical"
            or model["cohort"] != reference["cohort"]
            or model["source_hashes"] != reference["source_hashes"]
        ):
            return ["Matched model/cohort/schema evidence differs."]
        for filename, expected in model["source_hashes"].items():
            if filename not in ("baseline.csv", "labels.csv", "split.csv", "fastsurfer_features.csv"):
                return ["Unexpected study source in release."]
            if sha256(processed_dir / filename) != expected:
                return ["Study data changed after training; rebuild the release."]
        reasons = []
        from src.common import read_table

        features = read_table(processed_dir / "fastsurfer_features.csv")
        selected = features[features["patient_id"].isin([p["patient_id"] for p in model["cohort"]])]
        if (
            len(selected) != len(model["cohort"])
            or not (selected["qc"] == "passed").all()
            or not (selected["feature_set_version"] == FEATURE_SET).all()
            or not (selected["fastsurfer_version"].astype(str) == model["fastsurfer_version"]).all()
            or not selected[list(ANATOMY)].map(lambda v: math.isfinite(v) and v > 0).all().all()
        ):
            return ["Reviewed, version-matched physical anatomy is required for every serving-cohort case."]
        if dict(zip(selected["patient_id"], selected["scan_id"])) != {
            p["patient_id"]: p["scan_id"] for p in model["cohort"]
        }:
            return ["Reviewed anatomy is not matched to the trained baseline scans."]
        for bundle, evidence, filename in (
            (model, evaluation, FILES[0]),
            (reference, reference_eval, FILES[2]),
        ):
            if (
                evidence["model_sha256"] != sha256(directory / filename)
                or not evidence["clinical_fastsurfer_matched"]
                or evidence["support"] != bundle["support"]
            ):
                return ["Evaluation does not match the saved model."]
            for horizon in map(str, HORIZONS):
                if not bundle["heads"].get(horizon):
                    reasons.append(f"{horizon}-month trained head unavailable.")
                    continue
                for split, minimum in (("train", 5), ("validation", 2), ("test", 2)):
                    if any(bundle["support"][horizon][split][c] < minimum for c in ("events", "negatives")):
                        reasons.append(f"{horizon}-month {split} lacks both-class support.")
                for split in ("validation", "test"):
                    measured = evidence["split_metrics"][split][horizon]
                    if any(
                        measured.get(metric) is None or not math.isfinite(measured[metric])
                        for metric in ("roc_auc", "balanced_accuracy", "brier")
                    ):
                        reasons.append(f"{horizon}-month {split} metrics unavailable.")
        # Predeclared development gates. Never select a threshold/model on test scores.
        for horizon in map(str, HORIZONS):
            measured = evaluation["split_metrics"]["validation"][horizon]
            baseline = reference_eval["split_metrics"]["validation"][horizon]
            if measured.get("roc_auc") is not None and measured.get("balanced_accuracy") is not None:
                if measured["roc_auc"] < 0.7 or measured["balanced_accuracy"] < 0.6:
                    reasons.append(f"{horizon}-month development performance fails the serving gate.")
            if measured.get("brier") is not None and baseline.get("brier") is not None:
                if measured["brier"] > baseline["brier"]:
                    reasons.append(
                        f"{horizon}-month development Brier is worse than matched clinical reference."
                    )
        return sorted(set(reasons))
    except (OSError, ValueError, KeyError, TypeError):
        return [
            "Complete trained Clinical + FastSurfer and matched evaluation artifacts are missing or invalid."
        ]


def readiness(directory: Path | None = None, processed_dir: Path | None = None) -> dict:
    directory = directory or ROOT / "artifacts/forecast_v2"
    processed_dir = processed_dir or ROOT / "data/forecast_v2"
    try:
        manifest = json.loads((directory / "serving_manifest.json").read_text(encoding="utf-8"))
        if (
            manifest["schema_version"] != 1
            or manifest["model_kind"] != "clinical_fastsurfer"
            or set(manifest["files"]) != set(FILES)
            or any(sha256(directory / name) != digest for name, digest in manifest["files"].items())
        ):
            raise ValueError("Release fingerprint mismatch")
        reasons = assess(directory, processed_dir)
        return {
            "ready": not reasons,
            "model_kind": "clinical_fastsurfer",
            "reasons": reasons,
            "model_sha256": manifest["files"][FILES[0]] if not reasons else None,
            "clinical_validation": False,
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {
            "ready": False,
            "model_kind": "clinical_fastsurfer",
            "model_sha256": None,
            "reasons": ["No intact promoted Clinical + FastSurfer release. No fallback is enabled."],
            "clinical_validation": False,
        }


def serving_predict(
    request: dict, directory: Path | None = None, processed_dir: Path | None = None
) -> PredictionResult:
    state = readiness(directory, processed_dir)
    if not state["ready"]:
        return unavailable("ML-only serving blocked: " + " ".join(state["reasons"]))
    return predict(request, "clinical_fastsurfer", artifact_dir=directory)


def promote(directory: Path, processed_dir: Path) -> dict:
    reasons = assess(directory, processed_dir)
    if reasons:
        raise ValueError("Release blocked: " + " ".join(reasons))
    path = directory / "serving_manifest.json"
    if path.exists():
        raise ValueError("Release already promoted; use an immutable new run directory")
    manifest = {
        "schema_version": 1,
        "model_kind": "clinical_fastsurfer",
        "files": {name: sha256(directory / name) for name in FILES},
        "clinical_validation": False,
    }
    write_json(path, manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--processed-dir", required=True, type=Path)
    args = parser.parse_args()
    promote(args.artifact_dir.resolve(), args.processed_dir.resolve())
    print("Release promoted; research-use only, not clinical validation.")
