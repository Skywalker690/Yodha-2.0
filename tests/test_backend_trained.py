"""Backend integration using synthetic MRIs, an isolated DB and a stub checkpoint.

The ML loader/weight round-trip is covered separately by the ML owner. These tests
exercise orchestration without loading participant data or the configured real run.
"""

import hashlib
import io
from pathlib import Path

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from backend.app.core.config import ROOT, Settings, get_settings
from backend.app.models import Analysis, Biomarker, Patient, Visit
from backend.app.schemas.contracts import AnalysisCreate
from backend.app.services.analysis import COVARIATES, cache_key
from backend.app.services.storage import resolve_key
from backend.app.workers import runner
from ml import trained_inference
from ml.contracts import MODEL_VERSION, TrainedPrediction
from ml.inference import run_pipeline
from ml.preprocessing import prepare


def source_covariates(index: int) -> dict:
    return {
        "Age": 72 + index,
        "EDUC": 16,
        "SES": None,
        "MMSE": None,
        "eTIV": 1450,
        "nWBV": 0.72,
        "ASF": 1.1,
        "MR Delay": index * 365,
        "Visit": index + 1,
        "M/F": "F",
        "Hand": "R",
    }


@pytest.fixture
def trained_stub(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_root", tmp_path / "storage")
    checkpoint = tmp_path / "synthetic-model.pt"
    checkpoint.write_bytes(b"synthetic backend checkpoint, not clinical weights")
    monkeypatch.setattr(settings, "trained_model_path", checkpoint)
    calls = []
    real_identity = trained_inference.checkpoint_identity
    real_run = trained_inference.run_trained_pipeline

    def identity(path: Path) -> str:
        return "synthetic-trained-" + hashlib.sha256(path.read_bytes()).hexdigest()[:12]

    def trained_run(
        patient_id, visits, output_dir, checkpoint_path, expected_version, subject_code, progress=None
    ):
        assert identity(checkpoint_path) == expected_version
        calls.append({"visits": visits, "subject_code": subject_code, "version": expected_version})
        prediction = TrainedPrediction(
            score=0.6,
            decision_threshold=0.514227,
            predicted_increase=True,
            checkpoint_sha256=hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
            cohort_role="train",
            training_subjects=40,
            training_visits=132,
            test_subjects=8,
            test_accuracy=0.25,
            test_balanced_accuracy=1 / 3,
            test_roc_auc=1 / 12,
            majority_baseline_accuracy=0.75,
        )
        return run_pipeline(
            patient_id,
            visits,
            output_dir,
            "trained",
            progress,
            predictor=lambda volumes: prediction,
            model_version=expected_version,
        )

    monkeypatch.setattr(trained_inference, "checkpoint_identity", identity)
    monkeypatch.setattr(trained_inference, "run_trained_pipeline", trained_run)

    def forbidden_baseline(*args, **kwargs):
        raise AssertionError("Worker must never fall back to the baseline for a trained request")

    monkeypatch.setattr(runner, "run_pipeline", forbidden_baseline)
    return {
        "path": checkpoint,
        "identity": identity,
        "calls": calls,
        "real_identity": real_identity,
        "real_run": real_run,
    }


@pytest.fixture
def trained_case(trained_stub, session_factory, mri):
    with session_factory() as db:
        patient = Patient(owner_id="researcher-a", code="SYNTHETIC_TRAIN", age=72, sex="Female")
        db.add(patient)
        db.flush()
        visits = []
        for index in range(3):
            key = f"raw/synthetic-{index}.nii.gz"
            path = resolve_key(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(mri.read_bytes())
            visit = Visit(
                patient_id=patient.id,
                label=f"Visit {index + 1}",
                days_from_baseline=index * 365,
                mri_key=key,
                metadata_json={
                    **source_covariates(index),
                    "CDR": 0.5,
                    "Group": "label-must-not-leak",
                    "Subject ID": "identifier-must-not-leak",
                    "MRI ID": f"source-{index}",
                },
            )
            db.add(visit)
            db.flush()
            visits.append(visit.id)
        db.commit()
        return {"patient_id": patient.id, "visit_ids": visits}


def enqueue_trained(client, case):
    return client.post(f"/analysis/{case['visit_ids'][-1]}", json={"outputMode": "trained"})


def test_configuration_and_legacy_default():
    assert Settings.model_fields["trained_model_path"].default == (
        ROOT / "data/training_multimodal/runs/20261001T134908Z/multimodal_model.pt"
    )
    assert AnalysisCreate().output_mode == "inference"
    assert AnalysisCreate(output_mode="trained").output_mode == "trained"


def test_health_advertises_readiness_without_paths(authenticated, trained_stub):
    response = authenticated.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["modelVersion"] == payload["baselineModelVersion"] == MODEL_VERSION
    assert payload["trainedModelReady"]
    assert payload["trainedModelVersion"] == trained_stub["identity"](trained_stub["path"])
    assert str(trained_stub["path"]) not in response.text
    trained_stub["path"].unlink()
    response = authenticated.get("/health")
    assert response.status_code == 200
    assert response.json()["trainedModelReady"] is False
    assert response.json()["trainedModelVersion"] is None
    assert response.json()["baselineModelVersion"] == MODEL_VERSION


def test_trained_snapshot_prediction_report_and_ownership(
    authenticated,
    trained_case,
    trained_stub,
    session_factory,
):
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 202, response.text
    payload = response.json()
    job_id = payload["id"]
    pinned = trained_stub["identity"](trained_stub["path"])
    assert payload["modelVersion"] == pinned and payload["outputMode"] == "trained"
    assert "inputJson" not in payload and "covariates" not in response.text
    assert enqueue_trained(authenticated, trained_case).status_code == 409
    with session_factory() as db:
        job = db.get(Analysis, job_id)
        snapshot = job.input_json
        assert [item["covariates"]["Age"] for item in snapshot] == [72, 73, 74]
        for item in snapshot:
            assert set(item["covariates"]) == set(COVARIATES)
            assert item["covariates"]["SES"] is None and item["covariates"]["MMSE"] is None
        assert "label-must-not-leak" not in str(snapshot)
        assert "identifier-must-not-leak" not in str(snapshot)
        # A later metadata edit cannot silently change the queued model inputs.
        last = db.get(Visit, trained_case["visit_ids"][-1])
        last.metadata_json = {**last.metadata_json, "Age": 99, "CDR": 3}
        db.commit()
    runner.execute(job_id)
    completed = authenticated.get(f"/analysis/{job_id}").json()
    assert completed["status"] == "completed", completed
    assert completed["score"] == 0.6 and completed["confidence"] is None
    assert completed["modelVersion"] == completed["resultJson"]["modelVersion"] == pinned
    result = completed["resultJson"]
    assert result["riskScores"] == [] and result["prediction"]["cohortRole"] == "train"
    assert result["prediction"]["decisionThreshold"] == 0.514227
    assert all(len(values) == 3 for values in result["biomarkers"].values())
    assert result["volumeOverlaysReady"]
    assert trained_stub["calls"][0]["subject_code"] == "SYNTHETIC_TRAIN"
    assert [visit.covariates["Age"] for visit in trained_stub["calls"][0]["visits"]] == [72, 73, 74]
    assert not resolve_key(cache_key(snapshot)).is_file()
    assert not resolve_key("cache").exists()
    last_id = trained_case["visit_ids"][-1]
    assert authenticated.get(f"/analysis/{job_id}/visits/{last_id}/overlay").status_code == 200
    assert authenticated.get(f"/analysis/{job_id}/visits/{last_id}/difference-volume").status_code == 200
    report = authenticated.post(f"/reports/{trained_case['patient_id']}")
    assert report.status_code == 201, report.text
    url = report.json()["downloadUrl"].removeprefix("/api")
    pdf = authenticated.get(url)
    text = " ".join(
        " ".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(pdf.content)).pages
    )
    for phrase in (
        "Not a medical diagnosis",
        "Trained",
        "POOR HELD-OUT PERFORMANCE",
        "retrospectively",
        "in-sample",
        "not accuracy evidence",
        "One uncalibrated sequence score: 0.600000",
        "threshold: 0.514227",
        "Classification: Observed CDR increase",
        "not a disease probability",
        "accuracy 25.0%",
        "baseline accuracy 75.0%",
        "Per-visit image-proxy metrics",
    ):
        assert phrase in text
    assert "Longitudinal progression-risk estimates" not in text
    assert "The index changed by" not in text
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get(f"/analysis/{job_id}").status_code == 404
    assert enqueue_trained(authenticated, trained_case).status_code == 404
    assert authenticated.get(f"/analysis/{job_id}/visits/{last_id}/overlay").status_code == 404
    assert authenticated.get(f"/analysis/{job_id}/visits/{last_id}/difference-volume").status_code == 404
    assert authenticated.post(f"/reports/{trained_case['patient_id']}").status_code == 404
    assert authenticated.get(url).status_code == 404


@pytest.mark.parametrize("key", COVARIATES)
def test_absent_source_fields_are_rejected_not_imputed(authenticated, trained_case, session_factory, key):
    with session_factory() as db:
        visit = db.get(Visit, trained_case["visit_ids"][1])
        visit.metadata_json = {name: value for name, value in visit.metadata_json.items() if name != key}
        db.commit()
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 422
    with session_factory() as db:
        assert db.scalar(select(Analysis)) is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("Age", True),
        ("Age", "73"),
        ("Age", None),
        ("Age", 121),
        ("MMSE", 31),
        ("SES", 0),
        ("SES", float("inf")),
        ("nWBV", -1),
        ("ASF", 0),
        ("eTIV", 0),
        ("EDUC", 2.5),
        ("MR Delay", 999),
        ("Visit", 1),
        ("Hand", None),
        ("Hand", "unknown"),
        ("M/F", "Female"),
    ],
)
def test_invalid_source_domains_are_safe_422(authenticated, trained_case, session_factory, key, value):
    with session_factory() as db:
        visit = db.get(Visit, trained_case["visit_ids"][1])
        visit.metadata_json = {**visit.metadata_json, key: value}
        db.commit()
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 422
    assert "Traceback" not in response.text and "mri_path" not in response.text


