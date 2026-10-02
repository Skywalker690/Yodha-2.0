"""Offline study lifecycle for the existing anatomy worker, not a second ingestion app."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.common import ROOT, sha256, write_json


def export_study(split_path: Path, output: Path, *, allow_unreviewed_research: bool = False) -> dict:
    from sqlalchemy import select
    from backend.app.db.session import SessionLocal
    from backend.app.core.config import get_settings
    from backend.app.models import Analysis, Patient, User, Visit
    from backend.app.services.storage import resolve_key
    from ml.contracts import ProgressionResult
    from ml.anatomy.integrity import measurement_files, rating_files
    from ml.anatomy.study import frozen_split

    split = frozen_split(split_path)
    subjects, blocked = [], []
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == get_settings().seed_email.lower()))
        if owner is None:
            raise ValueError("Import the frozen OASIS cohort for the configured local researcher first")
        for subject in split:
            cutoff = db.scalar(
                select(Visit.id)
                .join(Patient, Patient.id == Visit.patient_id)
                .where(Patient.owner_id == owner.id, Patient.source == "oasis-2", Patient.code == subject)
                .order_by(Visit.days_from_baseline.desc())
            )
            candidates = db.execute(
                select(Patient, Analysis)
                .join(Analysis, Analysis.patient_id == Patient.id)
                .where(
                    Patient.code == subject,
                    Patient.owner_id == owner.id,
                    Patient.source == "oasis-2",
                    Analysis.output_mode == "anatomy",
                    Analysis.status == "completed",
                    Analysis.visit_id == cutoff,
                )
                .order_by(Analysis.created_at.desc())
            ).all()
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
                        if not allow_unreviewed_research and (
                            visit.qc != "passed" or visit.ratings.status != "ok"
                        ):
                            raise ValueError("Segmentation/alignment review incomplete")
                        source = next(s for s in job.input_json if s["visit_id"] == visit.visit_id)
                        files = measurement_files(
                            root, patient.id, index, visit, resolve_key(source["mri_key"])
                        )
                        provenance = rating_files(root, index, visit, reviewed=not allow_unreviewed_research)
                        measurement = visit.model_copy(deep=True)
                        if allow_unreviewed_research and visit.ratings.status != "ok":
                            from ml.anatomy.ratings import parse_avra_csv

                            # Parse finite raw regression outputs only; do not
                            # change app review state or claim alignment approval.
                            scores = parse_avra_csv(
                                root / f"rating_{index}/rating.csv",
                                alignment_verified=True,
                                allow_unreviewed_research=True,
                            )
                            if scores.status not in {"ok", "unreviewed_research"}:
                                raise ValueError("Automatic rating outputs failed finite/structure checks")
                            raw_warnings = scores.warnings if scores.status == "unreviewed_research" else []
                            scores.status = "unreviewed_research"
                            scores.warnings = [
                                "Research training inputs; visual alignment review incomplete.",
                                *raw_warnings,
                            ]
                            measurement.ratings = scores
                        if allow_unreviewed_research and visit.qc != "passed":
                            measurement.qc = "automated_checks_only"
                        records.append(
                            {
                                "subject_id": subject,
                                "analysis_id": job.id,
                                "measurement": measurement.model_dump(),
                                "mri_path": str(resolve_key(source["mri_key"])),
                                "source_units_verified": source.get("source_units_verified", False),
                                "labels_path": str(files["segmentation"]),
                                "labels_sha256": sha256(files["segmentation"]),
                                "rating_provenance": provenance,
                            }
                        )
                    subjects.append({"subject_id": subject, "visits": records})
                    found = True
                    break
                except (ValueError, OSError, KeyError, StopIteration):
                    continue
            if not found:
                blocked.append(subject)
    result = {
        "version": "anatomy-export-v1",
        "synthetic": False,
        "allow_unreviewed_research": allow_unreviewed_research,
        "split": split,
        "split_sha256": sha256(split_path),
        "subjects": subjects,
        "blocked_subjects": blocked,
        "stage": "ready_for_registration" if not blocked else "blocked_reviewed_anatomy",
    }
    if output.exists():
        raise ValueError("Exports are immutable; choose a new path")
    write_json(output, result)
    return {"stage": result["stage"], "ready_subjects": len(subjects), "blocked_subjects": len(blocked)}


def queue_cohort(split_path: Path, limit: int = 56) -> dict:
    from sqlalchemy import select
    from backend.app.db.session import SessionLocal
    from backend.app.core.config import get_settings
    from backend.app.models import Analysis, Patient, User, Visit
    from backend.app.services.analysis import enqueue
    from backend.app.services.storage import resolve_key
    from ml.anatomy.study import frozen_split

    heartbeat = json.loads(resolve_key("worker-capabilities.json").read_text())
    if (
        "longitudinal-anatomy-v1" not in heartbeat["capabilities"]
        or time.time() - heartbeat["timestamp"] > 60
    ):
        raise ValueError("Restart the single existing worker with anatomy support before queuing a cohort")
    split = frozen_split(split_path)
    if not 1 <= limit <= len(split):
        raise ValueError("Queue limit must fit the frozen anatomy study")
    queued, skipped = 0, 0
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == get_settings().seed_email.lower()))
        if owner is None:
            raise ValueError("Import the frozen OASIS cohort for the configured local researcher first")
        for subject in split:
            if queued >= limit:
                break
            patient = db.scalar(
                select(Patient).where(
                    Patient.code == subject, Patient.owner_id == owner.id, Patient.source == "oasis-2"
                )
            )
            if patient is None:
                raise ValueError("Frozen subject not imported; do not silently select replacements")
            visits = db.scalars(
                select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.days_from_baseline)
            ).all()
            completed = (
                db.scalar(
                    select(Analysis).where(
                        Analysis.patient_id == patient.id,
                        Analysis.output_mode == "anatomy",
                        Analysis.status == "completed",
                        Analysis.visit_id == visits[-1].id,
                    )
                )
                if visits
                else None
            )
            if completed or db.scalar(
                select(Analysis).where(
                    Analysis.patient_id == patient.id, Analysis.status.in_(["queued", "processing"])
                )
            ):
                skipped += 1
                continue
            if not 3 <= len(visits) <= 5 or any(not v.mri_key for v in visits):
                raise ValueError("Frozen subject lacks the expected three-to-five managed MRI visits")
            enqueue(db, patient, visits[-1], "anatomy")
            queued += 1
        db.commit()
    return {
        "queued_subjects": queued,
        "skipped_existing_subjects": skipped,
        "execution": "single existing worker, serialized",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-cohort")
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    p.add_argument("--output", type=Path, required=True)
    for command in ("export", "queue-cohort"):
        p = sub.add_parser(command)
        p.add_argument(
            "--split",
            type=Path,
            default=ROOT / "artifacts/anatomy-score-study-20261002/subject_split.csv",
        )
        if command == "export":
            p.add_argument("--output", type=Path, required=True)
            p.add_argument("--allow-unreviewed-research", action="store_true")
        else:
            p.add_argument(
                "--limit",
                type=int,
                default=56,
                help="Bound the initial pilot without changing frozen membership",
            )
    p = sub.add_parser("prepare")
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--grid-size", type=int, default=96)
    p.add_argument("--allow-unreviewed-research", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument(
        "--completed-only",
        action="store_true",
        help="Prepare finished histories without finalizing study.json",
    )
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
            p.add_argument("--allow-unreviewed-research", action="store_true")
    args = parser.parse_args()
    if args.command == "create-cohort":
        from ml.anatomy.cohort import create_cohort

        cohort = create_cohort(args.metadata, args.dataset, args.output)
        result = {
            "stage": "cohort_frozen",
            "counts": cohort["counts"],
            "scan_counts": cohort["scan_count_distribution"],
        }
    elif args.command == "export":
        result = export_study(
            args.split, args.output, allow_unreviewed_research=args.allow_unreviewed_research
        )
    elif args.command == "queue-cohort":
        result = queue_cohort(args.split, args.limit)
    elif args.command == "prepare":
        from ml.anatomy.study import prepare_case

        exported = json.loads(args.export.read_text())
        if exported["synthetic"] or (exported["blocked_subjects"] and not args.completed_only):
            raise ValueError("Complete frozen reviewed anatomy and automatic ratings before registration")
        if exported.get("allow_unreviewed_research") and not args.allow_unreviewed_research:
            raise ValueError(
                "Unreviewed research export requires an explicit candidate-only preparation flag"
            )
        args.output.mkdir(parents=True, exist_ok=args.resume)
        entries = []
        membership = list(exported["split"])
        for subject in exported["subjects"]:
            subject_index = membership.index(subject["subject_id"])
            for cutoff in range(2, len(subject["visits"])):
                directory = args.output / f"case-{subject_index}-{cutoff}"
                case_path = directory / "case.json"
                if case_path.exists() and args.resume:
                    from ml.anatomy.study import load_case

                    prior, _, arrays = load_case(case_path, require_review=False)
                    if (
                        prior["source_records"] != subject["visits"][: cutoff + 1]
                        or arrays["images"].shape[1:] != (args.grid_size,) * 3
                        or prior.get("allow_unreviewed_research", False) != args.allow_unreviewed_research
                    ):
                        raise ValueError("Existing prepared case differs from the immutable export")
                else:
                    if directory.exists() and args.resume:
                        # Preserve interrupted artifacts; create a fresh attempt at
                        # the stable case path without deleting prior bytes.
                        prior_directory = directory.resolve()
                        preserved = directory.with_name(
                            f"{directory.name}.interrupted-{uuid4().hex}"
                        ).resolve()
                        prior_directory.relative_to(args.output.resolve())
                        preserved.relative_to(args.output.resolve())
                        prior_directory.rename(preserved)
                    prepare_case(
                        subject["visits"][:cutoff],
                        subject["visits"][cutoff],
                        directory,
                        args.grid_size,
                        allow_unreviewed_research=args.allow_unreviewed_research,
                    )
                entries.append(
                    {
                        "relative_path": (directory / "case.json").relative_to(args.output).as_posix(),
                        "sha256": sha256(directory / "case.json"),
                    }
                )
        write_json(
            args.output / ("preparation-progress.json" if args.completed_only else "study.json"),
            {
                "synthetic": False,
                "allow_unreviewed_research": args.allow_unreviewed_research,
                "split": exported["split"],
                "export_sha256": sha256(args.export),
                "cases": entries,
            },
        )
        result = {
            "stage": "completed_histories_prepared"
            if args.completed_only
            else "awaiting_registration_review",
            "cases": len(entries),
        }
    elif args.command == "review-registration":
        from ml.anatomy.study import load_case

        case, _, _ = load_case(args.case, require_review=False)
        if case["registration_qc"] != "pending_review" or not args.reviewer.strip():
            raise ValueError("Named reviewer and a pending registration required")
        case.update(
            registration_qc="passed",
            reviewer_id=args.reviewer.strip(),
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        write_json(args.case, case)
        study_path = args.case.parent.parent / "study.json"
        study = json.loads(study_path.read_text())
        entry = next(
            e
            for e in study["cases"]
            if (study_path.parent / e["relative_path"]).resolve() == args.case.resolve()
        )
        entry["sha256"] = sha256(args.case)
        write_json(study_path, study)
        result = {"stage": "registration_reviewed"}
    elif args.command == "train":
        from ml.anatomy.training import train

        report = train(
            args.study,
            args.run,
            epochs=args.epochs,
            device=args.device,
            allow_unreviewed_research=args.allow_unreviewed_research,
        )
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
