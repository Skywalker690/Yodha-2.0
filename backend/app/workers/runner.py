import json
import logging
import time
from pathlib import Path

from sqlalchemy import select, text, update

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal, engine
from backend.app.models import Analysis, Biomarker, Heatmap, Patient
from backend.app.services.analysis import cache_key, trained_model_version
from backend.app.services.storage import resolve_key
from ml.contracts import ProgressionResult, VisitInput
from ml.inference import run_pipeline

logger = logging.getLogger(__name__)


def update_progress(analysis_id: str, progress: int, stage: str) -> None:
    with SessionLocal() as db:
        item = db.get(Analysis, analysis_id)
        if item:
            item.progress, item.stage = progress, stage
            db.commit()


def execute(analysis_id: str) -> None:
    """Run outside the HTTP process; only validated results are persisted as completed."""
    failure_message = "Analysis could not be completed. Verify the MRI files and local worker, then retry."
    try:
        with SessionLocal() as db:
            job = db.get(Analysis, analysis_id)
            if not job or job.status not in {"queued", "processing"}:
                return
            job.status, job.progress, job.stage = "processing", 5, "Loading chronological visits"
            db.commit()
            snapshot, patient_id, mode = job.input_json, job.patient_id, job.output_mode
            pinned_version = job.model_version
            subject_code = None
            if mode == "trained":
                failure_message = "Trained analysis inputs are unavailable. No baseline fallback is used."
                patient = db.get(Patient, patient_id)
                if patient is None:
                    raise ValueError("Patient is unavailable")
                subject_code = patient.code
        artifact_prefix = f"derived/{analysis_id}"
        if mode == "trained":
            failure_message = (
                "The trained checkpoint is unavailable, invalid, or changed since enqueue. "
                "Restore the pinned checkpoint and retry. No baseline fallback is used."
            )
            if trained_model_version() != pinned_version:
                raise ValueError("Checkpoint no longer matches queued version")
            from ml.trained_inference import run_trained_pipeline, validate_covariates

            failure_message = (
                "Trained analysis failed: verify the recorded visit covariates, chronological MRI inputs, "
                "and pinned checkpoint. No baseline fallback is used."
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
            validate_covariates(inputs)
            raw_result = run_trained_pipeline(
                patient_id=patient_id,
                visits=inputs,
                output_dir=resolve_key(artifact_prefix),
                checkpoint_path=get_settings().trained_model_path,
                expected_version=pinned_version,
                subject_code=subject_code,
                progress=lambda p, s: update_progress(analysis_id, p, s),
            )
            result = ProgressionResult.model_validate(
                raw_result.model_dump() if isinstance(raw_result, ProgressionResult) else raw_result
            )
            if (
                result.output_mode != "trained"
                or result.model_version != pinned_version
                or result.patient_id != patient_id
                or result.visit_ids != [item["visit_id"] for item in snapshot]
                or result.days_from_baseline != [item["days_from_baseline"] for item in snapshot]
                or result.selected_visit != snapshot[-1]["visit_id"]
                or result.prediction is None
                or result.risk_scores
            ):
                raise ValueError("Trained result does not match pinned job inputs")
        elif mode == "precomputed":
            payload = json.loads(resolve_key(cache_key(snapshot)).read_text(encoding="utf-8"))
            result = ProgressionResult.model_validate(payload["result"])
            if result.patient_id != patient_id or result.visit_ids != [s["visit_id"] for s in snapshot]:
                raise ValueError("Cached inputs do not match")
            artifact_prefix = payload["artifact_prefix"]
            if not all(
                resolve_key(f"{artifact_prefix}/{i}-overlay.png").is_file() for i in range(len(snapshot))
            ):
                raise ValueError("Cached visualization is unavailable. Run inference again.")
            result.output_mode = "precomputed"
            if result.volume_overlays_ready and not all(
                resolve_key(f"{artifact_prefix}/{i}-difference.nii.gz").is_file()
                for i in range(len(snapshot))
            ):
                raise ValueError("Cached 3D visualization is unavailable. Run inference again.")
            update_progress(analysis_id, 85, "Restoring versioned precomputed result")
        else:
            inputs = [
                VisitInput(
                    visit_id=s["visit_id"],
                    days_from_baseline=s["days_from_baseline"],
                    mri_path=str(resolve_key(s["mri_key"])),
                )
                for s in snapshot
            ]
            result = run_pipeline(
                patient_id,
                inputs,
                resolve_key(artifact_prefix),
                mode,
                lambda p, s: update_progress(analysis_id, p, s),
            )
            if mode == "inference":
                cache = resolve_key(cache_key(snapshot))
                cache.parent.mkdir(parents=True, exist_ok=True)
                temporary = cache.with_suffix(".tmp")
                temporary.write_text(
                    json.dumps({"result": result.model_dump(), "artifact_prefix": artifact_prefix}),
                    encoding="utf-8",
                )
                temporary.replace(cache)
        with SessionLocal() as db:
            job = db.get(Analysis, analysis_id)
            for name, values in result.biomarkers.items():
                db.add(Biomarker(analysis_id=job.id, name=name, values_json=values, unit="fraction"))
            for index, visit_id in enumerate(result.visit_ids):
                db.add(
                    Heatmap(
                        analysis_id=job.id,
                        visit_id=visit_id,
                        object_key=f"{artifact_prefix}/{index}-overlay.png",
                    )
                )
            result.heatmap_url = f"/api/analysis/{job.id}/visits/{result.selected_visit}/overlay"
            job.result_json = result.model_dump()
            job.score = result.prediction.score if result.prediction else result.risk_scores[-1]
            job.model_version = result.model_version
            job.confidence = result.confidence
            job.status, job.progress, job.stage = "completed", 100, "Analysis complete"
            db.commit()
    except Exception:
        logger.exception("Analysis %s failed", analysis_id)
        with SessionLocal() as db:
            job = db.get(Analysis, analysis_id)
            if job:
                job.status, job.stage = "failed", "Analysis failed"
                job.error = failure_message
                db.commit()


def claim_next() -> str | None:
    with SessionLocal() as db:
        job = db.scalar(
            select(Analysis)
            .where(Analysis.status == "queued")
            .order_by(Analysis.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status, job.stage = "processing", "Worker started"
        db.commit()
        return job.id


def recover_interrupted() -> None:
    with SessionLocal() as db:
        db.execute(
            update(Analysis)
            .where(Analysis.status == "processing")
            .values(
                status="failed",
                stage="Worker restarted",
                error="Analysis was interrupted by a worker restart. Start analysis again.",
            )
        )
        db.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Keep a session-level advisory lock so an accidental second worker cannot
    # mark another worker's live processing jobs as interrupted.
    with engine.connect() as lock_connection:
        if engine.dialect.name == "postgresql":
            acquired = lock_connection.execute(text("SELECT pg_try_advisory_lock(202609301)")).scalar()
            lock_connection.commit()
            if not acquired:
                raise SystemExit(
                    "Another local analysis worker is already running. Stop it before starting this one."
                )
        recover_interrupted()
        heartbeat: Path = resolve_key("worker-heartbeat.txt")
        logger.info("Local analysis worker ready")
        while True:
            heartbeat.write_text(str(time.time()), encoding="utf-8")
            job_id = claim_next()
            if job_id:
                execute(job_id)
            else:
                time.sleep(get_settings().worker_poll_seconds)


if __name__ == "__main__":
    main()
