"""Queue the frozen training cohort through the real worker and verify integration only.

This is an in-sample regression check, never predictive-performance evaluation.
Only aggregate verification information is printed or saved.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models import Analysis, Patient, User, Visit
from backend.app.services.analysis import enqueue, trained_snapshot
from ml.contracts import ProgressionResult
from ml.trained_inference import load_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Read existing completed predictions without queueing new jobs",
    )
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--output", type=Path, default=Path("data/qa-trained-integration.json"))
    args = parser.parse_args()
    if args.timeout_seconds < 1:
        parser.error("Timeout must be positive")
    settings = get_settings()
    bundle = load_bundle(settings.trained_model_path)
    manifest = pd.read_csv(settings.trained_model_path.parent / "subject_split.csv")
    training = manifest[manifest["split"] == "train"]
    expected_scores = pd.read_csv(settings.trained_model_path.parent / "predictions.csv")
    expected_scores = expected_scores[expected_scores["split"] == "train"].set_index("subject_id")
    if training["subject_id"].nunique() != 40 or set(expected_scores.index) != set(training["subject_id"]):
        raise ValueError("Expected the exact frozen forty training subjects and their saved predictions")
    jobs = {}
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == settings.seed_email.lower()))
        if user is None:
            raise ValueError("The local researcher account must be seeded first")
        for code, rows in training.groupby("subject_id", sort=True):
            patient = db.scalar(select(Patient).where(Patient.owner_id == user.id, Patient.code == code))
            if patient is None or patient.source != "oasis-2":
                raise ValueError("Import the complete frozen training cohort before inference")
            visits = list(
                db.scalars(
                    select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.days_from_baseline)
                ).all()
            )
            rows = rows.sort_values("days_from_baseline")
            if [v.label for v in visits] != rows["visit_id"].tolist() or [
                v.days_from_baseline for v in visits
            ] != rows["days_from_baseline"].tolist():
                raise ValueError(
                    "Application visit coverage or chronology differs from the frozen training cohort"
                )
            snapshot = trained_snapshot(visits)
            existing = db.scalar(
                select(Analysis)
                .where(
                    Analysis.patient_id == patient.id,
                    Analysis.status == "completed",
                )
                .order_by(Analysis.created_at.desc())
            )
            if (
                existing is not None
                and existing.output_mode == "trained"
                and existing.model_version == bundle.version
                and existing.input_json == snapshot
            ):
                jobs[code] = existing.id
            elif args.verify_only:
                raise ValueError("A current trained prediction is unavailable for part of the cohort")
            else:
                job = enqueue(db, patient, visits[-1], "trained")
                jobs[code] = job.id
        if not args.verify_only:
            db.commit()
    print(
        "Frozen cohort verified: 40 subjects / 132 visits. Waiting for the single analysis worker.",
        flush=True,
    )
    deadline, last_count = time.monotonic() + args.timeout_seconds, -1
    while True:
        with SessionLocal() as db:
            analyses = {
                item.id: item
                for item in db.scalars(select(Analysis).where(Analysis.id.in_(jobs.values()))).all()
            }
        if len(analyses) != 40 or any(item.status == "failed" for item in analyses.values()):
            raise RuntimeError(
                "A trained job failed or disappeared. Check local worker logs; no fallback was used."
            )
        completed = sum(item.status == "completed" for item in analyses.values())
        if completed != last_count:
            print(f"Completed trained sequences: {completed}/40", flush=True)
            last_count = completed
        if completed == 40:
            break
        if args.verify_only or time.monotonic() >= deadline:
            raise TimeoutError(
                "Trained analysis is still pending. Ensure exactly one current worker is running."
            )
        time.sleep(1)
    differences, visits_verified = [], 0
    for code, job_id in jobs.items():
        item = analyses[job_id]
        result = ProgressionResult.model_validate(item.result_json)
        if (
            result.output_mode != "trained"
            or result.prediction is None
            or result.model_version != bundle.version
            or result.prediction.cohort_role != "train"
        ):
            raise ValueError("Persisted results do not match the pinned trained model and training role")
        if item.score != result.prediction.score or result.risk_scores or item.confidence is not None:
            raise ValueError("Persisted score/provenance is inconsistent")
        differences.append(abs(result.prediction.score - float(expected_scores.loc[code, "model_score"])))
        visits_verified += len(result.visit_ids)
    if max(differences) > 1e-6 or visits_verified != 132:
        raise ValueError("Application inference did not reproduce the original full training-sequence scores")
    report = {
        "status": "passed",
        "model_version": bundle.version,
        "training_sequences_verified": 40,
        "training_visits_verified": visits_verified,
        "maximum_score_difference": max(differences),
        "comparison_tolerance": 1e-6,
        "trained_weights_used": True,
        "baseline_fallback": False,
        "scope": "in-sample application integration regression, not accuracy or future forecasting",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