def test_insufficient_visits_and_mri_rejected(authenticated, trained_case, session_factory):
    response = authenticated.post(f"/analysis/{trained_case['visit_ids'][1]}", json={"outputMode": "trained"})
    assert response.status_code == 422
    with session_factory() as db:
        visit = db.get(Visit, trained_case["visit_ids"][0])
        visit.mri_key = None
        db.commit()
    assert enqueue_trained(authenticated, trained_case).status_code == 422


def test_missing_checkpoint_is_safe_503(authenticated, trained_case, trained_stub, session_factory):
    trained_stub["path"].unlink()
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 503 and "No baseline fallback" in response.text
    assert str(trained_stub["path"]) not in response.text
    with session_factory() as db:
        assert db.scalar(select(Analysis)) is None


def test_validator_dependency_failure_is_safe_503(authenticated, trained_case, monkeypatch):
    def unavailable(*args, **kwargs):
        raise RuntimeError(r"Dependency failed at C:\private\model-inputs")

    monkeypatch.setattr(trained_inference, "validate_covariates", unavailable)
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 503 and "No baseline fallback" in response.text
    assert "private" not in response.text


@pytest.mark.parametrize("failure", ["changed", "missing", "model-input"])
def test_worker_failure_is_explicit_and_never_falls_back(
    authenticated,
    trained_case,
    trained_stub,
    session_factory,
    monkeypatch,
    failure,
):
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 202
    job_id = response.json()["id"]
    pinned = response.json()["modelVersion"]
    if failure == "changed":
        trained_stub["path"].write_bytes(b"replacement checkpoint")
    elif failure == "missing":
        trained_stub["path"].unlink()
    else:

        def invalid_inputs(*args, **kwargs):
            raise ValueError(r"C:\private\participant\invalid.nii.gz")

        monkeypatch.setattr(trained_inference, "run_trained_pipeline", invalid_inputs)
    runner.execute(job_id)
    job = authenticated.get(f"/analysis/{job_id}").json()
    assert job["status"] == "failed" and job["modelVersion"] == pinned
    assert job["score"] is None and job["resultJson"] is None
    assert "No baseline fallback" in job["error"]
    assert "C:\\private" not in job["error"] and str(trained_stub["path"]) not in job["error"]
    assert trained_stub["calls"] == [] and not resolve_key("cache").exists()
    with session_factory() as db:
        assert db.scalar(select(Biomarker)) is None


