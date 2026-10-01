import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Analysis, Patient, Visit
from backend.app.services.storage import resolve_key
from ml.contracts import MODEL_VERSION


def cache_key(snapshot: list[dict]) -> str:
    digest = hashlib.sha256(
        json.dumps({"version": MODEL_VERSION, "inputs": snapshot}, sort_keys=True).encode()
    ).hexdigest()
    return f"cache/{digest}.json"


def enqueue(db: Session, patient: Patient, selected: Visit, mode: str) -> Analysis:
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
    if mode == "precomputed" and not resolve_key(cache_key(snapshot)).is_file():
        raise HTTPException(
            409, "No matching precomputed result. Run local inference once to prepare the cache."
        )
    analysis = Analysis(patient_id=patient.id, visit_id=selected.id, input_json=snapshot, output_mode=mode)
    db.add(analysis)
    db.flush()
    return analysis


def latest_completed(db: Session, patient_id: str) -> Analysis | None:
    return db.scalar(
        select(Analysis)
        .where(Analysis.patient_id == patient_id, Analysis.status == "completed")
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
