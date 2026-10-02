import json
import logging
import time
from pathlib import Path
from threading import Event, Thread

from sqlalchemy import case, select, text, update

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal, engine
from backend.app.models import Analysis, Biomarker, Heatmap, Patient
from backend.app.services.analysis import cache_key, trained_model_version
from backend.app.services.storage import resolve_key
from backend.app.services.compute import gpu_slot
from ml.contracts import ProgressionResult, VisitInput
from ml.inference import run_pipeline
from ml.nwbv_contract import NWBV_REFERENCE_KEY, NwbvAgeReferenceBiomarker

logger = logging.getLogger(__name__)


def heartbeat_loop(stop: Event, experimental_only: bool = False) -> None:
    """Remain observable while a native inference job takes tens of minutes."""
    from src.common import write_json

    heartbeat: Path = resolve_key("worker-heartbeat.txt")
    while not stop.is_set():
        temporary = heartbeat.with_suffix(".tmp")
        temporary.write_text(str(time.time()), encoding="utf-8")
        temporary.replace(heartbeat)
        write_json(
            resolve_key("worker-capabilities.json"),
            {
                "timestamp": time.time(),
                "workerMode": "experimental_forecasts_only" if experimental_only else "all_analysis",
                "capabilities": ["anatomy-experimental-forecast-v1"]
                if experimental_only
                else [
                    "longitudinal-anatomy-v1",
                    "anatomy-forecast-v1",
                    "nwbv-age-reference-v1",
                    "anatomy-experimental-forecast-v1",
                ],
            },
        )
        stop.wait(min(get_settings().worker_poll_seconds, 5.0))


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
            if get_settings().ml_only and job.output_mode != "anatomy":
                job.status, job.stage = "failed", "Legacy analysis disabled"
                job.error = "ML-only serving requires Clinical + FastSurfer. No legacy model was executed."
                db.commit()
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
        if mode == "anatomy":
            from ml.anatomy.pipeline import run_anatomy
            from ml.anatomy.ratings import AUTOMATIC_RESEARCH_RATING_POLICY

            failure_message = "Anatomy processing failed. Verify Docker availability, pinned image, native MRI geometry and private execution logs. No synthetic anatomy or scores were substituted."
            inputs = [{**s, "mri_path": str(resolve_key(s["mri_key"]))} for s in snapshot]
            spec = snapshot[-1].get("forecast_spec")
            if spec:
                from backend.app.services.anatomy_forecast import execute_forecast, result_hash

                with SessionLocal() as db:
                    source = db.get(Analysis, spec["source_analysis_id"])
                    patient = db.get(Patient, patient_id)
                    if (
                        not source
                        or not patient
                        or source.patient_id != patient_id
                        or source.status != "completed"
                        or result_hash(source.result_json) != spec["source_result_sha256"]
                        or snapshot[-1]["visit_id"] not in (source.result_json or {}).get("visit_ids", [])
                    ):
                        raise ValueError("Pinned reviewed anatomy source changed")
                    payload, source_inputs, source_id, subject = (
                        source.result_json,
                        source.input_json,
                        source.id,
                        patient.code,
                    )
                failure_message = "Forecast generation failed. Verify source integrity, registration coverage, positive deformation geometry and the pinned checkpoint. See the private worker log for the specific failure."
                update_progress(
                    analysis_id,
                    20,
                    "Experimental cutoff-local registration and spatial prediction"
                    if spec.get("is_research_candidate")
                    else "Cutoff-local registration and evaluated spatial prediction",
                )
                result = execute_forecast(
                    payload,
                    source_inputs,
                    resolve_key(f"derived/{source_id}"),
                    resolve_key(artifact_prefix),
                    subject,
                    snapshot[-1]["future_interval_days"],
                    spec["release_sha256"],
                    snapshot[-1]["visit_id"],
                    allow_unreviewed_research=spec.get("is_research_candidate", False),
                    candidate_dir=spec.get("candidate_dir"),
                )
            else:
                result = run_anatomy(
                    patient_id,
                    inputs,
                    resolve_key(artifact_prefix),
                    lambda p, s: update_progress(analysis_id, p, s),
                    rating_runtime=get_settings().avra_runtime_manifest,
                    automatic_research_values=all(
                        s.get("rating_policy", AUTOMATIC_RESEARCH_RATING_POLICY)
                        == AUTOMATIC_RESEARCH_RATING_POLICY
                        for s in snapshot
                    ),
                )
            result = ProgressionResult.model_validate(result.model_dump())
            if (
                result.model_version != pinned_version
                or result.output_mode != "anatomy"
                or result.patient_id != patient_id
                or result.visit_ids != [s["visit_id"] for s in snapshot]
                or result.days_from_baseline != [s["days_from_baseline"] for s in snapshot]
                or result.anatomy is None
                or result.anatomy.forecast.interval_days != snapshot[-1]["future_interval_days"]
                or any(v.source_sha256 != s["source_sha256"] for v, s in zip(result.anatomy.visits, snapshot))
            ):
                raise ValueError("Anatomy result does not match pinned job inputs")
        elif mode == "trained":
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
        from backend.app.services.nwbv_reference import attach

        result = attach(result, snapshot)
        with SessionLocal() as db:
            job = db.get(Analysis, analysis_id)
            for name, values in result.biomarkers.items():
                structured = name == NWBV_REFERENCE_KEY and isinstance(values, NwbvAgeReferenceBiomarker)
                db.add(
                    Biomarker(
                        analysis_id=job.id,
                        name=name,
                        values_json=values.model_dump() if structured else values,
                        unit="descriptive_reference" if structured else "fraction",
                    )
                )
            for index, visit_id in enumerate(result.visit_ids if mode != "anatomy" else []):
                db.add(
                    Heatmap(
                        analysis_id=job.id,
                        visit_id=visit_id,
                        object_key=f"{artifact_prefix}/{index}-overlay.png",
                    )
                )
            if mode != "anatomy":
                result.heatmap_url = f"/api/analysis/{job.id}/visits/{result.selected_visit}/overlay"
            job.result_json = result.model_dump()
            job.score = (
                None
                if mode == "anatomy"
                else result.prediction.score
                if result.prediction
                else result.risk_scores[-1]
            )
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


