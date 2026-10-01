import json
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import create_token, current_user, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.models import Analysis, Biomarker, Heatmap, Patient, User, Visit
from backend.app.schemas.contracts import AnalysisCreate, AnalysisOut, Login, PatientCreate, VisitCreate
from backend.app.services.analysis import enqueue, latest_completed, trained_model_version
from backend.app.services.reports import build_report
from backend.app.services.forecast import patient_forecast
from backend.app.services.storage import new_key, resolve_key
from ml.contracts import MODEL_VERSION
from ml.preprocessing import render_preview

router = APIRouter()
attempts: dict[str, list[float]] = defaultdict(list)
DUMMY_HASH = hash_password("dummy-password-used-only-for-timing")


def owned_patient(db: Session, user: User, patient_id: str) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None or patient.owner_id != user.id:
        raise HTTPException(404, "Patient not found.")
    return patient


def owned_visit(db: Session, user: User, visit_id: str) -> Visit:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(404, "Visit not found.")
    owned_patient(db, user, visit.patient_id)
    return visit


@router.get("/patients/{patient_id}/forecast")
def forecast(patient_id: str, model_kind: Literal["clinical", "clinical_matched", "clinical_fastsurfer"] = "clinical",
             db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    patient = owned_patient(db, user, patient_id)
    return camel(patient_forecast(patient.code, patient.source, model_kind))


def owned_analysis(db: Session, user: User, analysis_id: str) -> Analysis:
    item = db.get(Analysis, analysis_id)
    if item is None:
        raise HTTPException(404, "Analysis not found.")
    owned_patient(db, user, item.patient_id)
    return item


def camel(value):
    if isinstance(value, list):
        return [camel(item) for item in value]
    if isinstance(value, dict):
        return {
            re.sub(r"_([a-z])", lambda match: match[1].upper(), key): camel(item)
            for key, item in value.items()
        }
    return value


def analysis_payload(item: Analysis) -> dict:
    return camel(AnalysisOut.model_validate(item).model_dump(mode="json"))


def patient_payload(db: Session, patient: Patient) -> dict:
    visits = db.scalars(
        select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.days_from_baseline)
    ).all()
    latest = db.scalar(
        select(Analysis)
        .where(Analysis.patient_id == patient.id)
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    completed = latest_completed(db, patient.id)
    return {
        "id": patient.id,
        "code": patient.code,
        "age": patient.age,
        "sex": patient.sex,
        "notes": patient.notes,
        "source": patient.source,
        "createdAt": patient.created_at.isoformat(),
        "visitCount": len(visits),
        "latestAnalysis": analysis_payload(latest) if latest else None,
        "latestCompleted": analysis_payload(completed) if completed else None,
        "visits": [
            {
                "id": v.id,
                "label": v.label,
                "daysFromBaseline": v.days_from_baseline,
                "hasMri": bool(v.mri_key),
                "metadata": v.metadata_json,
                "previewUrl": f"/api/visits/{v.id}/preview" if v.preview_key else None,
                "volumeUrl": f"/api/visits/{v.id}/volume" if v.mri_key else None,
            }
            for v in visits
        ],
    }


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    heartbeat = resolve_key("worker-heartbeat.txt")
    worker = heartbeat.exists() and time.time() - heartbeat.stat().st_mtime < 120
    try:
        trained_version = trained_model_version()
    except HTTPException:
        trained_version = None
    return {
        "status": "online",
        "database": "connected",
        "worker": "online" if worker else "offline",
        "modelVersion": MODEL_VERSION,
        "baselineModelVersion": MODEL_VERSION,
        "trainedModelVersion": trained_version,
        "trainedModelReady": trained_version is not None,
        "storage": "local filesystem",
    }


@router.post("/auth/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    address = request.client.host if request.client else "local"
    attempts[address] = [t for t in attempts[address] if t > time.time() - 60]
    if len(attempts[address]) >= 10:
        raise HTTPException(429, "Too many attempts. Wait one minute and try again.")
    attempts[address].append(time.time())
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Email or password is incorrect.")
    attempts[address].clear()
    settings = get_settings()
    response.set_cookie(
        "neuro_session",
        create_token(user.id),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.token_minutes * 60,
        path="/",
    )
    return {"id": user.id, "email": user.email}


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("neuro_session", path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email}


@router.get("/patients")
def patients(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return [
        patient_payload(db, p)
        for p in db.scalars(
            select(Patient).where(Patient.owner_id == user.id).order_by(Patient.created_at.desc())
        ).all()
    ]


@router.post("/patients", status_code=201)
def create_patient(
    body: PatientCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    item = Patient(**body.model_dump(), owner_id=user.id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This patient code already exists.") from None
    return patient_payload(db, item)


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return patient_payload(db, owned_patient(db, user, patient_id))


@router.post("/patients/{patient_id}/visits", status_code=201)
def create_visit(
    patient_id: str, body: VisitCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    patient = owned_patient(db, user, patient_id)
    db.add(Visit(patient_id=patient.id, **body.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A visit already exists on this day from baseline.") from None
    return patient_payload(db, patient)


@router.post("/visits/{visit_id}/upload", status_code=202)
def upload(
    visit_id: str, file: UploadFile, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    visit = owned_visit(db, user, visit_id)
    db.execute(select(Visit).where(Visit.id == visit_id).with_for_update()).scalar_one()
    if visit.mri_key:
        raise HTTPException(409, "This visit already has an MRI. Create another visit for a new scan.")
    name = (file.filename or "").lower()
    suffix = ".nii.gz" if name.endswith(".nii.gz") else ".nii" if name.endswith(".nii") else None
    if suffix is None:
        raise HTTPException(
            415, "Upload a .nii or .nii.gz file. Use the offline importer for OASIS header/image pairs."
        )
    if file.content_type not in {
        "application/octet-stream",
        "application/gzip",
        "application/x-gzip",
        "application/x-nifti",
        "application/nifti",
        None,
        "",
    }:
        raise HTTPException(415, "Unsupported MRI content type.")
    key, preview = new_key("raw", suffix), new_key("derived", ".png")
    path, thumbnail = resolve_key(key), resolve_key(preview)
    try:
        size = 0
        with path.open("wb") as dest:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > get_settings().max_upload_bytes:
                    raise HTTPException(413, "MRI exceeds the 100 MiB upload limit.")
                dest.write(chunk)
        metadata = render_preview(path, thumbnail)
        visit.mri_key, visit.preview_key, visit.metadata_json = key, preview, metadata
        db.flush()
        patient = owned_patient(db, user, visit.patient_id)
        # Only complete chronological inputs can form an analysis. Upload always queues a single
        # visit when earlier files are pending; a later explicit analysis includes the sequence.
        prior = db.scalars(
            select(Visit).where(
                Visit.patient_id == patient.id, Visit.days_from_baseline <= visit.days_from_baseline
            )
        ).all()
        active = db.scalar(
            select(Analysis).where(
                Analysis.patient_id == patient.id, Analysis.status.in_(["queued", "processing"])
            )
        )
        if not active and all(v.mri_key for v in prior):
            job = enqueue(db, patient, visit, "inference")
        else:
            job = Analysis(
                patient_id=patient.id,
                visit_id=visit.id,
                input_json=[
                    {"visit_id": visit.id, "days_from_baseline": visit.days_from_baseline, "mri_key": key}
                ],
                output_mode="inference",
            )
            db.add(job)
        db.commit()
        return analysis_payload(job)
    except (ValueError, HTTPException) as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        thumbnail.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(422, str(exc)) from None
    finally:
        file.file.close()


@router.get("/visits/{visit_id}/preview")
def preview(visit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> FileResponse:
    visit = owned_visit(db, user, visit_id)
    if not visit.preview_key or not resolve_key(visit.preview_key).is_file():
        raise HTTPException(404, "MRI preview is unavailable.")
    return FileResponse(resolve_key(visit.preview_key), media_type="image/png")


@router.get("/visits/{visit_id}/volume")
def volume(visit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> FileResponse:
    visit = owned_visit(db, user, visit_id)
    if not visit.mri_key or not resolve_key(visit.mri_key).is_file():
        raise HTTPException(404, "MRI volume is unavailable.")
    suffix = ".nii.gz" if visit.mri_key.endswith(".nii.gz") else ".nii"
    return FileResponse(
        resolve_key(visit.mri_key),
        media_type="application/octet-stream",
        filename=f"research-mri{suffix}",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/analysis/{visit_id}", status_code=202)
def start_analysis(
    visit_id: str, body: AnalysisCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    visit = owned_visit(db, user, visit_id)
    job = enqueue(db, owned_patient(db, user, visit.patient_id), visit, body.output_mode)
    db.commit()
    return analysis_payload(job)


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return analysis_payload(owned_analysis(db, user, analysis_id))


@router.get("/analysis/{analysis_id}/visits/{visit_id}/overlay")
def overlay(
    analysis_id: str, visit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> FileResponse:
    owned_analysis(db, user, analysis_id)
    item = db.scalar(select(Heatmap).where(Heatmap.analysis_id == analysis_id, Heatmap.visit_id == visit_id))
    if not item or not resolve_key(item.object_key).is_file():
        raise HTTPException(404, "Explanation is unavailable.")
    return FileResponse(resolve_key(item.object_key), media_type="image/png")


@router.get("/analysis/{analysis_id}/visits/{visit_id}/difference-volume")
def difference_volume(
    analysis_id: str, visit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> FileResponse:
    analysis = owned_analysis(db, user, analysis_id)
    if analysis.status != "completed" or not (analysis.result_json or {}).get("volume_overlays_ready"):
        raise HTTPException(404, "3D differences are unavailable for this result. Run local inference again.")
    item = db.scalar(select(Heatmap).where(Heatmap.analysis_id == analysis_id, Heatmap.visit_id == visit_id))
    if not item or not item.object_key.endswith("-overlay.png"):
        raise HTTPException(404, "3D difference volume is unavailable.")
    path = resolve_key(item.object_key.removesuffix("-overlay.png") + "-difference.nii.gz")
    if not path.is_file():
        raise HTTPException(404, "3D difference volume is unavailable. Run local inference again.")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename="research-difference.nii.gz",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/patients/{patient_id}/trajectory")
def trajectory(patient_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    owned_patient(db, user, patient_id)
    analysis = latest_completed(db, patient_id)
    return {"analysis": analysis_payload(analysis) if analysis else None}


@router.get("/patients/{patient_id}/biomarkers")
def biomarkers(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[dict]:
    owned_patient(db, user, patient_id)
    analysis = latest_completed(db, patient_id)
    if not analysis:
        return []
    return [
        {"name": b.name, "values": b.values_json, "unit": b.unit, "outputMode": analysis.output_mode}
        for b in db.scalars(select(Biomarker).where(Biomarker.analysis_id == analysis.id)).all()
    ]


@router.get("/patients/{patient_id}/heatmaps")
def heatmaps(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[dict]:
    owned_patient(db, user, patient_id)
    analysis = latest_completed(db, patient_id)
    if not analysis:
        return []
    return [
        {
            "visitId": h.visit_id,
            "method": h.method,
            "outputMode": analysis.output_mode,
            "url": f"/api/analysis/{analysis.id}/visits/{h.visit_id}/overlay",
        }
        for h in db.scalars(select(Heatmap).where(Heatmap.analysis_id == analysis.id)).all()
    ]


@router.post("/reports/{patient_id}", status_code=201)
def create_report(patient_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    patient = owned_patient(db, user, patient_id)
    analysis = latest_completed(db, patient_id)
    if not analysis:
        raise HTTPException(409, "Complete an analysis before generating a report.")
    visits = db.scalars(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.days_from_baseline)
    ).all()
    heatmap = db.scalar(
        select(Heatmap).where(Heatmap.analysis_id == analysis.id, Heatmap.visit_id == analysis.visit_id)
    )
    return build_report(patient, analysis, list(visits), resolve_key(heatmap.object_key) if heatmap else None)


@router.get("/reports")
def reports(user: User = Depends(current_user)) -> list[dict]:
    items = []
    directory = resolve_key("reports")
    for path in directory.glob("*.json"):
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if metadata.get("ownerId") == user.id:
            items.append({k: v for k, v in metadata.items() if k != "ownerId"})
    return sorted(items, key=lambda v: v["createdAt"], reverse=True)


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, user: User = Depends(current_user)) -> FileResponse:
    if not re.fullmatch(r"[a-f0-9]{32}", report_id):
        raise HTTPException(404, "Report not found.")
    path = resolve_key(f"reports/{report_id}.json")
    if not path.is_file():
        raise HTTPException(404, "Report not found.")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if metadata["ownerId"] != user.id:
        raise HTTPException(404, "Report not found.")
    return FileResponse(
        resolve_key(f"reports/{report_id}.pdf"),
        media_type="application/pdf",
        filename=f"NeuroPredict-{metadata['patientCode']}-{datetime.now():%Y%m%d}.pdf",
    )
