import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
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
from backend.app.schemas.contracts import (
    AnatomyReview,
    AnatomyForecastCreate,
    AnalysisCreate,
    AnalysisOut,
    Login,
    PatientCreate,
    VisitCreate,
)
from backend.app.services.analysis import enqueue, latest_completed, latest_anatomy, trained_model_version
from backend.app.services.reports import build_report
from backend.app.services.forecast import patient_forecast
from src.risk.release import readiness
from backend.app.services.storage import new_key, resolve_key
from ml.contracts import MODEL_VERSION
from ml.preprocessing import render_preview
from src.common import sha256
from src.fastsurfer.regions import REGIONS
from ml.anatomy.measurements import changes as anatomy_changes
from ml.contracts import ProgressionResult
from datetime import timezone

router = APIRouter()
attempts: dict[str, list[float]] = defaultdict(list)
DUMMY_HASH = hash_password("dummy-password-used-only-for-timing")


def owned_patient(db: Session, user: User, patient_id: str) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None or patient.owner_id != user.id:
        raise HTTPException(404, "Patient not found.")
    return patient


def owned_visit(db: Session, user: User, visit_id: str, *, lock: bool = False) -> Visit:
    visit = (
        db.scalar(
            select(Visit).where(Visit.id == visit_id).with_for_update()
            .execution_options(populate_existing=True)
        )
        if lock else db.get(Visit, visit_id)
    )
    if visit is None:
        raise HTTPException(404, "Visit not found.")
    owned_patient(db, user, visit.patient_id)
    return visit