def test_worker_rejects_wrong_result_version(authenticated, trained_case, monkeypatch, session_factory):
    response = enqueue_trained(authenticated, trained_case)
    job_id = response.json()["id"]
    original = trained_inference.run_trained_pipeline

    def wrong_version(**kwargs):
        return original(**kwargs).model_copy(update={"model_version": "wrong-checkpoint"})

    monkeypatch.setattr(trained_inference, "run_trained_pipeline", wrong_version)
    runner.execute(job_id)
    completed = authenticated.get(f"/analysis/{job_id}").json()
    assert completed["status"] == "failed" and completed["score"] is None
    assert completed["modelVersion"] == response.json()["modelVersion"]
    with session_factory() as db:
        assert db.scalar(select(Biomarker)) is None


def test_actual_saved_weight_integration(
    authenticated,
    trained_case,
    trained_stub,
    monkeypatch,
    trained_bundle_path,
    session_factory,
    mri,
):
    path = trained_bundle_path
    monkeypatch.setattr(get_settings(), "trained_model_path", path)
    monkeypatch.setattr(trained_inference, "checkpoint_identity", trained_stub["real_identity"])
    monkeypatch.setattr(trained_inference, "run_trained_pipeline", trained_stub["real_run"])
    with session_factory() as db:
        patient = db.get(Patient, trained_case["patient_id"])
        patient.code = "SYNTH_train_0"
        db.commit()
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    runner.execute(job_id)
    job = authenticated.get(f"/analysis/{job_id}").json()
    assert job["status"] == "completed", job
    assert job["modelVersion"] == trained_stub["real_identity"](path)
    prediction = job["resultJson"]["prediction"]
    expected = trained_inference.load_bundle(path, job["modelVersion"]).predict(
        [prepare(mri).volume] * 3,
        [source_covariates(i) for i in range(3)],
        "SYNTH_train_0",
    )
    assert job["score"] == prediction["score"] == pytest.approx(expected.score, abs=1e-7)
    assert prediction["decisionThreshold"] == expected.decision_threshold
    assert prediction["predictedIncrease"] == expected.predicted_increase
    assert prediction["cohortRole"] == "train"
    assert prediction["checkpointSha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert job["resultJson"]["riskScores"] == []
    assert not resolve_key("cache").exists()
    report = authenticated.post(f"/reports/{trained_case['patient_id']}")
    assert report.status_code == 201
    pdf = authenticated.get(report.json()["downloadUrl"].removeprefix("/api"))
    text = " ".join(" ".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(pdf.content)).pages)
    classification = "Observed CDR increase" if expected.predicted_increase else "No observed CDR increase"
    assert f"Classification: {classification}" in text


