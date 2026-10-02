"""Offline study lifecycle for the existing anatomy worker, not a second ingestion app."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.common import ROOT, sha256, write_json


def export_study(split_path: Path, output: Path) -> dict:
    from sqlalchemy import select
    from backend.app.db.session import SessionLocal
    from backend.app.models import Analysis, Patient
    from backend.app.services.storage import resolve_key
    from ml.contracts import ProgressionResult
    from ml.anatomy.integrity import measurement_files, rating_files
    from ml.anatomy.study import frozen_split
    split = frozen_split(split_path)
    subjects, blocked = [], []
    with SessionLocal() as db:
        for subject in split:
            candidates = db.execute(select(Patient, Analysis).join(Analysis, Analysis.patient_id == Patient.id)
                .where(Patient.code == subject, Analysis.output_mode == "anatomy", Analysis.status == "completed")
                .order_by(Analysis.created_at.desc())).all()
            found = False
            for patient, job in candidates:
                result = ProgressionResult.model_validate(job.result_json)
                anatomy = result.anatomy
                if anatomy is None or len(anatomy.visits) < 3:
                    continue
                try:
                    records = []
                    root = resolve_key(f"derived/{job.id}")
                    for index, visit in enumerate(anatomy.visits):
                        if visit.qc != "passed" or visit.ratings.status != "ok":
                            raise ValueError("Segmentation/alignment review incomplete")
                        source = next(s for s in job.input_json if s["visit_id"] == visit.visit_id)
                        files = measurement_files(root, patient.id, index, visit, resolve_key(source["mri_key"]))
                        provenance = rating_files(root, index, visit, reviewed=True)
                        records.append({"subject_id": subject, "analysis_id": job.id, "measurement": visit.model_dump(),
                                        "mri_path": str(resolve_key(source["mri_key"])), "source_units_verified": source.get("source_units_verified", False),
                                        "labels_path": str(files["segmentation"]), "labels_sha256": sha256(files["segmentation"]), "rating_provenance": provenance})
                    subjects.append({"subject_id": subject, "visits": records})
                    found = True
                    break
                except (ValueError, OSError, KeyError, StopIteration):
                    continue
            if not found:
                blocked.append(subject)
    result = {"version": "anatomy-export-v1", "synthetic": False, "split": split, "split_sha256": sha256(split_path),
              "subjects": subjects, "blocked_subjects": blocked, "stage": "ready_for_registration" if not blocked else "blocked_reviewed_anatomy"}
    if output.exists():
        raise ValueError("Exports are immutable; choose a new path")
    write_json(output, result)
    return {"stage": result["stage"], "ready_subjects": len(subjects), "blocked_subjects": len(blocked)}


def queue_cohort(split_path: Path) -> dict:
    from sqlalchemy import select
    from backend.app.db.session import SessionLocal
    from backend.app.models import Analysis, Patient, Visit
    from backend.app.services.analysis import enqueue
    from backend.app.services.storage import resolve_key
    from ml.anatomy.study import frozen_split
    heartbeat = json.loads(resolve_key("worker-capabilities.json").read_text())
    if "longitudinal-anatomy-v1" not in heartbeat["capabilities"] or time.time() - heartbeat["timestamp"] > 60:
        raise ValueError("Restart the single existing worker with anatomy support before queuing a cohort")
    split = frozen_split(split_path)
    queued, skipped = 0, 0
    with SessionLocal() as db:
        for subject in split:
            patient = db.scalar(select(Patient).where(Patient.code == subject))
            if patient is None:
                raise ValueError("Frozen subject not imported; do not silently select replacements")
            visits = db.scalars(select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.days_from_baseline)).all()
            completed = db.scalar(select(Analysis).where(Analysis.patient_id == patient.id, Analysis.output_mode == "anatomy", Analysis.status == "completed", Analysis.visit_id == visits[-1].id)) if visits else None
            if completed or db.scalar(select(Analysis).where(Analysis.patient_id == patient.id, Analysis.status.in_(["queued", "processing"]))):
                skipped += 1
                continue
            if not 3 <= len(visits) <= 5 or any(not v.mri_key for v in visits):
                raise ValueError("Frozen subject lacks the expected three-to-five managed MRI visits")
            enqueue(db, patient, visits[-1], "anatomy")
            queued += 1
        db.commit()
    return {"queued_subjects": queued, "skipped_existing_subjects": skipped, "execution": "single existing worker, serialized"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("export", "queue-cohort"):
        p = sub.add_parser(command)
        p.add_argument("--split", type=Path, default=ROOT / "data/training_multimodal/runs/20261001T134908Z/subject_split.csv")
        if command == "export":
            p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--grid-size", type=int, default=96)
    p = sub.add_parser("review-registration")
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--visual-review-confirmed", action="store_true", required=True)
    for command in ("train", "evaluate-native", "promote"):
        p = sub.add_parser(command)
        p.add_argument("--run", type=Path, required=True)
        if command != "promote":
            p.add_argument("--study", type=Path, required=True)
        if command == "train":
            p.add_argument("--epochs", type=int, default=20)
            p.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    if args.command == "export":
        result = export_study(args.split, args.output)
    elif args.command == "queue-cohort":
        result = queue_cohort(args.split)
    elif args.command == "prepare":
        from ml.anatomy.study import prepare_case
        exported = json.loads(args.export.read_text())
        if exported["synthetic"] or exported["blocked_subjects"]:
            raise ValueError("Complete frozen reviewed anatomy and automatic ratings before registration")
        args.output.mkdir(parents=True, exist_ok=False)
        entries = []
        for subject_index, subject in enumerate(exported["subjects"]):
            for cutoff in range(2, len(subject["visits"])):
                directory = args.output / f"case-{subject_index}-{cutoff}"
                prepare_case(subject["visits"][:cutoff], subject["visits"][cutoff], directory, args.grid_size)
                entries.append({"relative_path": str((directory / "case.json").relative_to(args.output)), "sha256": sha256(directory / "case.json")})
        write_json(args.output / "study.json", {"synthetic": False, "split": exported["split"], "export_sha256": sha256(args.export), "cases": entries})
        result = {"stage": "awaiting_registration_review", "cases": len(entries)}
    elif args.command == "review-registration":
        from ml.anatomy.study import load_case
        case, _, _ = load_case(args.case, require_review=False)
        if case["registration_qc"] != "pending_review" or not args.reviewer.strip():
            raise ValueError("Named reviewer and a pending registration required")
        case.update(registration_qc="passed", reviewer_id=args.reviewer.strip(), reviewed_at=datetime.now(timezone.utc).isoformat())
        write_json(args.case, case)
        study_path = args.case.parent.parent / "study.json"
        study = json.loads(study_path.read_text())
        entry = next(e for e in study["cases"] if (study_path.parent / e["relative_path"]).resolve() == args.case.resolve())
        entry["sha256"] = sha256(args.case)
        write_json(study_path, study)
        result = {"stage": "registration_reviewed"}
    elif args.command == "train":
        from ml.anatomy.training import train
        report = train(args.study, args.run, epochs=args.epochs, device=args.device)
        result = {"stage": "candidate_trained", "release_failures": report["release_failures"]}
    elif args.command == "evaluate-native":
        from ml.anatomy.native_evaluation import evaluate_native
        result = {"stage": evaluate_native(args.study, args.run)["native"]["status"]}
    else:
        from ml.anatomy.native_evaluation import promote
        result = {"stage": promote(args.run)["status"]}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
