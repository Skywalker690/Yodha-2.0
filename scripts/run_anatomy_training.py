"""Durable single-model research run: wait for anatomy, register, train and evaluate."""

import argparse
import json
import re
import shutil
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models import Analysis, Patient, User, Visit
from backend.app.services.compute import gpu_slot
from ml.anatomy.study import frozen_split
from ml.anatomy.features import VERSION as FEATURE_VERSION, fit_reference_baselines, reference_hash
from sqlalchemy import select
from src.common import ROOT, sha256, write_json


def gpu_training_command(image: str, study: Path, output: Path, epochs: int) -> list[str]:
    """Only the candidate directory is writable inside the pinned offline runtime."""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("GPU training requires an immutable Docker image ID")
    relative_study = study.resolve().relative_to(ROOT.resolve()).as_posix()
    runtime = freeze_runtime(output.parent)
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--gpus",
        "all",
        "--workdir",
        "/runtime",
        "--mount",
        f"type=bind,source={runtime},target=/runtime,readonly",
        "--mount",
        f"type=bind,source={ROOT},target=/workspace,readonly",
        "--mount",
        f"type=bind,source={output.parent.resolve()},target=/output",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "OMP_NUM_THREADS=2",
        "--env",
        "PYTHONPATH=/runtime:/workspace/nwbv_reference_module/src:/workspace",
        image,
        "-m",
        "scripts.train_anatomy",
        "train",
        "--study",
        f"/workspace/{relative_study}",
        "--run",
        f"/output/{output.name}",
        "--epochs",
        str(epochs),
        "--device",
        "cuda",
        "--allow-unreviewed-research",
        "--reference",
        "/output/nwbv-reference.json",
    ]


def freeze_runtime(run: Path) -> Path:
    """Freeze the forecasting code; verify existing snapshots instead of rewriting."""
    runtime = run / "runtime"
    manifest = runtime / "runtime-manifest.json"
    if manifest.is_file():
        saved = json.loads(manifest.read_text())
        if saved["feature_contract"] != FEATURE_VERSION or any(
            sha256(runtime / name) != fingerprint for name, fingerprint in saved["files"].items()
        ):
            raise ValueError("Frozen forecasting runtime changed; choose a fresh run")
        return runtime
    runtime.mkdir(parents=True, exist_ok=True)
    files = [
        *ROOT.joinpath("ml").rglob("*.py"),
        ROOT / "scripts/__init__.py",
        ROOT / "scripts/train_anatomy.py",
    ]
    for source in files:
        if not source.exists():
            continue
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        target = runtime / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    write_json(
        manifest,
        {
            "feature_contract": FEATURE_VERSION,
            "files": {p.relative_to(runtime).as_posix(): sha256(p) for p in runtime.rglob("*.py")},
        },
    )
    return runtime


def cohort_reference(cohort: Path) -> dict:
    """Read only baseline metadata from subjects in the frozen training role."""
    from ml.data import read_metadata

    record = json.loads((cohort / "cohort.json").read_text())
    candidates = [*get_settings().dataset_root.glob("*.xlsx"), *get_settings().dataset_root.glob("*.csv")]
    source = next((p for p in candidates if sha256(p) == record["metadata_sha256"]), None)
    if source is None:
        raise ValueError("The frozen cohort's original metadata file is missing or changed")
    frame = read_metadata(source)
    split = frozen_split(cohort / "subject_split.csv")
    baselines = {}
    for subject in record["subjects"]:
        if split[subject["subject_id"]] != "train":
            continue
        first = min(subject["visits"], key=lambda v: v["days_from_baseline"])
        rows = frame[frame["MRI ID"] == first["visit_id"]]
        if len(rows) != 1:
            raise ValueError("Frozen training baseline metadata is not unique")
        row = rows.iloc[0].to_dict()
        baselines[subject["subject_id"]] = {key: row.get(key) for key in ("Age", "nWBV", "Visit", "CDR")} | {
            "days_from_baseline": first["days_from_baseline"],
            "visit_id": first["visit_id"],
        }
    return fit_reference_baselines(baselines, split)


