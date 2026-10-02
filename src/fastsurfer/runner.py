"""Offline isolated FastSurfer jobs. Never run this in an HTTP handler."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time

from src.common import config, resolve, sha256, write_json
from src.data.preprocess_mri import convert_native, inspect_mri
from src.fastsurfer.manifest import scans, subject_dir
from src.fastsurfer.feature_map import STATS_RELATIVE


def docker_command(cfg: dict, scan_id: str, native, output) -> list[str]:
    subject_dir(cfg, scan_id)
    if not re.fullmatch(r"deepmi/fastsurfer:(cuda|cpu)-v\d+\.\d+\.\d+", cfg["image"]):
        raise ValueError("Use a release-pinned official FastSurfer image")
    if "version" in cfg and not cfg["image"].endswith(f"-v{cfg['version']}"):
        raise ValueError("Configured version must match the pinned image")
    if cfg["device"] not in ("cpu", "cuda") or cfg["viewagg_device"] not in ("cpu", "cuda"):
        raise ValueError("Explicit CPU or CUDA devices required")
    user = cfg.get("container_user", f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "1000:1000")
    if not re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", user) or user.split(":")[0] == "999":
        raise ValueError("Explicit non-root UID:GID required; FastSurfer's placeholder UID 999 is forbidden")
    name = "neuropredict-fs-" + hashlib.sha256(f"{output}/{scan_id}".encode()).hexdigest()[:16]
    cmd = ["docker", "run", "--rm", "--name", name, "--network", "none", "--user", user]
    if cfg["device"] == "cuda":
        cmd += ["--gpus", "all"]
    cmd += [
        "--mount",
        f"type=bind,source={native.parent},target=/input,readonly",
        "--mount",
        f"type=bind,source={output},target=/output",
    ]
    if cfg.get("surface"):
        license_path = resolve(cfg["license_path"]) if cfg.get("license_path") else None
        if license_path is None or not license_path.is_file():
            raise ValueError("Surface reconstruction requires a local FreeSurfer license")
        cmd += ["--mount", f"type=bind,source={license_path},target=/license.txt,readonly"]
    cmd += [
        cfg["image"],
        "--t1",
        f"/input/{native.name}",
        "--sid",
        scan_id,
        "--sd",
        "/output",
        "--device",
        cfg["device"],
        "--viewagg_device",
        cfg["viewagg_device"],
        "--threads",
        str(int(cfg["threads"])),
        "--no_cereb",
        "--no_hypothal",
    ]
    cmd += ["--fs_license", "/license.txt"] if cfg.get("surface") else ["--seg_only"]
    return cmd


def run_scan(cfg: dict, row: dict, image_digest: str) -> dict:
    destination = subject_dir(cfg, row["scan_id"])
    destination.mkdir(parents=True, exist_ok=True)
    record_path = destination / "processing.json"
    if record_path.exists():
        old = json.loads(record_path.read_text())
        if old.get("status") == "completed":
            raise ValueError("Existing completed scan is immutable; use a new output directory")
    source = resolve(row["source_mri_path"])
    qc = inspect_mri(source)
    source_hash = sha256(source)
    pair_hash = sha256(source.with_suffix(".img")) if source.suffix == ".hdr" else None
    native = resolve(cfg["processed_dir"]) / "native" / f"{row['scan_id']}.nii.gz"
    convert_native(source, native)
    cmd = docker_command(cfg, row["scan_id"], native, resolve(cfg["output_dir"]))
    record = {
        "patient_id": row["patient_id"],
        "scan_id": row["scan_id"],
        "status": "processing",
        "version": cfg["version"],
        "image": cfg["image"],
        "digest": image_digest,
        "command": cmd,
        "device": cfg["device"],
        "input_qc": qc,
        "source_sha256": source_hash,
        "source_pair_sha256": pair_hash,
        "native_sha256": sha256(native),
        "preprocessing_version": "native-t1-v1",
        "conversion": "nibabel affine/voxel preserving paired-NIfTI conversion",
        "surface": cfg.get("surface", False),
    }
    write_json(record_path, record)
    started = time.monotonic()
    try:
        with (destination / "execution.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                cmd, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=int(cfg["timeout_seconds"])
            )
        record["container_exit_code"] = 0
        required = [destination / STATS_RELATIVE, destination / "mri/aparc.DKTatlas+aseg.deep.mgz"]
        if not all(p.is_file() for p in required):
            raise ValueError("FastSurfer did not produce required statistics and segmentation")
        record.update(
            status="completed",
            output_sha256={p.relative_to(destination).as_posix(): sha256(p) for p in required},
        )
    except subprocess.TimeoutExpired:
        # A timed-out Docker client alone does not stop its container. Stop only this
        # runner's deterministic named container, never other jobs or any volumes.
        name = cmd[cmd.index("--name") + 1]
        try:
            subprocess.run(
                ["docker", "stop", "--time", "10", name], check=True, capture_output=True, timeout=20
            )
            record["container_cleanup"] = "stopped"
        except (OSError, subprocess.SubprocessError):
            record["container_cleanup"] = "failed"
        record.update(status="failed", error="TimeoutExpired")
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        record.update(status="failed", error=type(error).__name__)
    record["elapsed_seconds"] = round(time.monotonic() - started, 3)
    write_json(record_path, record)
    outcome = {"status": record["status"], "elapsed_seconds": record["elapsed_seconds"]}
    if record["status"] == "failed":
        outcome["error"] = record["error"]
        if "container_cleanup" in record:
            outcome["container_cleanup"] = record["container_cleanup"]
    return outcome


def run(cfg: dict, pilot: int) -> dict:
    if not 1 <= pilot <= 150:
        raise ValueError("Pilot/full batch must be bounded to 1–150 scans")
    subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=30)
    result = subprocess.run(
        ["docker", "image", "inspect", cfg["image"], "--format", "{{json .RepoDigests}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    digests = json.loads(result.stdout)
    if not digests:
        raise ValueError("Pull the official pinned image first; a registry digest is required")
    outcomes = []
    for row in scans(cfg).sort_values("patient_id").head(pilot).to_dict("records"):
        try:
            saved = subject_dir(cfg, row["scan_id"]) / "processing.json"
            record = json.loads(saved.read_text()) if saved.exists() else {}
            if record.get("status") == "completed":
                source = resolve(row["source_mri_path"])
                expected_outputs = {STATS_RELATIVE, "mri/aparc.DKTatlas+aseg.deep.mgz"}
                if (
                    record["digest"] != digests[0]
                    or record["version"] != cfg["version"]
                    or record["patient_id"] != row["patient_id"]
                    or record["scan_id"] != row["scan_id"]
                    or record["source_sha256"] != sha256(source)
                    or (
                        source.suffix == ".hdr"
                        and record["source_pair_sha256"] != sha256(source.with_suffix(".img"))
                    )
                    or set(record["output_sha256"]) != expected_outputs
                    or any(
                        sha256(saved.parent / key) != value for key, value in record["output_sha256"].items()
                    )
                ):
                    raise ValueError("Existing completed output changed; use a new output directory")
                outcomes.append({"status": "completed", "reused_verified": True})
            else:
                outcomes.append(run_scan(cfg, row, digests[0]))
        except (ValueError, OSError, KeyError, TypeError) as error:
            outcomes.append({"status": "failed", "error": type(error).__name__})
        print(f"Processed {len(outcomes)}/{pilot}: {outcomes[-1]['status']}", flush=True)
        if outcomes[-1].get("error") == "TimeoutExpired":
            break  # Inspect timeout/cleanup before launching further GPU work.
    audit = {
        "requested": pilot,
        "completed": sum(r["status"] == "completed" for r in outcomes),
        "results": outcomes,
        "image": cfg["image"],
        "digest": digests[0],
    }
    write_json(resolve(cfg["output_dir"]) / "batch_audit.json", audit)
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/fastsurfer.yaml")
    parser.add_argument("--pilot", type=int, default=5)
    args = parser.parse_args()
    try:
        print(run(config(args.config), args.pilot))
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        raise SystemExit(
            f"FastSurfer unavailable ({type(error).__name__}); check local Docker/image configuration"
        ) from None
