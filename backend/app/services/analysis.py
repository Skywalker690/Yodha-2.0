import hashlib
import json
from math import isfinite

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Analysis, Patient, Visit
from backend.app.services.storage import resolve_key
from ml.contracts import MODEL_VERSION, VisitInput
from ml.anatomy.contracts import VERSION as ANATOMY_VERSION
from ml.anatomy.ratings import AUTOMATIC_RESEARCH_RATING_POLICY
from src.common import sha256

NUMERIC_COVARIATES = ("Age", "EDUC", "SES", "MMSE", "eTIV", "nWBV", "ASF", "MR Delay", "Visit")
COVARIATES = (*NUMERIC_COVARIATES, "M/F", "Hand")


def trained_model_version() -> str:
    """Resolve the configured checkpoint identity without exposing filesystem errors."""
    try:
        from ml.trained_inference import checkpoint_identity

        return checkpoint_identity(get_settings().trained_model_path)
    except Exception:
        raise HTTPException(
            503, "The trained checkpoint is unavailable or invalid. No baseline fallback is used."
        ) from None


def trained_snapshot(visits: list[Visit]) -> list[dict]:
    """Freeze only source covariates; never derive demographics or include outcome labels."""
    snapshot = []
    try:
        for visit in visits:
            metadata = visit.metadata_json
            if not isinstance(metadata, dict) or not set(COVARIATES).issubset(metadata):
                raise ValueError("Incomplete source covariates")
            covariates = {key: metadata[key] for key in COVARIATES}
            # Reject coercible strings/bools before VisitInput's numeric union can coerce them.
            for key in NUMERIC_COVARIATES:
                value = covariates[key]
                if value is None and key in {"SES", "MMSE"}:
                    continue
                if type(value) not in {int, float} or not isfinite(value):
                    raise ValueError("Invalid numeric source covariate")
            if any(
                value is not None and not isinstance(value, str)
                for value in (covariates["M/F"], covariates["Hand"])
            ):
                raise ValueError("Invalid categorical source covariate")
            snapshot.append(
                {
                    "visit_id": visit.id,
                    "days_from_baseline": visit.days_from_baseline,
                    "mri_key": visit.mri_key,
                    "covariates": covariates,
                }
            )
        inputs = [
            VisitInput(
                visit_id=item["visit_id"],
                days_from_baseline=item["days_from_baseline"],
                mri_path=str(resolve_key(item["mri_key"])),
                covariates=item["covariates"],
            )
            for item in snapshot
        ]
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(
            422,
            "Trained analysis requires complete recorded visit covariates with valid numeric values. "
            "Recorded SES/MMSE may explicitly be null; demographics are never invented.",
        ) from None
    try:
        from ml.trained_inference import validate_covariates
    except Exception:
        raise HTTPException(
            503, "The trained inference service is unavailable. No baseline fallback is used."
        ) from None
    try:
        validate_covariates(inputs)
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            422,
            "Trained analysis requires at least three chronological MRI visits with complete, "
            "valid source covariates and matching recorded visit timing.",
        ) from None
    except Exception:
        raise HTTPException(
            503, "Trained input validation is unavailable. No baseline fallback is used."
        ) from None
    return snapshot


def cache_key(snapshot: list[dict]) -> str:
    digest = hashlib.sha256(
        json.dumps({"version": MODEL_VERSION, "inputs": snapshot}, sort_keys=True).encode()
    ).hexdigest()
    return f"cache/{digest}.json"


def enqueue(
    db: Session, patient: Patient, selected: Visit, mode: str, future_interval_days: int = 365
) -> Analysis:
    if get_settings().ml_only and mode != "anatomy":
        raise HTTPException(
            409, "Legacy analysis modes are disabled. Use Clinical + FastSurfer forecast; no fallback."
        )
    # Serialize starts per patient, including concurrent API requests.
    db.execute(select(Patient).where(Patient.id == patient.id).with_for_update()).scalar_one()
    active = db.scalar(
        select(Analysis).where(
            Analysis.patient_id == patient.id, Analysis.status.in_(["queued", "processing"])
        )
    )
    if active:
        raise HTTPException(409, "An analysis is already running for this patient.")
    visits = db.scalars(
        select(Visit)
        .where(Visit.patient_id == patient.id, Visit.days_from_baseline <= selected.days_from_baseline)
        .order_by(Visit.days_from_baseline)
    ).all()
    if not visits or any(not visit.mri_key for visit in visits):
        raise HTTPException(422, "Upload MRI files for all visits up to the selected visit before analysis.")
    snapshot = [
        {"visit_id": v.id, "days_from_baseline": v.days_from_baseline, "mri_key": v.mri_key} for v in visits
    ]
    model_version = MODEL_VERSION
    if mode == "anatomy":
        if not 1 <= len(visits) <= 5:
            raise HTTPException(
                422, "Anatomy supports one measured visit or two-to-five chronological history visits."
            )
        model_version = ANATOMY_VERSION
        for item, visit in zip(snapshot, visits):
            item.update(
                source_sha256=sha256(resolve_key(visit.mri_key)),
                metadata={key: visit.metadata_json.get(key) for key in (*COVARIATES, "CDR")},
                etiv_unit="cm3" if patient.source == "oasis-2" else None,
                source_units_verified=patient.source == "oasis-2",
                future_interval_days=future_interval_days,
                rating_policy=AUTOMATIC_RESEARCH_RATING_POLICY,
            )
    if mode == "trained":
        snapshot = trained_snapshot(list(visits))
        model_version = trained_model_version()
    for item, visit in zip(snapshot, visits):
        if "Age" in visit.metadata_json or "nWBV" in visit.metadata_json:
            from backend.app.services.nwbv_reference import OASIS_SOURCE_METHOD

            item["nwbv_reference_input"] = {
                "age": visit.metadata_json.get("Age"),
                "nwbv": visit.metadata_json.get("nWBV"),
                "measurement_method": visit.metadata_json.get("nwbv_measurement_method")
                or (OASIS_SOURCE_METHOD if patient.source == "oasis-2" else "unknown"),
            }
    if mode == "precomputed" and not resolve_key(cache_key(snapshot)).is_file():
        raise HTTPException(
            409, "No matching precomputed result. Run local inference once to prepare the cache."
        )
    analysis = Analysis(
        patient_id=patient.id,
        visit_id=selected.id,
        input_json=snapshot,
        output_mode=mode,
        model_version=model_version,
    )
    db.add(analysis)
    db.flush()
    return analysis


def latest_anatomy(db: Session, patient_id: str, completed: bool = False) -> Analysis | None:
    query = select(Analysis).where(Analysis.patient_id == patient_id, Analysis.output_mode == "anatomy")
    if completed:
        query = query.where(Analysis.status == "completed")
    return db.scalar(query.order_by(Analysis.created_at.desc()).limit(1))


def latest_completed(db: Session, patient_id: str) -> Analysis | None:
    if get_settings().ml_only:
        return None
    return db.scalar(
        select(Analysis)
        .where(
            Analysis.patient_id == patient_id,
            Analysis.status == "completed",
            Analysis.output_mode != "anatomy",
        )
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