def processing_state(split_path: Path) -> dict:
    split = frozen_split(split_path)
    counts = {"completed": 0, "processing": 0, "queued": 0, "failed": 0, "missing": 0}
    failures = []
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == get_settings().seed_email.lower()))
        if owner is None:
            raise ValueError("Configured OASIS importer account is unavailable")
        for subject in split:
            from scripts.train_anatomy import cohort_days

            days = cohort_days(split_path, subject)
            cutoff = db.scalar(
                select(Visit.id)
                .join(Patient, Patient.id == Visit.patient_id)
                .where(Patient.owner_id == owner.id, Patient.source == "oasis-2", Patient.code == subject)
                .where(Visit.days_from_baseline.in_(days) if days is not None else True)
                .order_by(Visit.days_from_baseline.desc())
            )
            job = db.scalar(
                select(Analysis)
                .join(Patient, Patient.id == Analysis.patient_id)
                .where(
                    Patient.owner_id == owner.id,
                    Patient.source == "oasis-2",
                    Patient.code == subject,
                    Analysis.output_mode == "anatomy",
                    Analysis.visit_id == cutoff,
                )
                .order_by(Analysis.created_at.desc())
            )
            status = job.status if job else "missing"
            counts[status] += 1
            if status == "failed":
                failures.append({"subject_id": subject, "analysis_id": job.id, "error": job.error})
    return {"subjects": len(split), "counts": counts, "failures": failures}