@router.get("/patients/{patient_id}/forecast")
def forecast(
    patient_id: str,
    model_kind: Literal["clinical", "clinical_matched", "clinical_fastsurfer"] = "clinical_fastsurfer",
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    patient = owned_patient(db, user, patient_id)
    if get_settings().ml_only and model_kind != "clinical_fastsurfer":
        raise HTTPException(
            409, "ML-only serving allows only Clinical + FastSurfer. No clinical-only fallback."
        )
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
        .where(Analysis.patient_id == patient.id, Analysis.output_mode != "anatomy")
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    completed = latest_completed(db, patient.id)
    if get_settings().ml_only:
        latest = None
        completed = None  # anatomy has its own payload; never insert it into legacy charts
    return {
        "id": patient.id,
        "servingPolicy": "ml_only" if get_settings().ml_only else "research",
        "code": patient.code,
        "age": patient.age,
        "sex": patient.sex,
        "notes": patient.notes,
        "source": patient.source,
        "createdAt": patient.created_at.isoformat(),
        "visitCount": len(visits),
        "latestAnalysis": analysis_payload(latest) if latest else None,
        "latestCompleted": analysis_payload(completed) if completed else None,
        "latestAnatomy": analysis_payload(anatomy) if (anatomy := latest_anatomy(db, patient.id)) else None,
        "completedAnatomy": analysis_payload(anatomy)
        if (anatomy := latest_anatomy(db, patient.id, completed=True))
        else None,
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
        "modelVersion": "clinical-fastsurfer-serving-v1" if get_settings().ml_only else MODEL_VERSION,
        "baselineModelVersion": MODEL_VERSION,
        "trainedModelVersion": trained_version,
        "trainedModelReady": trained_version is not None,
        "storage": "local filesystem",
        "servingPolicy": "ml_only" if get_settings().ml_only else "research",
        "forecastReadiness": readiness(
            get_settings().forecast_artifact_dir, get_settings().forecast_processed_dir
        ),
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


@router.delete("/visits/{visit_id}")
def delete_pending_visit(
    visit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    visit = owned_visit(db, user, visit_id, lock=True)
    if visit.mri_key or visit.preview_key:
        raise HTTPException(409, "Only visits awaiting an MRI can be deleted.")
    jobs = db.scalars(select(Analysis).where(Analysis.patient_id == visit.patient_id))
    for job in jobs:
        if job.visit_id == visit.id or any(
            item.get("visit_id") == visit.id for item in job.input_json if isinstance(item, dict)
        ) or visit.id in (job.result_json or {}).get("visit_ids", []):
            raise HTTPException(409, "This visit is referenced by an analysis and cannot be deleted.")
    if db.scalar(select(Heatmap.id).where(Heatmap.visit_id == visit.id).limit(1)):
        raise HTTPException(409, "This visit has derived artifacts and cannot be deleted.")
    db.delete(visit)
    db.commit()
    return {"status": "deleted", "visitId": visit_id}


@router.post("/visits/{visit_id}/upload", status_code=202)
def upload(
    visit_id: str, file: UploadFile, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    visit = owned_visit(db, user, visit_id, lock=True)
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
        if get_settings().ml_only:
            db.commit()
            return {
                "status": "stored",
                "visitId": visit.id,
                "message": "MRI stored. Clinical metadata, offline FastSurfer processing, visual QC and a promoted model are required; no rule-based job was queued.",
            }
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
    job = enqueue(
        db, owned_patient(db, user, visit.patient_id), visit, body.output_mode, body.future_interval_days
    )
    db.commit()
    return analysis_payload(job)


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return analysis_payload(owned_analysis(db, user, analysis_id))


@router.get("/anatomy-model/readiness")
def anatomy_model_readiness(experimental: bool = False, user: User = Depends(current_user)) -> dict:
    from backend.app.services.anatomy_forecast import readiness as anatomy_readiness

    return anatomy_readiness(experimental=True) if experimental else anatomy_readiness()


@router.get("/anatomy-preview")
def saved_anatomy_preview(
    intervalDays: int = 229,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    from backend.app.services.anatomy_preview import metadata

    return metadata(db, user.id, intervalDays)


@router.get("/anatomy-preview/{artifact}")
def saved_anatomy_preview_artifact(
    artifact: str,
    intervalDays: int = 229,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> FileResponse:
    from backend.app.services.anatomy_preview import ARTIFACTS, load_preview
    from ml.anatomy.integrity import checked_file

    if artifact not in ARTIFACTS:
        raise HTTPException(404, "Saved preview artifact unavailable.")
    try:
        _, root, manifest = load_preview(db, user.id, intervalDays)
        path = checked_file(root, manifest["artifacts"][artifact])
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        raise HTTPException(404, "Saved preview missing or changed.") from None
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/patients/{patient_id}/anatomy-forecasts")
def anatomy_forecast_history(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[dict]:
    owned_patient(db, user, patient_id)
    jobs = db.scalars(
        select(Analysis)
        .where(
            Analysis.patient_id == patient_id,
            Analysis.output_mode == "anatomy",
            Analysis.status == "completed",
        )
        .order_by(Analysis.created_at.desc())
        .limit(30)
    ).all()
    return [
        analysis_payload(job)
        for job in jobs
        if (job.result_json or {}).get("anatomy", {}).get("forecast", {}).get("status") == "available"
    ]


@router.post("/analysis/{analysis_id}/forecast", status_code=202)
def create_anatomy_forecast(
    analysis_id: str,
    body: AnatomyForecastCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    from backend.app.services.anatomy_forecast import enqueue_forecast

    job = enqueue_forecast(
        db, owned_analysis(db, user, analysis_id), body.interval_days, body.cutoff_visit_id,
        experimental=body.experimental,
    )
    db.commit()
    return analysis_payload(job)


@router.get("/analysis/{analysis_id}/future/{artifact}")
def future_anatomy_artifact(
    analysis_id: str, artifact: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> FileResponse:
    from ml.anatomy.integrity import checked_file

    job = owned_analysis(db, user, analysis_id)
    result = (
        ProgressionResult.model_validate(job.result_json)
        if job.status == "completed" and job.output_mode == "anatomy"
        else None
    )
    forecast = result.anatomy.forecast if result and result.anatomy else None
    released = next((a for a in forecast.artifacts if a.name == artifact), None) if forecast else None
    if not forecast or forecast.status != "available" or not released:
        raise HTTPException(404, "Matching evaluated future artifact unavailable.")
    root = resolve_key(f"derived/{job.id}/future")
    try:
        manifest = json.loads((root / "future-artifacts.json").read_text())
        if (
            manifest["cutoff_visit_id"] != forecast.cutoff_visit_id
            or manifest["interval_days"] != forecast.interval_days
            or manifest["model_sha256"] != forecast.model_sha256
            or manifest["version"] != forecast.spatial_model_version
            or manifest["release_sha256"] != forecast.release_sha256
            or manifest["source_sha256"] != [v.source_sha256 for v in result.anatomy.visits]
        ):
            raise ValueError("Future metadata changed")
        entry = manifest["artifacts"][artifact]
        expected_name = artifact + (".gii" if released.kind == "mesh" else ".nii.gz")
        if (
            entry["sha256"] != released.sha256
            or entry["kind"] != released.kind
            or entry["relative_path"] != expected_name
        ):
            raise ValueError("Future artifact no longer matches completed result")
        path = checked_file(root, entry)
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(404, "Future artifact missing or changed; no substitute generated.") from None
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=expected_name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/analysis/{analysis_id}/forecast-comparison")
def forecast_comparison(
    analysis_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    from backend.app.services.forecast_comparison import compare

    job = owned_analysis(db, user, analysis_id)
    # Reuse owned, source-bound and hash-verified artifact handlers.
    mri = future_anatomy_artifact(analysis_id, "mri", db, user)
    labels = future_anatomy_artifact(analysis_id, "labels", db, user)
    field = future_anatomy_artifact(analysis_id, "pull", db, user)
    result = ProgressionResult.model_validate(job.result_json)
    forecast = result.anatomy.forecast
    cutoff = next(v for v in result.anatomy.visits if v.visit_id == forecast.cutoff_visit_id)
    visit = owned_visit(db, user, cutoff.visit_id)
    snapshot = next(item for item in job.input_json if item["visit_id"] == cutoff.visit_id)
    if visit.patient_id != job.patient_id or not visit.mri_key or visit.mri_key != snapshot["mri_key"]:
        raise HTTPException(409, "Cutoff MRI changed since forecast generation")
    source = resolve_key(visit.mri_key)
    try:
        source_matches = sha256(source) == cutoff.source_sha256
    except OSError:
        source_matches = False
    if not source_matches:
        raise HTTPException(409, "Cutoff MRI changed since forecast generation")
    observed_labels = anatomy_artifact(analysis_id, cutoff.visit_id, "segmentation", db, user)
    try:
        comparison = compare(source, Path(observed_labels.path), Path(mri.path), Path(labels.path), Path(field.path),
            cutoff.volumes_mm3, forecast.volumes_mm3, verified_units=snapshot.get("source_units_verified", False))
    except (ValueError, OSError, KeyError) as error:
        raise HTTPException(409, "Forecast comparison unavailable: " + str(error)) from None
    return camel({"cutoff_visit_id": cutoff.visit_id, "interval_days": forecast.interval_days, **comparison})


@router.get("/analysis/{analysis_id}/visits/{visit_id}/rating-alignment")
def rating_alignment(
    analysis_id: str, visit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> FileResponse:
    from ml.anatomy.integrity import rating_files

    job = owned_analysis(db, user, analysis_id)
    result = (
        ProgressionResult.model_validate(job.result_json)
        if job.status == "completed" and job.output_mode == "anatomy"
        else None
    )
    anatomy = result.anatomy if result else None
    item = next((v for v in anatomy.visits if v.visit_id == visit_id), None) if anatomy else None
    if not item or item.ratings.status not in {"pending_alignment_qc", "ok"}:
        raise HTTPException(404, "Automatic-rating alignment unavailable.")
    try:
        index = result.visit_ids.index(visit_id)
        root = resolve_key(f"derived/{job.id}")
        rating_files(root, index, item)
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(404, "Rating alignment changed or missing.") from None
    return FileResponse(
        root / f"rating_{index}/rating_mni_dof_6.nii",
        media_type="application/octet-stream",
        filename="rating-alignment.nii",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/analysis/{analysis_id}/rating-qc/{visit_id}")
def review_rating_alignment(
    analysis_id: str,
    visit_id: str,
    body: AnatomyReview,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    from ml.anatomy.integrity import measurement_files, rating_files
    from ml.anatomy.ratings import parse_avra_csv
    from src.common import write_json

    job = owned_analysis(db, user, analysis_id)
    db.execute(select(Analysis).where(Analysis.id == job.id).with_for_update()).scalar_one()
    if job.status != "completed" or job.output_mode != "anatomy":
        raise HTTPException(409, "Complete automatic scoring before alignment review.")
    result = ProgressionResult.model_validate(job.result_json)
    item = (
        next((v for v in result.anatomy.visits if v.visit_id == visit_id), None) if result.anatomy else None
    )
    if not item or item.qc != "passed" or item.ratings.status != "pending_alignment_qc":
        raise HTTPException(409, "Review the segmentation and pending automatic alignment first.")
    root = resolve_key(f"derived/{job.id}")
    try:
        index = result.visit_ids.index(visit_id)
        snapshot = next(s for s in job.input_json if s["visit_id"] == visit_id)
        measurement_files(root, job.patient_id, index, item, resolve_key(snapshot["mri_key"]))
        provenance = rating_files(root, index, item)
        scores = parse_avra_csv(root / f"rating_{index}/rating.csv", alignment_verified=True)
        if scores.status != "ok":
            raise ValueError("Invalid automatic scores")
    except (ValueError, OSError, KeyError, TypeError, StopIteration):
        raise HTTPException(409, "Automatic rating, alignment or source integrity failed.") from None
    provenance.update(
        alignment_qc="passed", reviewer_id=user.id, reviewed_at=datetime.now(timezone.utc).isoformat()
    )
    write_json(root / f"rating_{index}/provenance.json", provenance)
    scores.provenance_sha256 = sha256(root / f"rating_{index}/provenance.json")
    scores.reviewer_id, scores.reviewed_at = user.id, provenance["reviewed_at"]
    item.ratings = scores
    job.result_json = result.model_dump()
    db.commit()
    return analysis_payload(job)


@router.get("/analysis/{analysis_id}/visits/{visit_id}/anatomy/{artifact}")
def anatomy_artifact(
    analysis_id: str,
    visit_id: str,
    artifact: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> FileResponse:
    job = owned_analysis(db, user, analysis_id)
    if (
        job.status != "completed"
        or job.output_mode != "anatomy"
        or artifact not in {"regions", "segmentation", *REGIONS}
        or visit_id not in (job.result_json or {}).get("visit_ids", [])
    ):
        raise HTTPException(404, "Anatomical artifact unavailable.")
    directory = resolve_key(f"derived/{job.id}")
    try:
        manifest = json.loads((directory / "anatomy-artifacts.json").read_text())
        entry = manifest["visits"][visit_id][artifact]
        path = (directory / entry["relative_path"]).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or sha256(path) != entry["sha256"]:
            raise ValueError("Changed artifact")
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(
            404, "Anatomical artifact missing or changed. No substitute was generated."
        ) from None
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename="measured-regions.nii.gz",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/analysis/{analysis_id}/anatomy-qc/{visit_id}")
def review_anatomy(
    analysis_id: str,
    visit_id: str,
    body: AnatomyReview,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    job = owned_analysis(db, user, analysis_id)
    db.execute(select(Analysis).where(Analysis.id == job.id).with_for_update()).scalar_one()
    if job.output_mode != "anatomy" or job.status != "completed":
        raise HTTPException(409, "Complete native segmentation before visual review.")
    result = ProgressionResult.model_validate(job.result_json)
    anatomy = result.anatomy
    item = next((v for v in anatomy.visits if v.visit_id == visit_id), None) if anatomy else None
    if not item:
        raise HTTPException(404, "Visit not included in this anatomy result.")
    if item.qc != "pending_review":
        raise HTTPException(409, "Only a pending segmentation can receive a visual review.")
    try:
        source = next(s for s in job.input_json if s["visit_id"] == visit_id)
        if sha256(resolve_key(source["mri_key"])) != item.source_sha256:
            raise ValueError("Source changed")
        directory = resolve_key(f"derived/{job.id}")
        index = result.visit_ids.index(visit_id)
        seg = directory / f"fastsurfer/scan_{index}/mri/aparc.DKTatlas+aseg.deep.mgz"
        stats_relative = "stats/aseg+DKT.VINN.stats"
        scan_directory = directory / f"fastsurfer/scan_{index}"
        stats = scan_directory / stats_relative
        processing = json.loads((scan_directory / "processing.json").read_text())
        if (
            sha256(seg) != item.segmentation_sha256
            or sha256(stats) != item.statistics_sha256
            or processing.get("status") != "completed"
            or processing.get("version") != item.fastsurfer_version
            or processing.get("digest") != item.container_digest
            or processing.get("scan_id") != f"scan_{index}"
            or processing.get("patient_id") != job.patient_id
            or processing.get("source_sha256") != item.source_sha256
            or processing.get("output_sha256", {}).get(stats_relative) != item.statistics_sha256
            or processing.get("output_sha256", {}).get("mri/aparc.DKTatlas+aseg.deep.mgz")
            != item.segmentation_sha256
        ):
            raise ValueError("FastSurfer source or outputs changed")
        manifest = json.loads((directory / "anatomy-artifacts.json").read_text())
        entries = manifest["visits"][visit_id]
        if manifest.get("version") != "longitudinal-anatomy-v1" or set(entries) != {
            "regions",
            "segmentation",
            *REGIONS,
        }:
            raise ValueError("Incomplete anatomy artifact set")
        for name, entry in entries.items():
            relative = Path(entry["relative_path"])
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
                or relative != Path(f"visit_{index}") / f"{name}.nii.gz"
            ):
                raise ValueError("Invalid anatomy artifact manifest")
            artifact_path = (directory / entry["relative_path"]).resolve()
            if not artifact_path.is_relative_to(directory) or sha256(artifact_path) != entry["sha256"]:
                raise ValueError("Review artifacts changed")
    except (ValueError, OSError, KeyError, TypeError, StopIteration):
        raise HTTPException(409, "Source or anatomy artifacts changed; review cannot be recorded.") from None
    item.qc, item.reviewer_id, item.reviewed_at = "passed", user.id, datetime.now(timezone.utc).isoformat()
    anatomy.changes = anatomy_changes(anatomy.visits)
    job.result_json = result.model_dump()
    db.commit()
    return analysis_payload(job)


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
def create_report(
    patient_id: str,
    analysis_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    patient = owned_patient(db, user, patient_id)
    analysis = owned_analysis(db, user, analysis_id) if analysis_id else latest_completed(db, patient_id)
    if analysis and (analysis.patient_id != patient_id or analysis.status != "completed"):
        raise HTTPException(409, "Select a completed analysis for this patient.")
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
