"""Reuse reviewed measurements; queue inference on the existing serialized worker."""

import hashlib
import json
import shutil
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Analysis, Patient
from backend.app.services.storage import resolve_key
from ml.anatomy.contracts import VERSION
from ml.anatomy.integrity import measurement_files, rating_files
from ml.contracts import ProgressionResult
from src.common import sha256


def result_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def readiness() -> dict:
    try:
        from ml.anatomy.forecasting import release

        data, fingerprint = release(get_settings().anatomy_release_dir)
        return {
            "status": "available",
            "releaseSha256": fingerprint,
            "intervalsDays": [0, *data["supported_intervals_days"]],
            "clinicalValidation": False,
        }
    except (ValueError, OSError, KeyError, TypeError):
        return {
            "status": "unavailable",
            "intervalsDays": [],
            "reason": "No evaluated native-anatomy release. Complete reviewed anatomy, scoring, registration, training and held-out validation.",
        }


def enqueue_forecast(db: Session, source: Analysis, interval: int, cutoff_id: str | None = None) -> Analysis:
    if source.status != "completed" or source.output_mode != "anatomy":
        raise HTTPException(409, "Complete and review anatomical measurements before forecasting.")
    result = ProgressionResult.model_validate(source.result_json)
    cutoff_id = cutoff_id or source.visit_id
    if cutoff_id not in result.visit_ids:
        raise HTTPException(422, "Select a cutoff included in this anatomical history.")
    end = result.visit_ids.index(cutoff_id) + 1
    history = result.anatomy.visits[:end] if result.anatomy else []
    if not 2 <= len(history) <= 5 or any(v.qc != "passed" or v.ratings.status != "ok" for v in history):
        raise HTTPException(
            409, "Two-to-five reviewed segmentations and alignment-reviewed automatic scores required."
        )
    state = readiness()
    if state["status"] != "available":
        raise HTTPException(409, state["reason"])
    if interval not in state["intervalsDays"]:
        raise HTTPException(422, "This interval has no evaluated support in the promoted anatomy model.")
    db.execute(select(Patient).where(Patient.id == source.patient_id).with_for_update()).scalar_one()
    if db.scalar(
        select(Analysis).where(
            Analysis.patient_id == source.patient_id, Analysis.status.in_(["queued", "processing"])
        )
    ):
        raise HTTPException(409, "An analysis is already running for this patient.")
    snapshot = [{k: v for k, v in item.items() if k != "forecast_spec"} for item in source.input_json[:end]]
    for item in snapshot:
        item["future_interval_days"] = interval
    snapshot[-1]["forecast_spec"] = {
        "source_analysis_id": source.id,
        "source_result_sha256": result_hash(source.result_json),
        "release_sha256": state["releaseSha256"],
    }
    job = Analysis(
        patient_id=source.patient_id,
        visit_id=cutoff_id,
        output_mode="anatomy",
        model_version=VERSION,
        input_json=snapshot,
    )
    db.add(job)
    db.flush()
    return job


def execute_forecast(
    source_payload: dict,
    source_inputs: list[dict],
    source_root: Path,
    output: Path,
    subject_id: str,
    interval: int,
    expected_release: str,
    cutoff_id: str | None = None,
) -> ProgressionResult:
    from ml.anatomy.forecasting import predict

    result = ProgressionResult.model_validate(source_payload)
    if result.anatomy is None:
        raise ValueError("Reviewed measurement source missing")
    cutoff_id = cutoff_id or result.visit_ids[-1]
    end = result.visit_ids.index(cutoff_id) + 1
    from ml.nwbv_contract import NWBV_REFERENCE_KEY

    # The worker recomputes this observed support value for the selected cutoff.
    result.biomarkers.pop(NWBV_REFERENCE_KEY, None)
    result.visit_ids = result.visit_ids[:end]
    result.days_from_baseline = result.days_from_baseline[:end]
    result.selected_visit = cutoff_id
    result.anatomy.visits = result.anatomy.visits[:end]
    from ml.anatomy.measurements import changes

    result.anatomy.changes = changes(result.anatomy.visits)
    records, copies = [], []
    for index, visit in enumerate(result.anatomy.visits):
        if visit.qc != "passed" or visit.ratings.status != "ok":
            raise ValueError("Source review changed")
        snapshot = next(s for s in source_inputs if s["visit_id"] == visit.visit_id)
        files = measurement_files(
            source_root, result.patient_id, index, visit, resolve_key(snapshot["mri_key"])
        )
        rating_files(source_root, index, visit, reviewed=True)
        records.append(
            {
                "visit_id": visit.visit_id,
                "mri_path": str(resolve_key(snapshot["mri_key"])),
                "labels_path": str(files["segmentation"]),
                "labels_sha256": sha256(files["segmentation"]),
                "source_units_verified": snapshot.get("source_units_verified", False),
            }
        )
        copies.extend(files.values())
        copies.extend(
            source_root / f"fastsurfer/scan_{index}" / name
            for name in ("processing.json", "stats/aseg+DKT.VINN.stats", "mri/aparc.DKTatlas+aseg.deep.mgz")
        )
        copies.extend(
            source_root / f"rating_{index}" / name
            for name in ("rating.csv", "rating_mni_dof_6.nii", "rating_mni_dof_6.mat", "provenance.json")
        )
    output.mkdir(parents=True, exist_ok=False)
    for path in [source_root / "anatomy-artifacts.json", *copies]:
        target = output / path.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    result.anatomy.forecast = predict(
        get_settings().anatomy_release_dir,
        subject_id,
        result.anatomy.visits,
        records,
        interval,
        output / "future",
        expected_release,
    )
    result.anatomy.spatial_registration = "cutoff_local_rigid"
    result.caveats = [
        "Future MRI and mask-boundary meshes are model-generated structural research estimates, not acquired scans or a clinical diagnosis.",
        "Only observed data through the cutoff conditions the model; future scans are never serving inputs.",
    ]
    return ProgressionResult.model_validate(result.model_dump())
