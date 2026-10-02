"""Queue the explicit frozen small-cohort model for prepared owned OASIS histories."""

import argparse
import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models import Analysis, Patient, User
from backend.app.services.anatomy_forecast import enqueue_forecast, readiness
from ml.contracts import ProgressionResult


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue", action="store_true", help="Persist jobs; otherwise report eligibility only"
    )
    parser.add_argument("--interval-days", type=int, default=365)
    parser.add_argument("--subjects", nargs="+", help="Queue only these patient codes")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    state = readiness(experimental=True)
    if state["status"] != "available" or args.interval_days not in state["intervalsDays"]:
        raise SystemExit("Configured historical candidate/interval is unavailable")
    outcomes = []
    with SessionLocal() as db:
        patients = db.scalars(
            select(Patient)
            .join(User)
            .where(User.email == get_settings().seed_email, Patient.source == "oasis-2")
            .order_by(Patient.code)
        ).all()
        if args.subjects:
            requested = set(args.subjects)
            missing = requested - {patient.code for patient in patients}
            if missing:
                raise SystemExit(f"Unknown owned OASIS patients: {', '.join(sorted(missing))}")
            patients = [patient for patient in patients if patient.code in requested]
        for patient in patients:
            sources = db.scalars(
                select(Analysis)
                .where(
                    Analysis.patient_id == patient.id,
                    Analysis.status == "completed",
                    Analysis.output_mode == "anatomy",
                )
                .order_by(Analysis.created_at.desc())
            ).all()
            source = next(
                (s for s in sources if s.result_json and not s.input_json[-1].get("forecast_spec")), None
            )
            if source is None:
                continue
            result = ProgressionResult.model_validate(source.result_json)
            if result.anatomy is None or len(result.anatomy.visits) < 2:
                continue
            cutoff = result.anatomy.visits[-1].visit_id
            existing = next(
                (
                    s
                    for s in sources
                    if s.result_json
                    and s.result_json.get("anatomy", {}).get("forecast", {}).get("experimental")
                    and s.result_json["anatomy"]["forecast"].get("cutoff_visit_id") == cutoff
                    and s.result_json["anatomy"]["forecast"].get("interval_days") == args.interval_days
                    and s.result_json["anatomy"]["forecast"].get("release_sha256") == state["releaseSha256"]
                ),
                None,
            )
            item = {
                "subject": patient.code,
                "patient_id": patient.id,
                "source_analysis_id": source.id,
                "cutoff_visit_id": cutoff,
                "visits": len(result.anatomy.visits),
            }
            if existing:
                item.update(status="already_completed", job_id=existing.id)
            elif args.queue:
                try:
                    job = enqueue_forecast(db, source, args.interval_days, cutoff, experimental=True)
                    db.commit()
                    item.update(status="queued", job_id=job.id)
                except HTTPException as error:
                    db.rollback()
                    item.update(status="blocked", reason=error.detail)
            else:
                item.update(status="prepared")
            outcomes.append(item)
    report = {
        "experimental": True,
        "interval_days": args.interval_days,
        "candidate_sha256": state["releaseSha256"],
        "patients": outcomes,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