@pytest.mark.parametrize("filename", ["multimodal_model.pt", "metrics.json", "status.json", "subject_split.csv"])
def test_mutated_bundle_evidence_invalidates_queued_job(
    authenticated, trained_case, trained_stub, trained_bundle_path, monkeypatch, filename,
):
    monkeypatch.setattr(get_settings(), "trained_model_path", trained_bundle_path)
    monkeypatch.setattr(trained_inference, "checkpoint_identity", trained_stub["real_identity"])
    monkeypatch.setattr(trained_inference, "run_trained_pipeline", trained_stub["real_run"])
    response = enqueue_trained(authenticated, trained_case)
    assert response.status_code == 202
    changed = trained_bundle_path.parent / filename
    changed.write_bytes(changed.read_bytes() + b"\nchanged-after-enqueue")
    runner.execute(response.json()["id"])
    job = authenticated.get(f"/analysis/{response.json()['id']}").json()
    assert job["status"] == "failed" and job["modelVersion"] == response.json()["modelVersion"]
    assert "changed since enqueue" in job["error"] and "No baseline fallback" in job["error"]
    assert str(trained_bundle_path) not in job["error"] and job["resultJson"] is None
    assert not resolve_key("cache").exists()


@pytest.mark.parametrize("mode", ["inference", "demo", "precomputed"])
def test_legacy_worker_persists_returned_model_version(
    authenticated,
    trained_case,
    monkeypatch,
    session_factory,
    mode,
):
    def baseline_run(*args, **kwargs):
        return run_pipeline(*args, **kwargs, model_version="synthetic-legacy-v2")

    monkeypatch.setattr(runner, "run_pipeline", baseline_run)
    prepare_mode = "inference" if mode == "precomputed" else mode
    response = authenticated.post(
        f"/analysis/{trained_case['visit_ids'][-1]}",
        json={"outputMode": prepare_mode},
    )
    assert response.status_code == 202
    runner.execute(response.json()["id"])
    if mode == "precomputed":
        response = authenticated.post(
            f"/analysis/{trained_case['visit_ids'][-1]}",
            json={"outputMode": mode},
        )
        assert response.status_code == 202
        runner.execute(response.json()["id"])
    job = authenticated.get(f"/analysis/{response.json()['id']}").json()
    assert job["status"] == "completed", job
    assert job["modelVersion"] == job["resultJson"]["modelVersion"] == "synthetic-legacy-v2"
    assert len(job["resultJson"]["riskScores"]) == 3
    with session_factory() as db:
        assert all("covariates" not in item for item in db.get(Analysis, job["id"]).input_json)
