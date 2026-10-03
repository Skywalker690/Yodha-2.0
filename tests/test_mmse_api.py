"""Assessment completion uses synthetic records in the isolated SQLite fixtures."""

import pytest

from backend.app.core.config import get_settings
from backend.app.services import mmse


@pytest.fixture
def assessment_case(authenticated, monkeypatch):
    monkeypatch.setattr(get_settings(), "mmse_protocol_path", None)
    monkeypatch.setattr(get_settings(), "ml_only", True)
    response = authenticated.post("/patients", json={"age": 70, "nwbvFraction": 0.75})
    assert response.status_code == 201, response.text
    patient = response.json()
    return authenticated, patient["id"], patient["visits"][0]["id"]


def start(client, visit_id):
    response = client.post(f"/visits/{visit_id}/mmse", json={})
    assert response.status_code == 200, response.text
    return response.json()


def save(client, visit_id, attempt, points):
    return client.patch(
        f"/visits/{visit_id}/mmse/{attempt['id']}",
        json={
            "revision": attempt["revision"],
            "assessedAt": attempt["assessedAt"],
            "items": [{"itemId": key, "points": value} for key, value in points.items()],
        },
    )


@pytest.mark.parametrize("zero", [False, True])
def test_complete_all_tasks_persists_separate_demo_total(assessment_case, zero):
    client, patient_id, visit_id = assessment_case
    attempt = start(client, visit_id)
    assert start(client, visit_id)["id"] == attempt["id"]
    points = {key: 0 if zero else maximum for key, maximum in mmse.DOMAINS}
    response = save(client, visit_id, attempt, points)
    assert response.status_code == 200, response.text
    saved = response.json()
    completed = client.post(
        f"/visits/{visit_id}/mmse/{attempt['id']}/complete",
        json={"revision": saved["revision"]},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["total"] == (0 if zero else 30)
    metadata = client.get(f"/patients/{patient_id}").json()["visits"][0]["metadata"]
    assert metadata["cognitiveDemoScore"] == (0 if zero else 30)
    assert metadata["Age"] == 70 and metadata["nWBV"] == 0.75
    assert "MMSE" not in metadata
    assert metadata["mmseAssessment"]["status"] == "completed"
    assert "clinicianId" not in completed.json()
    assert "definition" not in metadata["mmseAssessment"]


def test_missing_scores_block_completion_and_can_be_finished_after_resume(assessment_case):
    client, _, visit_id = assessment_case
    attempt = start(client, visit_id)
    saved = save(client, visit_id, attempt, {"time_orientation": 0}).json()
    path = f"/visits/{visit_id}/mmse/{attempt['id']}/complete"
    response = client.post(path, json={"revision": saved["revision"]})
    assert response.status_code == 422
    assert "every required task" in response.json()["detail"]
    resumed = start(client, visit_id)
    assert resumed["items"] == {"time_orientation": 0}
    assert save(client, visit_id, attempt, dict(mmse.DOMAINS)).status_code == 409
    saved = save(client, visit_id, resumed, dict(mmse.DOMAINS)).json()
    assert client.post(path, json={"revision": saved["revision"]}).status_code == 200


def test_mri_upload_preserves_completed_assessment(assessment_case, mri):
    client, patient_id, visit_id = assessment_case
    attempt = start(client, visit_id)
    saved = save(client, visit_id, attempt, dict(mmse.DOMAINS)).json()
    completed = client.post(
        f"/visits/{visit_id}/mmse/{attempt['id']}/complete", json={"revision": saved["revision"]}
    )
    assert completed.status_code == 200, completed.text
    response = client.post(
        f"/visits/{visit_id}/upload",
        data={"age": "70", "nwbvFraction": "0.75"},
        files={"file": ("synthetic.nii.gz", mri.read_bytes(), "application/gzip")},
    )
    assert response.status_code == 202, response.text
    metadata = client.get(f"/patients/{patient_id}").json()["visits"][0]["metadata"]
    assert metadata["cognitiveDemoScore"] == 30
    assert metadata["mmseAssessment"]["completedCount"] == 1
