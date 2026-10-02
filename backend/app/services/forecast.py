"""Cheap baseline prediction only; anatomy processing stays offline."""

from __future__ import annotations

import numpy as np

from src.common import CLINICAL, read_table
from src.fastsurfer.feature_map import ANATOMY, FEATURE_SET
from src.risk.predict import predict, unavailable
from src.risk.release import serving_predict
from backend.app.core.config import get_settings


def patient_forecast(patient_code: str, source: str, model_kind: str) -> dict:
    if source != "oasis-2":
        return {
            "prediction": unavailable(
                "No verified baseline study record for this uploaded case."
            ).model_dump(),
            "anatomy": None,
            "qc": "unavailable",
        }
    settings = get_settings()
    directory = settings.forecast_processed_dir
    try:
        baseline = read_table(directory / "baseline.csv")
        selected = baseline[baseline["patient_id"] == patient_code]
        if len(selected) != 1:
            return {
                "prediction": unavailable(
                    "Case is outside the CDR-zero baseline forecast cohort."
                ).model_dump(),
                "anatomy": None,
                "qc": "unavailable",
            }
        row = selected.iloc[0]
        request = {
            "patient_id": patient_code,
            "baseline": {f: None if np.isnan(row[f]) else float(row[f]) for f in CLINICAL},
        }
        anatomy, qc = None, "unavailable"
        path = directory / "fastsurfer_features.csv"
        if path.exists():
            features = read_table(path)
            found = features[
                (features["patient_id"] == patient_code) & (features["scan_id"] == row["scan_id"])
            ]
            if len(found) == 1:
                measurements = found.iloc[0]
                qc = measurements["qc"]
                if qc == "passed":
                    anatomy = {f: float(measurements[f]) for f in ANATOMY}
                    request.update(
                        fastsurfer_features=anatomy,
                        qc="passed",
                        scan_id=row["scan_id"],
                        fastsurfer_version=str(measurements["fastsurfer_version"]),
                        feature_set_version=FEATURE_SET,
                    )
        result = (
            serving_predict(request, settings.forecast_artifact_dir, directory)
            if settings.ml_only
            else predict(request, model_kind, artifact_dir=settings.forecast_artifact_dir)
        )
        return {
            "prediction": result.model_dump(mode="json"),
            "baseline": request["baseline"],
            "anatomy": anatomy,
            "qc": qc,
            "anatomy_units": "mm3",
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {
            "prediction": unavailable("Forecast study artifacts unavailable or invalid.").model_dump(),
            "anatomy": None,
            "qc": "unavailable",
        }
