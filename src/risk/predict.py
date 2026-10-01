"""Single CPU-safe predictor adapter for both application front ends."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.common import CLINICAL, HORIZONS, ROOT, TARGET, VERSION
from src.contracts import PredictionRequest, PredictionResult
from src.fastsurfer.feature_map import ANATOMY, FEATURE_SET
from src.risk.baseline import monotonic, score
from src.risk.explain import explain

LIMIT = "Research prototype: observed CDR conversion, not an Alzheimer diagnosis."


def unavailable(message: str, missing: list[str] | None = None) -> PredictionResult:
    nulls = {str(h): None for h in HORIZONS}
    return PredictionResult(
        status="unavailable",
        mode="unavailable",
        model_version=VERSION,
        preprocessing_version="median-standard-logistic-v1",
        probabilities=nulls,
        raw_probabilities=nulls,
        calibration={str(h): "unavailable" for h in HORIZONS},
        missing_fields=missing or [],
        warnings=[LIMIT, message],
    )


def predict(
    request: PredictionRequest | dict, model_kind: str = "clinical", *, artifact_dir: Path | None = None
) -> PredictionResult:
    request = PredictionRequest.model_validate(request)
    if model_kind not in ("clinical", "clinical_matched", "clinical_fastsurfer"):
        return unavailable("Optional 3D model is not trained or validated.")
    directory = artifact_dir or ROOT / "artifacts/forecast_v2"
    path = directory / f"{model_kind}.json"
    if not path.is_file():
        return unavailable("Requested model artifact is unavailable; no silent fallback.")
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        kind = "clinical" if model_kind == "clinical_matched" else model_kind
        fields = list(CLINICAL) + (list(ANATOMY) if kind == "clinical_fastsurfer" else [])
        if (
            bundle["target"] != TARGET
            or bundle["version"] != VERSION
            or bundle["fields"] != fields
            or bundle["model_kind"] != kind
        ):
            return unavailable("Model task/schema mismatch.")
        missing = sorted(set(CLINICAL) - set(request.baseline))
        if set(request.baseline) - set(CLINICAL):
            return unavailable("Unknown/future/outcome-derived predictors are forbidden.")
        if missing:
            return unavailable("Baseline source fields are absent.", missing)
        if request.baseline["cdr"] != 0:
            return unavailable(
                "This forecast requires a CDR-zero baseline, not baseline dementia or inferred MCI."
            )
        required = [f for f in CLINICAL if f not in ("ses", "mmse") and request.baseline[f] is None]
        if required:
            return unavailable("Required baseline measurements are missing.", required)
        domains = {
            "age_years": (18, 120),
            "sex": (0, 1),
            "education": (0, 40),
            "ses": (1, 5),
            "mmse": (0, 30),
            "etiv": (1, 10000),
            "nwbv": (0, 1),
            "asf": (0.01, 10),
        }
        if any(
            request.baseline[f] is not None and not low <= request.baseline[f] <= high
            for f, (low, high) in domains.items()
        ):
            return unavailable("Baseline measurement outside documented domain.")
        if request.baseline["sex"] not in (0, 1):
            return unavailable("Sex must match the documented binary source encoding.")
        values = dict(request.baseline)
        used_mri = kind == "clinical_fastsurfer"
        if used_mri:
            if (
                request.qc != "passed"
                or request.fastsurfer_version != bundle["fastsurfer_version"]
                or request.feature_set_version != FEATURE_SET
                or not request.scan_id
            ):
                return unavailable(
                    "Matching FastSurfer version, feature set, scan and passed visual QC required."
                )
            anatomy = request.fastsurfer_features or {}
            if any(f not in anatomy or anatomy[f] is None or anatomy[f] <= 0 for f in ANATOMY):
                return unavailable(
                    "Required verified anatomy is missing.", [f for f in ANATOMY if anatomy.get(f) is None]
                )
            values.update(anatomy)
        x = np.array([[values[f] if values[f] is not None else np.nan for f in fields]], dtype=float)
        raw, explanations, calibration = {}, {}, {}
        for horizon in HORIZONS:
            head = bundle["heads"][str(horizon)]
            raw[str(horizon)] = float(score(head, x)[0]) if head else None
            calibration[str(horizon)] = head["calibration"] if head else "unavailable"
            if head:
                explanations[str(horizon)] = explain(head, x, fields)
        probabilities = monotonic(raw)
        available = sum(v is not None for v in probabilities.values())
        warnings = list(bundle["warnings"])
        role = next(
            (p["split"] for p in bundle["cohort"] if p["patient_id"] == request.patient_id), "unassigned"
        )
        warnings += [f"Cohort role: {role}; training cases are in-sample demonstrations."]
        for horizon, value in probabilities.items():
            if value is None:
                warnings.append(
                    f"{horizon}-month horizon unavailable: insufficient training/development support."
                )
            elif any(bundle["support"][horizon]["test"][c] < 2 for c in ("events", "negatives")):
                warnings.append(
                    f"{horizon}-month test set lacks adequate class support; discrimination is not validated."
                )
        return PredictionResult(
            status="ok" if available == 3 else ("partial" if available else "unavailable"),
            mode="live" if available else "unavailable",
            model_version=VERSION,
            preprocessing_version=bundle["preprocessing_version"],
            fastsurfer_version=bundle["fastsurfer_version"] if used_mri else None,
            used_mri=used_mri,
            probabilities=probabilities,
            raw_probabilities=raw,
            calibration=calibration,
            missing_fields=[f for f in fields if values[f] is None],
            warnings=warnings,
            explanation={
                "raw_logistic_heads": explanations,
                "method": "standardized logit contributions, not causal effects",
                "postprocessing": "cumulative maximum over supported horizons",
            },
        )
    except (ValueError, KeyError, OSError, TypeError):
        return unavailable("Model bundle is invalid or incomplete; inspect local artifact logs.")
