"""Production-style serving policy tests with synthetic cases only."""

import pytest
from sqlalchemy import select

from backend.app.core.config import Settings, get_settings
from backend.app.models import Analysis
from backend.app.workers.runner import execute


@pytest.fixture
def strict(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "ml_only", True)
    monkeypatch.setattr(settings, "forecast_artifact_dir", tmp_path / "no-models")
    monkeypatch.setattr(settings, "forecast_processed_dir", tmp_path / "no-study")
    return settings


def case(client):
    patient = client.post("/patients", json={"code": "STRICT_SYNTHETIC"}).json()
    result = client.post(
        f"/patients/{patient['id']}/visits", json={"label": "Baseline", "daysFromBaseline": 0}
    ).json()
    return patient["id"], result["visits"][0]["id"]


def test_ml_only_is_default_without_env_optout(monkeypatch):
    monkeypatch.delenv("ML_ONLY")
    assert Settings(_env_file=None).ml_only is True


@pytest.mark.parametrize("mode", ["demo", "inference", "precomputed", "trained"])
def test_all_legacy_prediction_modes_are_denied(authenticated, strict, mode, session_factory):
    patient, visit = case(authenticated)
    response = authenticated.post(f"/analysis/{visit}", json={"outputMode": mode})
    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]
    assert authenticated.get(f"/patients/{patient}").json()["latestCompleted"] is None
    with session_factory() as db:
        assert db.scalars(select(Analysis)).all() == []


def test_upload_stores_mri_without_rule_based_job(authenticated, strict, mri, session_factory):
    patient, visit = case(authenticated)
    with mri.open("rb") as scan:
        response = authenticated.post(
            f"/visits/{visit}/upload", files={"file": ("synthetic.nii.gz", scan, "application/gzip")}
        )
    assert response.status_code == 202 and response.json()["status"] == "stored"
    assert authenticated.get(f"/patients/{patient}").json()["visits"][0]["hasMri"]
    with session_factory() as db:
        assert db.scalars(select(Analysis)).all() == []


def test_forecast_has_no_clinical_fallback_and_preserves_ownership(authenticated, strict):
    patient, _ = case(authenticated)
    assert authenticated.get(f"/patients/{patient}/forecast?model_kind=clinical").status_code == 409
    response = authenticated.get(f"/patients/{patient}/forecast")
    assert response.status_code == 200
    assert all(value is None for value in response.json()["prediction"]["probabilities"].values())
    assert authenticated.get("/patients/not-owned/forecast").status_code == 404
    health = authenticated.get("/health").json()
    assert health["servingPolicy"] == "ml_only" and not health["forecastReadiness"]["ready"]


def test_worker_does_not_execute_old_queued_rules(strict, session_factory, monkeypatch):
    from backend.app.models import Patient, Visit
    from backend.app.workers import runner

    with session_factory() as db:
        patient = Patient(code="QUEUED_SYNTHETIC", owner_id="researcher-a")
        db.add(patient)
        db.flush()
        visit = Visit(patient_id=patient.id, label="Baseline", days_from_baseline=0)
        db.add(visit)
        db.flush()
        job = Analysis(patient_id=patient.id, visit_id=visit.id, input_json=[], output_mode="inference")
        db.add(job)
        db.commit()
        job_id = job.id
    monkeypatch.setattr(runner, "run_pipeline", lambda *args: pytest.fail("Rule pipeline must not execute"))
    execute(job_id)
    with session_factory() as db:
        job = db.get(Analysis, job_id)
        assert job.status == "failed" and "No legacy model" in job.error