def claim_next(*, experimental_only: bool = False) -> str | None:
    with SessionLocal() as db:
        query = select(Analysis).where(Analysis.status == "queued")
        if experimental_only:
            query = query.where(Analysis.stage == "Experimental forecast queued")
        job = db.scalar(
            query.order_by(
                case((Analysis.stage == "Experimental forecast queued", 0), else_=1), Analysis.created_at
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status, job.stage = (
            "processing",
            "Experimental forecast started"
            if job.stage == "Experimental forecast queued"
            else "Worker started",
        )
        db.commit()
        return job.id


def recover_interrupted(*, experimental_only: bool = False) -> None:
    with SessionLocal() as db:
        query = update(Analysis).where(Analysis.status == "processing")
        if experimental_only:
            query = query.where(Analysis.stage.like("Experimental%"))
        db.execute(
            query.values(
                status="failed",
                stage="Worker restarted",
                error="Analysis was interrupted by a worker restart. Start analysis again.",
            )
        )
        db.commit()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experimental-only",
        action="store_true",
        help="Process CPU experimental forecasts while MRI/Docker preprocessing is paused",
    )
    args = parser.parse_args()
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
        recover_interrupted(experimental_only=args.experimental_only)
        logger.info("Local analysis worker ready")
        stop = Event()
        heartbeat_thread = Thread(target=heartbeat_loop, args=(stop, args.experimental_only), daemon=True)
        heartbeat_thread.start()
        try:
            while True:
                with gpu_slot(wait=False) as acquired:
                    job_id = (
                        claim_next(experimental_only=True)
                        if acquired and args.experimental_only
                        else claim_next()
                        if acquired
                        else None
                    )
                    if job_id:
                        execute(job_id)
                if not job_id:
                    time.sleep(get_settings().worker_poll_seconds)
        finally:
            stop.set()
            heartbeat_thread.join(timeout=5)


if __name__ == "__main__":
    main()
