"""Synthetic owned-artifact/review/report integration, no real patient records."""

import json

import pytest
from pypdf import PdfReader

from backend.app.models import Analysis, Patient, Visit
from backend.app.services.storage import resolve_key
from ml.anatomy.contracts import AnatomyResult, AnatomyVisit, StructuralForecast
from ml.anatomy.measurements import changes
from ml.contracts import ProgressionResult
from src.common import sha256, write_json
from src.fastsurfer.regions import REGIONS


@pytest.fixture
def anatomy_job(session_factory):
    directory = resolve_key("derived/synthetic-anatomy")
    manifest, inputs, items = {}, [], []
    with session_factory() as db:
        db.add(Patient(id="anatomy-patient", owner_id="researcher-a", code="SYNTHETIC_ANATOMY"))
        db.flush()
        for index, day in enumerate((0, 600)):
            vid = f"anatomy-v{index}"
            raw = resolve_key(f"raw/anatomy-v{index}.nii.gz")
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(b"synthetic MRI for digest checks")
            inputs.append({"visit_id": vid, "mri_key": f"raw/anatomy-v{index}.nii.gz"})
            db.add(
                Visit(
                    id=vid,
                    patient_id="anatomy-patient",
                    label=f"Synthetic visit {index + 1}",
                    days_from_baseline=day,
                    mri_key=inputs[-1]["mri_key"],
                )
            )
            seg = directory / f"fastsurfer/scan_{index}/mri/aparc.DKTatlas+aseg.deep.mgz"
            stats = directory / f"fastsurfer/scan_{index}/stats/aseg+DKT.VINN.stats"
            seg.parent.mkdir(parents=True, exist_ok=True)
            stats.parent.mkdir(parents=True, exist_ok=True)
            seg.write_bytes(b"synthetic segmentation")
            stats.write_bytes(b"synthetic verified statistics")
            item = AnatomyVisit(
                visit_id=vid,
                days_from_baseline=day,
                qc="pending_review",
                source_sha256=sha256(raw),
                segmentation_sha256=sha256(seg),
                statistics_sha256=sha256(stats),
                container_digest="deepmi/fastsurfer@sha256:" + "d" * 64,
                volumes_mm3={k: 4000 - index * 200 for k in REGIONS},
                mask_volumes_mm3={k: 3990 - index * 200 for k in REGIONS},
                hippocampal_asymmetry_percent=0,
            )
            items.append(item)
            write_json(
                directory / f"fastsurfer/scan_{index}/processing.json",
                {
                    "status": "completed",
                    "version": "2.5.4",
                    "scan_id": f"scan_{index}",
                    "patient_id": "anatomy-patient",
                    "digest": item.container_digest,
                    "source_sha256": item.source_sha256,
                    "output_sha256": {
                        "mri/aparc.DKTatlas+aseg.deep.mgz": item.segmentation_sha256,
                        "stats/aseg+DKT.VINN.stats": item.statistics_sha256,
                    },
                },
            )
            manifest[vid] = {}
            for name in ["regions", "segmentation", *REGIONS]:
                path = directory / f"visit_{index}/{name}.nii.gz"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic owned mask " + name.encode())
                manifest[vid][name] = {
                    "relative_path": path.relative_to(directory).as_posix(),
                    "sha256": sha256(path),
                }
        anatomy = AnatomyResult(
            visits=items,
            changes=changes(items),
            forecast=StructuralForecast(
                cutoff_visit_id=items[-1].visit_id, interval_days=365, warnings=["No trained spatial model."]
            ),
        )
        result = ProgressionResult(
            patient_id="anatomy-patient",
            visit_ids=[v.visit_id for v in items],
            selected_visit=items[-1].visit_id,
            days_from_baseline=[v.days_from_baseline for v in items],
            risk_scores=[],
            biomarkers={},
            output_mode="anatomy",
            model_version=anatomy.version,
            anatomy=anatomy,
            caveats=["Synthetic research estimate."],
        )
        db.add(
            Analysis(
                id="synthetic-anatomy",
                patient_id="anatomy-patient",
                visit_id=items[-1].visit_id,
                output_mode="anatomy",
                status="completed",
                model_version=anatomy.version,
                input_json=inputs,
                result_json=result.model_dump(),
            )
        )
        db.commit()
    write_json(directory / "anatomy-artifacts.json", {"version": anatomy.version, "visits": manifest})
    return directory


def test_owned_artifact_tamper_and_review_binding(authenticated, anatomy_job):
    c = authenticated
    base = "/analysis/synthetic-anatomy"
    artifact = base + "/visits/anatomy-v0/anatomy/regions"
    assert c.get(artifact).status_code == 200
    assert c.get(base + "/visits/anatomy-v0/anatomy/unknown").status_code == 404
    assert c.post(base + "/anatomy-qc/anatomy-v0", json={"visualReviewConfirmed": False}).status_code == 422
    c.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert c.get(artifact).status_code == 404
    assert c.post(base + "/anatomy-qc/anatomy-v0", json={"visualReviewConfirmed": True}).status_code == 404
    c.post("/auth/login", json={"email": "a@example.test", "password": "correct-password-123"})
    region = anatomy_job / "visit_0/regions.nii.gz"
    original = region.read_bytes()
    region.write_bytes(b"tampered")
    assert c.get(artifact).status_code == 404
    assert c.post(base + "/anatomy-qc/anatomy-v0", json={"visualReviewConfirmed": True}).status_code == 409
    region.write_bytes(original)
    reviewed = c.post(base + "/anatomy-qc/anatomy-v0", json={"visualReviewConfirmed": True})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["resultJson"]["anatomy"]["visits"][0]["reviewerId"] == "researcher-a"
    assert reviewed.json()["resultJson"]["anatomy"]["changes"][0]["regions"] == {}
    assert c.post(base + "/anatomy-qc/anatomy-v0", json={"visualReviewConfirmed": True}).status_code == 409
    second = c.post(base + "/anatomy-qc/anatomy-v1", json={"visualReviewConfirmed": True})
    assert second.json()["resultJson"]["anatomy"]["changes"][0]["status"] == "ok"
    patient = c.get("/patients/anatomy-patient").json()
    assert patient["completedAnatomy"]["id"] == "synthetic-anatomy"
    assert patient["latestCompleted"] is None


def test_report_explicit_analysis_and_preserved_legacy_default(authenticated, anatomy_job):
    c = authenticated
    assert c.post("/reports/anatomy-patient").status_code == 409
    response = c.post("/reports/anatomy-patient?analysis_id=synthetic-anatomy")
    assert response.status_code == 201, response.text
    record = response.json()
    text = "\n".join(
        page.extract_text() for page in PdfReader(resolve_key(f"reports/{record['id']}.pdf")).pages
    )
    assert "Predicted anatomy - unavailable" in text
    assert "pending_review" in text and "Stats/eTIV" in text
    assert "Source SHA256" in text
    assert record["analysisId"] == "synthetic-anatomy"
    c.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert c.post("/reports/anatomy-patient?analysis_id=synthetic-anatomy").status_code == 404


def test_review_rejects_changed_stats_or_incomplete_manifest(authenticated, anatomy_job):
    path = anatomy_job / "anatomy-artifacts.json"
    manifest = json.loads(path.read_text())
    del manifest["visits"]["anatomy-v0"]["segmentation"]
    path.write_text(json.dumps(manifest))
    assert (
        authenticated.post(
            "/analysis/synthetic-anatomy/anatomy-qc/anatomy-v0", json={"visualReviewConfirmed": True}
        ).status_code
        == 409
    )
