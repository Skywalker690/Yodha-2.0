"""Explicit candidate opt-in does not relax promoted serving or source ownership."""

from pathlib import Path
from types import SimpleNamespace

from backend.app.models import Analysis
from backend.app.services import anatomy_forecast as service
from ml.contracts import ProgressionResult
from tests.test_anatomy_api import anatomy_job as anatomy_job


def test_experimental_worker_leaves_native_queue_and_interruption_untouched(anatomy_job, session_factory, monkeypatch):
    from backend.app.workers import runner
    monkeypatch.setattr(runner, "SessionLocal", session_factory)
    with session_factory() as db:
        native = db.get(Analysis, "synthetic-anatomy")
        native.status, native.stage = "processing", "Native T1 segmentation"
        db.add(Analysis(id="experimental-job", patient_id=native.patient_id, visit_id=native.visit_id,
            status="queued", output_mode="anatomy", stage="Experimental forecast queued"))
        db.add(Analysis(id="native-job", patient_id=native.patient_id, visit_id=native.visit_id,
            status="queued", output_mode="anatomy", stage="Waiting for local worker"))
        db.commit()
    runner.recover_interrupted(experimental_only=True)
    assert runner.claim_next(experimental_only=True) == "experimental-job"
    assert runner.claim_next(experimental_only=True) is None
    with session_factory() as db:
        assert db.get(Analysis, "synthetic-anatomy").status == "processing"
        assert db.get(Analysis, "native-job").status == "queued"
    runner.recover_interrupted(experimental_only=True)
    with session_factory() as db:
        assert db.get(Analysis, "experimental-job").status == "failed"
        assert db.get(Analysis, "synthetic-anatomy").status == "processing"


def test_candidate_requires_explicit_readiness(monkeypatch, tmp_path):
    from ml.anatomy import experimental

    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: SimpleNamespace(
            anatomy_release_dir=tmp_path / "missing", anatomy_experimental_candidate_dir=tmp_path
        ),
    )
    monkeypatch.setattr(
        experimental,
        "candidate",
        lambda path: ({"counts": {"train": 4}, "release_failures": ["failed review"]}, "a" * 64),
    )
    assert service.readiness()["status"] == "unavailable"
    state = service.readiness(experimental=True)
    assert state["status"] == "available" and state["supportedIntervalsDays"] == []
    assert state["trainingSubjectCount"] == 4 and state["isResearchCandidate"]
    assert "failed review" in state["warnings"]


def test_candidate_change_is_unavailable(monkeypatch, tmp_path):
    from ml.anatomy import experimental

    monkeypatch.setattr(
        service, "get_settings", lambda: SimpleNamespace(anatomy_experimental_candidate_dir=tmp_path)
    )

    def changed(path):
        raise ValueError("Model changed after evaluation")

    monkeypatch.setattr(experimental, "candidate", changed)
    assert service.readiness(experimental=True)["status"] == "unavailable"


def test_opt_in_queues_unreviewed_inputs_without_approving_them(
    authenticated, anatomy_job, session_factory, monkeypatch
):
    from ml.anatomy.contracts import RatingEstimate

    with session_factory() as db:
        source = db.get(Analysis, "synthetic-anatomy")
        result = ProgressionResult.model_validate(source.result_json)
        for visit in result.anatomy.visits:
            visit.qc = "automated_checks_only"
            visit.ratings = RatingEstimate(
                status="unreviewed_research",
                method="AVRA-v0.8-ensemble-continuous",
                mta_left=1,
                mta_right=1,
                posterior_atrophy=1,
                provenance_sha256="d" * 64,
            )
        source.result_json = result.model_dump()
        db.commit()
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: SimpleNamespace(anatomy_experimental_candidate_dir=Path("frozen-candidate")),
    )
    monkeypatch.setattr(
        service,
        "readiness",
        lambda experimental=False: {
            "status": "available",
            "releaseSha256": "e" * 64,
            "intervalsDays": [365],
            "isResearchCandidate": experimental,
        },
    )
    endpoint = "/analysis/synthetic-anatomy/forecast"
    assert authenticated.post(endpoint, json={"intervalDays": 365}).status_code == 409
    assert (
        authenticated.post(
            endpoint, json={"intervalDays": 365, "experimental": True, "cutoffVisitId": "anatomy-v0"}
        ).status_code
        == 409
    )
    response = authenticated.post(endpoint, json={"intervalDays": 365, "experimental": True})
    assert response.status_code == 202, response.text
    with session_factory() as db:
        job = db.get(Analysis, response.json()["id"])
        assert job.stage == "Experimental forecast queued"
        assert job.input_json[-1]["forecast_spec"]["is_research_candidate"] is True
        original = db.get(Analysis, "synthetic-anatomy").result_json["anatomy"]["visits"]
        assert all(
            v["qc"] == "automated_checks_only" and v["ratings"]["status"] == "unreviewed_research"
            for v in original
        )
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.post(endpoint, json={"intervalDays": 365, "experimental": True}).status_code == 404