def run(
    cohort: Path,
    output: Path,
    *,
    epochs: int,
    device: str,
    grid_size: int,
    resume: bool = False,
    training_image: str | None = None,
    reuse_prepared: Path | None = None,
) -> None:
    split = cohort / "subject_split.csv"
    if not 15 <= epochs <= 500 or not 16 <= grid_size <= 128:
        raise ValueError("Research run requires 15–500 epochs and a 16–128 learning grid")
    cohort_record = json.loads((cohort / "cohort.json").read_text())
    if device == "cuda":
        gpu_training_command(
            training_image or "", output / "study" / "study.json", output / "candidate", epochs
        )
        subprocess.run(["docker", "image", "inspect", training_image], check=True, capture_output=True)
    if sha256(split) != cohort_record["split_sha256"]:
        raise ValueError("Frozen anatomy cohort changed")
    if output.exists() and not resume:
        raise ValueError("Run exists; explicitly resume it or select a fresh path")
    output.mkdir(parents=True, exist_ok=True)
    runtime = freeze_runtime(output)
    reference = cohort_reference(cohort)
    reference_path = output / "nwbv-reference.json"
    if reference_path.exists() and json.loads(reference_path.read_text()) != reference:
        raise ValueError("Cannot change a run's frozen training reference")
    write_json(reference_path, reference)
    status_path = output / "pipeline-status.json"
    if resume:
        previous = json.loads(status_path.read_text())
        if previous.get("feature_contract") != FEATURE_VERSION or previous.get(
            "nwbv_reference_sha256"
        ) != reference_hash(reference):
            raise ValueError(
                "Cannot resume older/different anatomy feature or reference settings; choose a fresh run"
            )
        if previous["cohort_sha256"] != sha256(cohort / "cohort.json"):
            raise ValueError("Cannot resume a different study")
        if any(
            previous[key] != value
            for key, value in (("epochs", epochs), ("device", device), ("grid_size", grid_size))
        ):
            raise ValueError("Cannot alter run settings when resuming")
        if previous.get("training_image") != training_image and (
            previous.get("training_image") is not None or previous["stage"] != "processing_native_anatomy"
        ):
            raise ValueError("Cannot change the training runtime after preparation starts")
    base = {
        "cohort_sha256": sha256(cohort / "cohort.json"),
        "split_sha256": sha256(split),
        "model_policy": "MTA-Koedam-conditioned-only",
        "feature_contract": FEATURE_VERSION,
        "reference_policy": "training_baseline_cdr0",
        "nwbv_reference_sha256": reference_hash(reference),
        "rating_policy": "finite-raw-AVRA-regression-research-v1",
        "allow_unreviewed_research": True,
        "epochs": epochs,
        "device": device,
        "training_image": training_image,
        "grid_size": grid_size,
        "clinical_validation": False,
    }

    def status(stage: str, **values) -> None:
        write_json(
            status_path,
            {**base, "stage": stage, "updated_at": datetime.now(timezone.utc).isoformat(), **values},
        )
        print(json.dumps({"stage": stage, **values}), flush=True)

    def command(arguments: list[str]) -> None:
        if arguments[0] == "prepare" and reuse_prepared:
            arguments = [*arguments, "--reuse-prepared", str(reuse_prepared)]
        with (output / "execution.log").open("a", encoding="utf-8") as log:
            subprocess.run(
                [sys.executable, "-m", "scripts.train_anatomy", *arguments],
                cwd=runtime,
                env={**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")},
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )

    try:
        prepared_subjects = -1
        while True:
            state = processing_state(split)
            if state["counts"]["missing"]:
                from scripts.train_anatomy import queue_cohort

                queue_cohort(split, limit=len(frozen_split(split)))
                state = processing_state(split)
            status("processing_native_anatomy", **state)
            if state["failures"]:
                raise ValueError("Anatomy jobs failed; repair the recorded job and resume this run")
            if state["counts"]["completed"] == state["subjects"]:
                break
            if state["counts"]["completed"] > 0 and state["counts"]["completed"] != prepared_subjects:
                from uuid import uuid4
                from scripts.train_anatomy import export_study

                snapshot = output / "preparation-snapshots" / f"completed-{uuid4().hex}.json"
                result = export_study(split, snapshot, allow_unreviewed_research=True)
                if result["ready_subjects"] < state["counts"]["completed"]:
                    raise ValueError(
                        "Completed anatomy has missing or changed score/source artifacts; inspect its rating logs"
                    )
                status("processing_native_anatomy", **state, preparing_completed_histories=True)
                command(
                    [
                        "prepare",
                        "--export",
                        str(snapshot),
                        "--output",
                        str(output / "study"),
                        "--grid-size",
                        str(grid_size),
                        "--allow-unreviewed-research",
                        "--resume",
                        "--completed-only",
                    ]
                )
                prepared_subjects = result["ready_subjects"]
            time.sleep(30)
        exported = output / "anatomy-export.json"
        if not exported.exists():
            status("exporting_real_anatomy")
            command(
                ["export", "--split", str(split), "--output", str(exported), "--allow-unreviewed-research"]
            )
        study = output / "study" / "study.json"
        if not study.exists():
            status("preparing_cutoff_local_registration")
            command(
                [
                    "prepare",
                    "--export",
                    str(exported),
                    "--output",
                    str(study.parent),
                    "--grid-size",
                    str(grid_size),
                    "--allow-unreviewed-research",
                    "--resume",
                ]
            )
        candidate = output / "candidate"
        evaluation = candidate / "evaluation.json"
        if not evaluation.exists():
            status("training_score_conditioned_model")
            if device == "cuda":
                with gpu_slot(), (output / "execution.log").open("a", encoding="utf-8") as log:
                    subprocess.run(
                        gpu_training_command(training_image, study, candidate, epochs),
                        cwd=ROOT,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
            else:
                command(
                    [
                        "train",
                        "--study",
                        str(study),
                        "--run",
                        str(candidate),
                        "--epochs",
                        str(epochs),
                        "--device",
                        device,
                        "--allow-unreviewed-research",
                        "--reference",
                        str(reference_path),
                    ]
                )
        report = json.loads(evaluation.read_text())
        if report["native"]["status"] == "not_evaluated":
            status("evaluating_native_predictions")
            command(["evaluate-native", "--study", str(study), "--run", str(candidate)])
            report = json.loads(evaluation.read_text())
        status(
            "research_candidate_trained_and_evaluated",
            evaluation_sha256=sha256(evaluation),
            release_failures=report["release_failures"],
            native_status=report["native"]["status"],
        )
    except Exception as error:
        status("failed", error=f"{type(error).__name__}: {error}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--grid-size", type=int, default=96)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--reuse-prepared", type=Path, help="Reuse verified source-matching registrations in a fresh run"
    )
    parser.add_argument("--training-image", help="Immutable sha256 Docker image ID, required for CUDA")
    args = parser.parse_args()
    # A long local run must survive normal idle sleep. This request applies only
    # to this process/thread, leaves display sleep and power settings unchanged,
    # and is cleared on exit (including when Windows terminates the process).
    kernel = None
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        if not kernel.SetThreadExecutionState(0x80000001):
            raise OSError("Unable to keep the system awake during the training run")
    try:
        run(
            args.cohort.resolve(),
            args.output.resolve(),
            epochs=args.epochs,
            device=args.device,
            grid_size=args.grid_size,
            resume=args.resume,
            training_image=args.training_image,
            reuse_prepared=args.reuse_prepared.resolve() if args.reuse_prepared else None,
        )
    finally:
        if kernel is not None:
            kernel.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
