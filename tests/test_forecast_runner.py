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
        (destination / "stats/aseg+DKT.stats").write_text(stats_text())
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
    with pytest.raises(ValueError, match="immutable"):
        run_scan(cfg, row, "deepmi/fastsurfer@sha256:" + "a" * 64)
    stats = destination / "stats/aseg+DKT.stats"
    stats.write_text(stats.read_text() + "\n")
    assert build_features(cfg) == {"failed": 1}


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
