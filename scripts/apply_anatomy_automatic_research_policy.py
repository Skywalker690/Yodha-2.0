"""Backfill verified source AVRA rows as unreviewed research estimates."""

import argparse

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models import Analysis, Patient
from backend.app.services.storage import resolve_key
from ml.anatomy.integrity import measurement_files, rating_files
from ml.anatomy.measurements import changes
from ml.anatomy.ratings import parse_avra_csv
from ml.contracts import ProgressionResult


def prepare_updates(db) -> tuple[list[tuple[Analysis, dict]], int, int]:
    rows = db.execute(
        select(Analysis, Patient.code)
        .join(Patient, Patient.id == Analysis.patient_id)
        .where(Analysis.output_mode == "anatomy", Analysis.status == "completed")
        .order_by(Patient.code, Analysis.created_at)
    ).all()
    updates: list[tuple[Analysis, dict]] = []
    updated_visits = skipped_scores = 0
    for job, code in rows:
        result = ProgressionResult.model_validate(job.result_json)
        if result.anatomy is None:
            raise ValueError(f"Completed anatomy result is missing: {job.id}")
        root = resolve_key(f"derived/{job.id}")
        snapshots = {item["visit_id"]: item for item in job.input_json}
        changed = False
        for index, visit in enumerate(result.anatomy.visits):
            source_snapshot = snapshots.get(visit.visit_id)
            if source_snapshot is None:
                raise ValueError(f"Frozen source visit is missing: {job.id}/{visit.visit_id}")
            source = resolve_key(source_snapshot["mri_key"])
            measurement_files(root, job.patient_id, index, visit, source)

            if visit.qc == "pending_review":
                visit.qc = "automated_checks_only"
                visit.reviewer_id = None
                visit.reviewed_at = None
                changed = True
            if visit.ratings.status == "pending_alignment_qc":
                rating_files(root, index, visit, reviewed=False)
                estimate = parse_avra_csv(
                    root / f"rating_{index}/rating.csv",
                    alignment_verified=False,
                    allow_unreviewed_research=True,
                )
                if estimate.status != "unreviewed_research":
                    skipped_scores += 1
                    continue
                estimate.provenance_sha256 = visit.ratings.provenance_sha256
                visit.ratings = estimate
                changed = True
                updated_visits += 1
        result.anatomy.changes = changes(result.anatomy.visits)
        if changed:
            caveats = [
                caveat
                for caveat in result.caveats
                if not caveat.startswith((
                    "Measured anatomy is pending visual segmentation QC",
                    "Automatic ratings unavailable until AVRA",
                ))
            ]
            caveats.extend(
                [
                    "Measured anatomy uses automated checks only; visual segmentation review was skipped by research policy.",
                    "MTA/Koedam outputs are unreviewed research estimates; alignment and rating agreement remain unverified.",
                ]
            )
            result.caveats = list(dict.fromkeys(caveats))
            updates.append((job, result.model_dump(mode="json")))
            print(f"{code}: prepared automatic research values for analysis {job.id}")
    return updates, updated_visits, skipped_scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the validated unreviewed estimates; without this flag the run is read-only.",
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        updates, visits, skipped = prepare_updates(db)
        print(f"Prepared {len(updates)} analysis results, {visits} AVRA visit scores, {skipped} unavailable rows.")
        if not args.apply:
            print("Dry run only. Pass --apply to persist these research-only values.")
            return
        for job, result_json in updates:
            job.result_json = result_json
        db.commit()
        print("Applied the automatic-unreviewed research policy.")


if __name__ == "__main__":
    main()
