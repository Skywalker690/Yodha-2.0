"""Synthetic patients and demo tasks; no provider calls or real questionnaire content."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from backend.app.core.config import get_settings
from backend.app.models import Patient, Visit
from backend.app.services import mmse
from backend.app.services.assistant import build_context


@pytest.fixture
def assessment_case(authenticated, monkeypatch):
    monkeypatch.setattr(get_settings(), "mmse_protocol_path", None)
    monkeypatch.setattr(get_settings(), "ml_only", True)
    patient = authenticated.post("/patients", json={"code": "SYNTHETIC_MMSE", "age": 70}).json()
    patient = authenticated.post(
        f"/patients/{patient['id']}/visits",
        json={
            "label": "Baseline",
            "daysFromBaseline": 0,
        },
    ).json()
    return authenticated, patient["id"], patient["visits"][0]["id"]


def start(client, visit_id):
    response = client.post(f"/visits/{visit_id}/mmse", json={})
    assert response.status_code == 200, response.text
    return response.json()


def save(client, visit_id, attempt, points=None):
    if points is None:
        points = dict(mmse.DOMAINS)
    return client.patch(
        f"/visits/{visit_id}/mmse/{attempt['id']}",
        json={
            "revision": attempt["revision"],
            "assessedAt": attempt["assessedAt"],
            "items": [{"itemId": key, "points": value} for key, value in points.items()],
        },
    )


def finish(client, visit_id, attempt):
    response = client.post(
        f"/visits/{visit_id}/mmse/{attempt['id']}/complete",
        json={
            "revision": attempt["revision"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "points,expected", [(dict(mmse.DOMAINS), 30), ({key: 0 for key, _ in mmse.DOMAINS}, 0)]
)
def test_completed_demo_persists_without_creating_mmse(assessment_case, session_factory, points, expected):
    client, patient_id, visit_id = assessment_case
    attempt = start(client, visit_id)
    assert start(client, visit_id)["id"] == attempt["id"]
    assert "clinicianId" not in attempt
    saved = save(client, visit_id, attempt, points).json()
    completed = finish(client, visit_id, saved)
    assert completed["total"] == expected
    assert finish(client, visit_id, saved)["id"] == completed["id"]
    payload = client.get(f"/patients/{patient_id}").json()["visits"][0]["metadata"]
    assert payload["cognitiveDemoScore"] == expected and "MMSE" not in payload
    assert "definition" not in str(payload) and "clinicianId" not in str(payload)
    assert payload["mmseAssessment"]["completedCount"] == 1
    with session_factory() as db:
        assert db.get(Visit, visit_id).metadata_json["cognitiveDemoScore"] == expected
    assert save(client, visit_id, completed).status_code == 409
    next_attempt = start(client, visit_id)
    assert next_attempt["supersedes"] == completed["id"]
    assert next_attempt["total"] is None
    assert (
        client.get(f"/patients/{patient_id}").json()["visits"][0]["metadata"]["cognitiveDemoScore"]
        == expected
    )


@pytest.mark.parametrize("invalid", [True, -1, 6, 1.5, "1"])
def test_invalid_points_rejected(assessment_case, invalid):
    client, _, visit_id = assessment_case
    attempt = start(client, visit_id)
    assert save(client, visit_id, attempt, {"time_orientation": invalid}).status_code == 422


def test_partial_missing_and_stale_drafts(assessment_case):
    client, patient_id, visit_id = assessment_case
    attempt = start(client, visit_id)
    saved = save(client, visit_id, attempt, {"time_orientation": 0, "place_orientation": None}).json()
    assert saved["total"] is None and saved["items"]["time_orientation"] == 0
    assert start(client, visit_id)["items"] == saved["items"]
    assert save(client, visit_id, attempt).status_code == 409
    assert (
        client.post(
            f"/visits/{visit_id}/mmse/{attempt['id']}/complete", json={"revision": saved["revision"]}
        ).status_code
        == 422
    )
    assert "cognitiveDemoScore" not in client.get(f"/patients/{patient_id}").json()["visits"][0]["metadata"]


def test_unknown_duplicate_total_and_future_time_rejected(assessment_case):
    client, _, visit_id = assessment_case
    attempt = start(client, visit_id)
    assert save(client, visit_id, attempt, {"unknown": 1}).status_code == 422
    assert save(client, visit_id, attempt, {"writing": 2}).status_code == 422
    body = {
        "revision": 0,
        "assessedAt": attempt["assessedAt"],
        "items": [
            {"itemId": "writing", "points": 1},
            {"itemId": "writing", "points": 0},
        ],
    }
    path = f"/visits/{visit_id}/mmse/{attempt['id']}"
    assert client.patch(path, json=body).status_code == 422
    body["items"] = []
    body["total"] = 30
    assert client.patch(path, json=body).status_code == 422
    del body["total"]
    body["assessedAt"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert client.patch(path, json=body).status_code == 422


@pytest.mark.parametrize("upload_first", [True, False])
def test_mri_and_assessment_preserved_in_both_orders(assessment_case, mri, session_factory, upload_first):
    client, patient_id, visit_id = assessment_case
    with session_factory() as db:
        visit = db.get(Visit, visit_id)
        visit.metadata_json = {"MMSE": 24, "CDR": 0, "Age": 70}
        db.commit()

    def upload():
        response = client.post(
            f"/visits/{visit_id}/upload",
            files={
                "file": ("synthetic.nii.gz", mri.read_bytes(), "application/gzip"),
            },
        )
        assert response.status_code == 202, response.text

    if upload_first:
        upload()
    attempt = start(client, visit_id)
    finish(client, visit_id, save(client, visit_id, attempt).json())
    if not upload_first:
        upload()
    payload = client.get(f"/patients/{patient_id}").json()["visits"][0]
    assert payload["hasMri"] and payload["previewUrl"]
    assert payload["metadata"]["shape"] == [24, 24, 24]
    assert payload["metadata"]["MMSE"] == 24
    assert payload["metadata"]["cognitiveDemoScore"] == 30
    assert payload["metadata"]["CDR"] == 0


def test_owned_visit_and_assessment_isolation(assessment_case):
    client, patient_id, visit_id = assessment_case
    attempt = start(client, visit_id)
    patient = client.post(
        f"/patients/{patient_id}/visits", json={"label": "Follow up", "daysFromBaseline": 365}
    ).json()
    other_visit = patient["visits"][-1]["id"]
    assert save(client, other_visit, attempt).status_code == 404
    client.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert client.post(f"/visits/{visit_id}/mmse", json={}).status_code == 404
    assert save(client, visit_id, attempt).status_code == 404
    client.post("/auth/logout")
    assert client.post(f"/visits/{visit_id}/mmse", json={}).status_code == 401


def test_imported_scores_are_protected(assessment_case, session_factory):
    client, patient_id, visit_id = assessment_case
    with session_factory() as db:
        db.get(Patient, patient_id).source = "oasis-2"
        db.commit()
    assert client.post(f"/visits/{visit_id}/mmse", json={}).status_code == 409


def test_completed_demo_context_is_distinct_from_mmse(assessment_case, session_factory, monkeypatch):
    client, patient_id, visit_id = assessment_case
    attempt = start(client, visit_id)
    finish(client, visit_id, save(client, visit_id, attempt).json())
    monkeypatch.setattr(
        "backend.app.services.assistant.patient_forecast",
        lambda *args: {"prediction": {"status": "unavailable"}},
    )
    with session_factory() as db:
        context, _ = build_context(db, db.get(Patient, patient_id))
    assert context["observations"][0]["recordedClinicalValues"]["MMSE"] is None
    assert context["observations"][0]["demoCognitiveAssessment"]["score"] == 30
    assert "clinicianId" not in str(context) and "lantern" not in str(context)


def test_standard_protocol_compatibility_uses_fixture_only(assessment_case, monkeypatch):
    client, patient_id, visit_id = assessment_case
    definition = mmse.demo_protocol()
    # Exercise the standard storage branch with a synthetic fixture, never real content.
    definition.update(instrument="mmse-original", version="synthetic-test-only")
    monkeypatch.setattr(mmse, "load_protocol", lambda: definition)
    attempt = start(client, visit_id)
    finish(client, visit_id, save(client, visit_id, attempt).json())
    payload = client.get(f"/patients/{patient_id}").json()["visits"][0]["metadata"]
    assert payload["MMSE"] == 30 and "cognitiveDemoScore" not in payload


def test_protocol_configuration_fails_explicitly(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "mmse_protocol_path", tmp_path / "missing.json")
    with pytest.raises(HTTPException) as error:
        mmse.load_protocol()
    assert error.value.status_code == 503


def test_patch_cors_preflight(assessment_case):
    client, _, visit_id = assessment_case
    response = client.options(
        f"/visits/{visit_id}/mmse/draft",
        headers={
            "origin": get_settings().allowed_origins.split(",")[0],
            "access-control-request-method": "PATCH",
        },
    )
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]
