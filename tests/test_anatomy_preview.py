"""Saved previews preserve exact subject/time, ownership and file integrity."""

import json

import pytest

from backend.app.core.config import get_settings
from backend.app.models import Analysis, Patient, Visit
from backend.app.services.anatomy_preview import ARTIFACTS
from backend.app.services.storage import resolve_key
from src.common import sha256, write_json


@pytest.fixture
def preview_files(tmp_path, monkeypatch, session_factory):
    directory = tmp_path / "preview"
    directory.mkdir()
    monkeypatch.setattr(get_settings(), "anatomy_preview_dir", directory)
    history = []
    with session_factory() as db:
        db.add(Patient(id="preview-patient", owner_id="researcher-a", code="SYNTH_PREVIEW"))
        db.flush()
        for i, day in enumerate([0, 600]):
            key = f"raw/preview-{i}.nii.gz"
            source = resolve_key(key)
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(f"synthetic source {i}".encode())
            db.add(Visit(id=f"preview-v{i}", patient_id="preview-patient", label=f"Visit {i}",
                         days_from_baseline=day, mri_key=key))
            history.append({"visit_id": f"preview-v{i}", "days_from_baseline": day,
                            "source_sha256": sha256(source)})
        db.commit()
    manifest = {"version": "saved-version", "cutoff_visit_id": "preview-v1", "interval_days": 229,
                "source_sha256": [v["source_sha256"] for v in history], "model_sha256": "e" * 64,
                "artifacts": {}}
    for name, kind in ARTIFACTS.items():
        path = directory / (name + (".gii" if kind == "mesh" else ".nii.gz"))
        path.write_bytes(f"synthetic {name}".encode())
        manifest["artifacts"][name] = {"relative_path": path.name, "sha256": sha256(path), "kind": kind}
    payloads = {
        "case": ("case.json", {"subject_id": "SYNTH_PREVIEW", "interval_days": 229, "history": history}),
        "manifest": ("future-artifacts.json", manifest),
        "evaluation": ("evaluation.json", {"version": "saved-version", "synthetic": False,
                                            "release_failures": ["Incomplete research candidate"]}),
    }
    descriptor = {"version": "saved-anatomy-preview-v1"}
    for key, (filename, payload) in payloads.items():
        write_json(directory / filename, payload)
        descriptor[key] = {"relative_path": filename, "sha256": sha256(directory / filename)}
    write_json(directory / "preview.json", descriptor)
    return directory


def test_saved_preview_is_read_only_and_keeps_original_interval(authenticated, preview_files, session_factory):
    response = authenticated.get("/anatomy-preview")
    assert response.status_code == 200
    data = response.json()
    assert data["intervalDays"] == 229 and data["cutoffVisitId"] == "preview-v1"
    assert data["promoted"] is False and data["clinicalValidation"] is False
    assert data["provenance"] == "saved_retrospective_evaluation"
    assert "relative_path" not in response.text
    assert authenticated.get("/anatomy-preview/mri").content == b"synthetic mri"
    assert "no-store" in authenticated.get("/anatomy-preview/mri").headers["cache-control"]
    assert authenticated.get("/anatomy-preview/pull").status_code == 404
    with session_factory() as db:
        assert db.query(Analysis).count() == 0


def test_saved_preview_rejects_other_researcher_and_changed_source(authenticated, preview_files):
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get("/anatomy-preview").json()["status"] == "unavailable"
    assert authenticated.get("/anatomy-preview/mri").status_code == 404
    authenticated.post("/auth/login", json={"email": "a@example.test", "password": "correct-password-123"})
    resolve_key("raw/preview-0.nii.gz").write_bytes(b"changed source")
    assert authenticated.get("/anatomy-preview/mri").status_code == 404


def test_saved_preview_rejects_tampered_artifact_and_manifest(authenticated, preview_files):
    mri = preview_files / "mri.nii.gz"
    original = mri.read_bytes()
    mri.write_bytes(b"changed future MRI")
    assert authenticated.get("/anatomy-preview/mri").status_code == 404
    mri.write_bytes(original)
    manifest = json.loads((preview_files / "future-artifacts.json").read_text())
    manifest["interval_days"] = 365
    write_json(preview_files / "future-artifacts.json", manifest)
    assert authenticated.get("/anatomy-preview").json()["status"] == "unavailable"


def test_saved_preview_rejects_path_escape(authenticated, preview_files):
    descriptor = json.loads((preview_files / "preview.json").read_text())
    descriptor["case"]["relative_path"] = "../case.json"
    write_json(preview_files / "preview.json", descriptor)
    assert authenticated.get("/anatomy-preview/mri").status_code == 404


def test_saved_preview_rejects_wrong_interval_profile(authenticated, preview_files):
    import shutil
    shutil.copytree(preview_files, preview_files / "365", ignore=shutil.ignore_patterns("365"))
    assert authenticated.get("/anatomy-preview?intervalDays=365").json()["status"] == "unavailable"
    assert authenticated.get("/anatomy-preview/mri?intervalDays=365").status_code == 404


def test_saved_preview_links_only_the_matching_acquired_mask(authenticated, preview_files, session_factory):
    assert authenticated.get("/anatomy-preview").json()["observedLabelsUrl"] is None
    case = json.loads((preview_files / "case.json").read_text())
    cutoff = case["history"][-1]
    cutoff["segmentation_sha256"] = "a" * 64
    write_json(preview_files / "case.json", case)
    descriptor = json.loads((preview_files / "preview.json").read_text())
    descriptor["case"]["sha256"] = sha256(preview_files / "case.json")
    write_json(preview_files / "preview.json", descriptor)
    mask = resolve_key("derived/preview-measured/masks/regions.nii.gz")
    mask.parent.mkdir(parents=True, exist_ok=True)
    mask.write_bytes(b"synthetic acquired hippocampus mask")
    write_json(mask.parent.parent / "anatomy-artifacts.json", {
        "visits": {"preview-v1": {"regions": {
            "relative_path": "masks/regions.nii.gz", "sha256": sha256(mask),
        }}},
    })
    with session_factory() as db:
        db.add(Analysis(id="preview-measured", patient_id="preview-patient", visit_id="preview-v1",
                        status="completed", output_mode="anatomy", result_json={
                            "visit_ids": ["preview-v1"], "anatomy": {"visits": [cutoff]},
                        }))
        db.commit()
    url = "/api/analysis/preview-measured/visits/preview-v1/anatomy/regions"
    assert authenticated.get("/anatomy-preview").json()["observedLabelsUrl"] == url
    assert authenticated.get(url.removeprefix("/api")).content == mask.read_bytes()
    mask.write_bytes(b"changed acquired mask")
    assert authenticated.get(url.removeprefix("/api")).status_code == 404
    with session_factory() as db:
        job = db.get(Analysis, "preview-measured")
        job.result_json = {"visit_ids": ["preview-v1"], "anatomy": {"visits": [
            {**cutoff, "segmentation_sha256": "b" * 64},
        ]}}
        db.commit()
    assert authenticated.get("/anatomy-preview").json()["observedLabelsUrl"] is None
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get(url.removeprefix("/api")).status_code == 404
