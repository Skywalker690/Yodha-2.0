"""Read-only, owner-scoped display of a saved retrospective evaluation example."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Analysis, Patient, Visit
from backend.app.services.storage import resolve_key
from ml.anatomy.integrity import checked_file
from src.common import sha256

ARTIFACTS = {
    "mri": "mri",
    "labels": "labels",
    "brain_mesh": "mesh",
    "hippocampus_left_mm3": "mesh",
    "hippocampus_right_mm3": "mesh",
}
PREVIEW_INTERVALS = {229, 365, 731, 1096}


def observed_labels_url(db: Session, patient_id: str, cutoff: dict) -> str | None:
    """Use the acquired cutoff's measured mask, matched to the saved input hashes."""
    if not cutoff.get("segmentation_sha256"):
        return None
    jobs = db.scalars(
        select(Analysis)
        .where(
            Analysis.patient_id == patient_id,
            Analysis.output_mode == "anatomy",
            Analysis.status == "completed",
        )
        .order_by(Analysis.created_at.desc())
    )
    for job in jobs:
        result = job.result_json or {}
        if cutoff["visit_id"] not in result.get("visit_ids", []):
            continue
        visits = (result.get("anatomy") or {}).get("visits", [])
        if any(
            visit.get("visit_id") == cutoff["visit_id"]
            and visit.get("source_sha256") == cutoff["source_sha256"]
            and visit.get("segmentation_sha256") == cutoff["segmentation_sha256"]
            for visit in visits
        ):
            return f"/api/analysis/{job.id}/visits/{cutoff['visit_id']}/anatomy/regions"
    return None


def _preview_root(interval_days: int) -> Path:
    if interval_days not in PREVIEW_INTERVALS:
        raise ValueError("This saved prototype interval is unavailable.")
    base = get_settings().anatomy_preview_dir.resolve()
    root = base if interval_days == 229 else base / str(interval_days)
    if root.resolve().parent != base and root.resolve() != base:
        raise ValueError("Preview profile escaped its configured directory.")
    return root


def load_preview(
    db: Session, owner_id: str, interval_days: int = 229
) -> tuple[dict, Path, dict]:
    """Validate saved files and original subject history without invoking inference."""
    root = _preview_root(interval_days)
    descriptor = json.loads((root / "preview.json").read_text())
    if descriptor["version"] != "saved-anatomy-preview-v1":
        raise ValueError("Unsupported preview profile")
    case = json.loads(checked_file(root, descriptor["case"]).read_text())
    manifest = json.loads(checked_file(root, descriptor["manifest"]).read_text())
    report = json.loads(checked_file(root, descriptor["evaluation"]).read_text())
    patient = db.scalar(
        select(Patient).where(Patient.owner_id == owner_id, Patient.code == case["subject_id"])
    )
    if patient is None:
        raise ValueError("Saved example is not owned by this researcher")
    history = case["history"]
    if (
        len(history) < 2
        or manifest["cutoff_visit_id"] != history[-1]["visit_id"]
        or manifest["interval_days"] != case["interval_days"]
        or manifest["interval_days"] != interval_days
        or manifest["interval_days"] <= 0
        or manifest["source_sha256"] != [v["source_sha256"] for v in history]
        or report["version"] != manifest["version"]
        or report["synthetic"] is not False
    ):
        raise ValueError("Saved preview provenance does not match its original case")
    for item in history:
        visit = db.get(Visit, item["visit_id"])
        if (
            visit is None
            or visit.patient_id != patient.id
            or visit.days_from_baseline != item["days_from_baseline"]
            or not visit.mri_key
            or sha256(resolve_key(visit.mri_key)) != item["source_sha256"]
        ):
            raise ValueError("Saved preview source history changed")
    for name, kind in ARTIFACTS.items():
        entry = manifest["artifacts"][name]
        suffix = ".gii" if kind == "mesh" else ".nii.gz"
        if entry["kind"] != kind or entry["relative_path"] != name + suffix:
            raise ValueError("Unexpected preview artifact")
        checked_file(root, entry)
    return (
        {
            "status": "available",
            "provenance": "saved_retrospective_evaluation",
            "subjectCode": patient.code,
            "patientId": patient.id,
            "cutoffVisitId": history[-1]["visit_id"],
            "cutoffDay": history[-1]["days_from_baseline"],
            "observedLabelsUrl": observed_labels_url(db, patient.id, history[-1]),
            "intervalDays": manifest["interval_days"],
            "modelVersion": manifest["version"],
            "modelSha256": manifest["model_sha256"],
            "promoted": False,
            "clinicalValidation": False,
            "evaluationStatus": (
                "saved_retrospective_example"
                if interval_days == 229
                else "generated_prototype_interval_without_matched_follow_up"
            ),
            "studySubjectCount": sum(report.get("counts", {}).values()),
            "gradientTrainingSubjectCount": report.get("counts", {}).get("train"),
            "trainingExampleCount": case.get("training_example_count"),
            "trainingEpochs": report.get("epochs"),
            "warnings": [*report.get("release_failures", []), *manifest.get("warnings", [])],
        },
        root,
        manifest,
    )


def metadata(db: Session, owner_id: str, interval_days: int = 229) -> dict:
    try:
        return load_preview(db, owner_id, interval_days)[0]
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return {
            "status": "unavailable",
            "reason": "The saved experimental example is missing, changed, or not owned by this researcher.",
        }
