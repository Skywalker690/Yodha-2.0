import io
import gzip
import json

import nibabel as nib
import numpy as np

from pypdf import PdfReader

from backend.app.models import Analysis
from backend.app.services.storage import resolve_key
from backend.app.services.analysis import cache_key
from backend.app.workers.runner import claim_next, execute, recover_interrupted


def create_case(client):
    patient = client.post("/patients", json={"code": "TEST_CASE", "age": 72, "sex": "Female"}).json()
    for index in range(3):
        response = client.post(
            f"/patients/{patient['id']}/visits",
            json={"label": f"Visit {index + 1}", "daysFromBaseline": index * 365},
        )
        assert response.status_code == 201
    return client.get(f"/patients/{patient['id']}").json()


def test_authentication_and_cookie(client):
    assert client.get("/patients").status_code == 401
    assert client.get("/visits/unknown/volume").status_code == 401
    assert client.get("/analysis/unknown/visits/unknown/difference-volume").status_code == 401
    response = client.post("/auth/login", json={"email": "a@example.test", "password": "wrong"})
    assert response.status_code == 401
    response = client.post(
        "/auth/login", json={"email": "a@example.test", "password": "correct-password-123"}
    )
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert client.get("/auth/me").json()["email"] == "a@example.test"
    assert "password" not in str(client.get("/auth/me").json())
    client.post("/auth/logout")
    assert client.get("/patients").status_code == 401


def test_patient_validation_uniqueness_ownership_and_chronology(authenticated):
    c = authenticated
    assert c.post("/patients", json={"code": "../../oops"}).status_code == 422
    p = create_case(c)
    assert c.get(f"/visits/{p['visits'][0]['id']}/volume").status_code == 404
    assert c.post("/patients", json={"code": "TEST_CASE"}).status_code == 409
    assert (
        c.post(
            f"/patients/{p['id']}/visits", json={"label": "duplicate", "daysFromBaseline": 365}
        ).status_code
        == 409
    )
    assert [v["daysFromBaseline"] for v in p["visits"]] == [0, 365, 730]
    c.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert c.get(f"/patients/{p['id']}").status_code == 404
    assert c.get("/patients").json() == []


def test_upload_rejects_invalid_extension_type_and_structure(authenticated):
    c = authenticated
    p = create_case(c)
    vid = p["visits"][0]["id"]
    assert (
        c.post(
            f"/visits/{vid}/upload", files={"file": ("a.exe", b"bad", "application/octet-stream")}
        ).status_code
        == 415
    )
    assert c.post(f"/visits/{vid}/upload", files={"file": ("a.nii", b"bad", "text/html")}).status_code == 415
    assert (
        c.post(
            f"/visits/{vid}/upload", files={"file": ("a.nii", b"bad", "application/octet-stream")}
        ).status_code
        == 422
    )
    assert not c.get(f"/patients/{p['id']}").json()["visits"][0]["hasMri"]


def test_complete_workflow_precomputed_reports_and_isolation(authenticated, mri, session_factory):
    c = authenticated
    p = create_case(c)
    for visit in p["visits"]:
        response = c.post(
            f"/visits/{visit['id']}/upload",
            files={"file": ("../../scan.nii.gz", mri.read_bytes(), "application/gzip")},
        )
        assert response.status_code == 202, response.text
        job = response.json()
        # No inference happens inside the upload request.
        assert job["status"] == "queued" and job["resultJson"] is None
        assert "mri_key" not in response.text and "C:\\" not in response.text
        claimed = claim_next()
        assert claimed == job["id"]
        assert c.get(f"/analysis/{claimed}").json()["status"] == "processing"
        execute(claimed)
        completed = c.get(f"/analysis/{claimed}").json()
        assert completed["status"] == "completed", completed
    completed_patient = c.get(f"/patients/{p['id']}").json()
    assert len(completed_patient["latestCompleted"]["resultJson"]["visitIds"]) == 3
    assert completed_patient["latestCompleted"]["confidence"] is None
    assert completed_patient["latestCompleted"]["resultJson"]["volumeOverlaysReady"]
    last = p["visits"][-1]["id"]
    raw = c.get(f"/visits/{last}/volume")
    assert raw.status_code == 200 and raw.content == mri.read_bytes()
    assert "research-mri.nii.gz" in raw.headers["content-disposition"]
    assert completed_patient["visits"][-1]["volumeUrl"] == f"/api/visits/{last}/volume"
    response = c.post(f"/analysis/{last}", json={"outputMode": "precomputed"})
    assert response.status_code == 202
    assert c.post(f"/analysis/{last}", json={"outputMode": "inference"}).status_code == 409
    execute(response.json()["id"])
    assert c.get(f"/analysis/{response.json()['id']}").json()["outputMode"] == "precomputed"
    difference_url = f"/analysis/{response.json()['id']}/visits/{last}/difference-volume"
    difference = c.get(difference_url)
    assert difference.status_code == 200
    assert "research-difference.nii.gz" in difference.headers["content-disposition"]
    image = nib.Nifti1Image.from_bytes(gzip.decompress(difference.content))
    assert image.shape == (64, 64, 64) and np.isfinite(image.get_fdata()).all()
    assert c.get(difference_url.replace(last, "unknown")).status_code == 404
    # Old cache contracts remain usable but must never imply a missing 3D artifact.
    with session_factory() as db:
        cached_job = db.get(Analysis, response.json()["id"])
        cached_job.result_json = {**cached_job.result_json, "volume_overlays_ready": False}
        db.commit()
    assert c.get(difference_url).status_code == 404
    assert len(c.get(f"/patients/{p['id']}/heatmaps").json()) == 3
    assert len(c.get(f"/patients/{p['id']}/biomarkers").json()) == 2
    preview = c.get(f"/visits/{last}/preview")
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
    report = c.post(f"/reports/{p['id']}")
    assert report.status_code == 201, report.text
    download = report.json()["downloadUrl"].removeprefix("/api")
    pdf = c.get(download)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    text = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Not a medical diagnosis" in text and "Precomputed" in text
    assert len(c.get("/reports").json()) >= 1
    c.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert c.get(download).status_code == 404
    assert c.get(f"/visits/{last}/preview").status_code == 404
    assert c.get(f"/visits/{last}/volume").status_code == 404
    assert c.get(f"/analysis/{job['id']}/visits/{last}/difference-volume").status_code == 404
    assert c.get(f"/analysis/{job['id']}").status_code == 404


