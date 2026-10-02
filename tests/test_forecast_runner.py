"""Synthetic FastSurfer outputs test the runner-to-QC-to-feature join, not accuracy."""

import json
import subprocess

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from src.common import sha256
from src.fastsurfer.parse_stats import build_features
from src.fastsurfer.qc import approve
from src.fastsurfer.runner import run_scan
from tests.test_forecast_v2 import stats_text


def test_synthetic_container_result_review_and_source_hash(mri, tmp_path, monkeypatch):
    from src.fastsurfer import runner

    cfg = {
        "image": "deepmi/fastsurfer:cuda-v2.5.4",
        "version": "2.5.4",
        "device": "cpu",
        "viewagg_device": "cpu",
        "threads": 2,
        "timeout_seconds": 60,
        "surface": False,
        "output_dir": str(tmp_path / "outputs"),
        "processed_dir": str(tmp_path / "processed"),
    }
    row = {"patient_id": "SYNTHETIC", "scan_id": "SCAN_1", "source_mri_path": str(mri)}
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([row]).to_csv(processed / "manifest.csv", index=False)
    destination = tmp_path / "outputs/SCAN_1"

    def fake_container(*args, **kwargs):
        (destination / "stats").mkdir(parents=True)
        (destination / "mri").mkdir()
        (destination / "stats/aseg+DKT.VINN.stats").write_text(stats_text())
        nib.save(
            nib.MGHImage(np.ones((8, 8, 8), dtype=np.int16), np.eye(4)),
            str(destination / "mri/aparc.DKTatlas+aseg.deep.mgz"),
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_container)
    original = sha256(mri)
    assert run_scan(cfg, row, "deepmi/fastsurfer@sha256:" + "a" * 64)["status"] == "completed"
    assert sha256(mri) == original
    assert build_features(cfg) == {"pending_review": 1}
    approve(cfg, "SCAN_1", "synthetic-reviewer")
    assert build_features(cfg) == {"passed": 1}

    def fake_docker_control(command, **kwargs):
        if command[1] == "info":
            return subprocess.CompletedProcess(command, 0)
        if command[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(
                command, 0, json.dumps(["deepmi/fastsurfer@sha256:" + "a" * 64])
            )
        pytest.fail("Verified completed scan must not rerun the container")

    monkeypatch.setattr(runner.subprocess, "run", fake_docker_control)
    assert runner.run(cfg, 1)["results"] == [{"status": "completed", "reused_verified": True}]
    with pytest.raises(ValueError, match="immutable"):
        run_scan(cfg, row, "deepmi/fastsurfer@sha256:" + "a" * 64)
    stats = destination / "stats/aseg+DKT.VINN.stats"
    stats.write_text(stats.read_text() + "\n")
    assert build_features(cfg) == {"failed": 1}
    assert runner.run(cfg, 1)["completed"] == 0


def test_container_failure_persists_failed_state(mri, tmp_path, monkeypatch):
    from src.fastsurfer import runner

    cfg = {
        "image": "deepmi/fastsurfer:cuda-v2.5.4",
        "version": "2.5.4",
        "device": "cpu",
        "viewagg_device": "cpu",
        "threads": 2,
        "timeout_seconds": 60,
        "surface": False,
        "output_dir": str(tmp_path / "outputs"),
        "processed_dir": str(tmp_path / "processed"),
    }

    def failure(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(runner.subprocess, "run", failure)
    row = {"patient_id": "SYNTHETIC", "scan_id": "SCAN_1", "source_mri_path": str(mri)}
    assert run_scan(cfg, row, "deepmi/fastsurfer@sha256:" + "a" * 64)["status"] == "failed"
    assert (
        json.loads((tmp_path / "outputs/SCAN_1/processing.json").read_text())["error"] == "CalledProcessError"
    )


@pytest.mark.parametrize("source_intact", [True, False])
def test_explicit_windows_alias_recovery_never_approves_qc(mri, tmp_path, source_intact):
    from src.common import write_json
    from src.data.preprocess_mri import convert_native
    from src.fastsurfer.recover import recover

    cfg = {
        "image": "deepmi/fastsurfer:cuda-v2.5.4",
        "version": "2.5.4",
        "output_dir": str(tmp_path / "outputs"),
        "processed_dir": str(tmp_path / "processed"),
    }
    processed = tmp_path / "processed"
    processed.mkdir()
    row = {"patient_id": "SYNTHETIC", "scan_id": "SCAN_1", "source_mri_path": str(mri)}
    pd.DataFrame([row]).to_csv(processed / "manifest.csv", index=False)
    native = processed / "native/SCAN_1.nii.gz"
    convert_native(mri, native)
    directory = tmp_path / "outputs/SCAN_1"
    (directory / "stats").mkdir(parents=True)
    (directory / "mri").mkdir()
    (directory / "stats/aseg+DKT.VINN.stats").write_text(stats_text())
    values = np.zeros((8, 8, 8), dtype=np.int16)
    values.flat[:6] = [17, 53, 4, 43, 1006, 2006]
    nib.save(nib.MGHImage(values, np.eye(4)), str(directory / "mri/aparc.DKTatlas+aseg.deep.mgz"))
    write_json(
        directory / "processing.json",
        {
            "status": "failed",
            "error": "OSError",
            "version": "2.5.4",
            "image": cfg["image"],
            "patient_id": row["patient_id"],
            "scan_id": row["scan_id"],
            "digest": "deepmi/fastsurfer@sha256:" + "a" * 64,
            "source_sha256": sha256(mri) if source_intact else "bad",
            "native_sha256": sha256(native),
        },
    )
    result = recover(cfg)
    assert result["visual_qc_approved"] is False
    assert result["recovered_outputs"] == int(source_intact)
    if source_intact:
        assert result["qc"] == {"pending_review": 1}
        assert (directory / "processing.io-failed.json").is_file()
        saved = json.loads((directory / "processing.json").read_text())
        assert saved["container_exit_code"] is None  # Do not invent historical exit status.


def test_timeout_stops_only_owned_named_container(mri, tmp_path, monkeypatch):
    from src.fastsurfer import runner

    cfg = {
        "image": "deepmi/fastsurfer:cuda-v2.5.4",
        "version": "2.5.4",
        "device": "cpu",
        "viewagg_device": "cpu",
        "threads": 2,
        "timeout_seconds": 1,
        "surface": False,
        "output_dir": str(tmp_path / "outputs"),
        "processed_dir": str(tmp_path / "processed"),
    }
    calls = []

    def timeout(command, **kwargs):
        calls.append(command)
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, 1)
        assert command[:4] == ["docker", "stop", "--time", "10"]
        assert command[4].startswith("neuropredict-fs-") and len(command) == 5
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", timeout)
    outcome = run_scan(
        cfg,
        {"patient_id": "SYNTHETIC", "scan_id": "SCAN_1", "source_mri_path": str(mri)},
        "deepmi/fastsurfer@sha256:" + "a" * 64,
    )
    assert outcome["error"] == "TimeoutExpired" and outcome["container_cleanup"] == "stopped"
    assert len(calls) == 2
