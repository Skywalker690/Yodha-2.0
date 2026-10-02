"""Explicit local processing/training workflow. No automatic visual-QC approval."""

from __future__ import annotations

import argparse
import json
import subprocess
import os
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from src.common import ROOT, config, read_table, resolve, sha256, write_json
from src.fastsurfer.parse_stats import build_features
from src.fastsurfer.runner import docker_command, run
from src.risk.evaluate import evaluate
from src.risk.release import assess, promote
from src.risk.train import train


@contextmanager
def study_lock(directory: Path) -> Iterator[None]:
    """One writer per study, released by the OS if the process exits/crashes."""
    with (directory / ".ml-pipeline.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError(
                "Another ML pipeline owns this study; do not start duplicate processing/training"
            ) from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def workflow(
    experiment: dict,
    fastsurfer: dict,
    run_dir: Path,
    batch_size: int,
    resume: bool = False,
    pull_image: bool = False,
) -> dict:
    with study_lock(resolve(experiment["processed_dir"])):
        return _workflow(experiment, fastsurfer, run_dir, batch_size, resume, pull_image)


def _workflow(
    experiment: dict,
    fastsurfer: dict,
    run_dir: Path,
    batch_size: int,
    resume: bool = False,
    pull_image: bool = False,
) -> dict:
    if not 1 <= batch_size <= 150:
        raise ValueError("Bound the processing batch to 1–150 scans")
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Pipeline runs must be inside the project's ignored artifacts directory")
    status_path = run_dir / "pipeline_status.json"
    if run_dir.exists() and not resume:
        raise ValueError("Run directory exists; use a new directory or explicitly resume")
    if resume and not status_path.is_file():
        raise ValueError("Cannot resume without a saved pipeline status")
    old = json.loads(status_path.read_text()) if resume else {}
    if old.get("stage") == "release_ready":
        raise ValueError("Completed releases are immutable")
    state = {
        "started_at": old.get("started_at", datetime.now(timezone.utc).isoformat()),
        "stage": "preflight",
        "clinical_validation": False,
        "batch_size": batch_size,
        "history": old.get("history", []),
    }

    def checkpoint(stage: str, detail: str) -> dict:
        state.update(stage=stage, detail=detail, updated_at=datetime.now(timezone.utc).isoformat())
        state["history"].append({"stage": stage, "at": state["updated_at"]})
        write_json(status_path, state)
        print(f"{stage}: {detail}", flush=True)
        return state

    checkpoint("preflight", "Validate frozen study inputs; source data and old models are preserved.")
    processed = resolve(experiment["processed_dir"])
    if processed != resolve(fastsurfer["processed_dir"]):
        raise ValueError("Training and FastSurfer processed directories must match")
    fingerprints = {
        name: sha256(processed / name) for name in ("baseline.csv", "labels.csv", "split.csv", "manifest.csv")
    }
    runtime_spec = {
        key: fastsurfer.get(key)
        for key in (
            "output_dir",
            "image",
            "version",
            "device",
            "viewagg_device",
            "surface",
            "threads",
            "container_user",
        )
    }
    if old.get("source_hashes") and old["source_hashes"] != fingerprints:
        raise ValueError("Study changed since pipeline start; create a new run")
    if old.get("runtime_spec") and old["runtime_spec"] != runtime_spec:
        raise ValueError("Processing specification changed; create a new run")
    state["source_hashes"] = fingerprints
    state["runtime_spec"] = runtime_spec
    # Validate the official pin/device/license before a download or container launch.
    docker_command(
        fastsurfer, "PREFLIGHT", processed / "native" / "preflight.nii.gz", resolve(fastsurfer["output_dir"])
    )
    if (
        not resume
        or old.get("stage") in ("blocked_runtime", "blocked_processing", "processing")
        or batch_size > old.get("batch_size", 0)
    ):
        checkpoint("processing", "Run actual baseline MRI segmentation; never synthesize anatomy.")
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=20)
            if pull_image:
                subprocess.run(["docker", "pull", fastsurfer["image"]], check=True, timeout=1800)
            audit = run(fastsurfer, batch_size)
            if audit["completed"] != batch_size:
                return checkpoint(
                    "blocked_processing", "Not every requested scan completed. Inspect local per-scan logs."
                )
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            return checkpoint(
                "blocked_runtime",
                f"FastSurfer could not execute ({type(error).__name__}). Restore Docker Linux engine and the pinned image; no anatomy/model was fabricated.",
            )
    build_features(fastsurfer)
    features = read_table(processed / "fastsurfer_features.csv")
    baseline = read_table(processed / "baseline.csv")
    reviewed = set(features.loc[features["qc"] == "passed", "patient_id"])
    state["reviewed_subjects"], state["required_subjects"] = len(reviewed), len(baseline)
    if reviewed != set(baseline["patient_id"]):
        return checkpoint(
            "awaiting_visual_qc",
            "Process remaining eligible baselines and visually review real segmentations before training. No automatic approval.",
        )
    candidate = dict(experiment, artifact_dir=str(run_dir / "models"))
    checkpoint(
        "training",
        "Train matched clinical reference and Clinical + FastSurfer on frozen subjects, known labels and training-only preprocessing.",
    )
    for kind, matched in (("clinical", True), ("clinical_fastsurfer", False)):
        name = "clinical_matched" if matched else kind
        path = resolve(candidate["artifact_dir"]) / f"{name}.json"
        try:
            if not path.exists():
                train(candidate, kind, matched)
            evaluate(candidate, kind, matched)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return checkpoint(
                "blocked_training",
                f"Training/evaluation failed ({type(error).__name__}); preserve artifacts and inspect study inputs. No serving promotion.",
            )
    reasons = assess(resolve(candidate["artifact_dir"]), processed)
    if reasons:
        state["release_blockers"] = reasons
        return checkpoint(
            "blocked_outcomes",
            "Training/evaluation finished, but full-horizon release gates failed. Unsupported outcomes remain unknown; no serving promotion.",
        )
    promote(resolve(candidate["artifact_dir"]), processed)
    return checkpoint(
        "release_ready",
        "Set FORECAST_ARTIFACT_DIR to this run's models directory and restart the API. Research validation limitations still apply.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--fastsurfer-config", default="configs/fastsurfer.yaml")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--pull-image", action="store_true")
    args = parser.parse_args()
    state = workflow(
        config(args.config),
        config(args.fastsurfer_config),
        args.run_dir,
        args.batch_size,
        args.resume,
        args.pull_image,
    )
    raise SystemExit(0 if state["stage"] == "release_ready" else 2)