def test_worker_failure_recovery_and_missing_cache(authenticated, session_factory):
    c = authenticated
    p = create_case(c)
    assert c.post(f"/analysis/{p['visits'][-1]['id']}", json={"outputMode": "precomputed"}).status_code == 422
    with session_factory() as db:
        job = Analysis(
            patient_id=p["id"],
            visit_id=p["visits"][0]["id"],
            input_json=[
                {"visit_id": p["visits"][0]["id"], "days_from_baseline": 0, "mri_key": "raw/missing.nii.gz"}
            ],
        )
        db.add(job)
        db.commit()
        job_id = job.id
    execute(job_id)
    assert c.get(f"/analysis/{job_id}").json()["status"] == "failed"
    with session_factory() as db:
        job = db.get(Analysis, job_id)
        job.status = "processing"
        db.commit()
    recover_interrupted()
    assert "restart" in c.get(f"/analysis/{job_id}").json()["error"]


def test_storage_paths_and_csrf(authenticated):
    import pytest

    for key in ["../../outside.txt", "C:\\secrets", "/etc/passwd"]:
        with pytest.raises(ValueError):
            resolve_key(key)
    assert (
        authenticated.post(
            "/patients", json={"code": "INTRUDER"}, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )


def test_report_requires_completed_analysis(authenticated):
    p = create_case(authenticated)
    assert authenticated.post(f"/reports/{p['id']}").status_code == 409


def test_precomputed_rejects_missing_claimed_3d_artifacts_but_accepts_legacy_contract(
    authenticated, mri, session_factory,
):
    c = authenticated
    p = create_case(c)
    visit = p["visits"][0]["id"]
    response = c.post(
        f"/visits/{visit}/upload",
        files={"file": ("scan.nii.gz", mri.read_bytes(), "application/gzip")},
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    execute(job_id)
    with session_factory() as db:
        job = db.get(Analysis, job_id)
        assert job.status == "completed"
        cache = resolve_key(cache_key(job.input_json))
    # Only isolated, newly generated test artifacts are modified here.
    payload = json.loads(cache.read_text(encoding="utf-8"))
    resolve_key(f"{payload['artifact_prefix']}/0-difference.nii.gz").unlink()
    new_job = c.post(f"/analysis/{visit}", json={"outputMode": "precomputed"}).json()
    execute(new_job["id"])
    assert c.get(f"/analysis/{new_job['id']}").json()["status"] == "failed"
    del payload["result"]["volume_overlays_ready"]
    cache.write_text(json.dumps(payload), encoding="utf-8")
    legacy_job = c.post(f"/analysis/{visit}", json={"outputMode": "precomputed"}).json()
    execute(legacy_job["id"])
    legacy = c.get(f"/analysis/{legacy_job['id']}").json()
    assert legacy["status"] == "completed" and not legacy["resultJson"]["volumeOverlaysReady"]
    assert c.get(f"/analysis/{legacy_job['id']}/visits/{visit}/difference-volume").status_code == 404
