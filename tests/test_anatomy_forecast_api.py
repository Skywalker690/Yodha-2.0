"""Synthetic review, async forecast, ownership and release-tamper integration."""

import json

from backend.app.models import Analysis
from backend.app.services.anatomy_forecast import result_hash
from backend.app.services.storage import resolve_key
from backend.app.workers import runner
from ml.anatomy.contracts import RatingEstimate
from ml.contracts import ProgressionResult
from src.common import sha256, write_json
from tests.test_anatomy_api import anatomy_job as anatomy_job


def prepare_ratings(client, directory, session_factory):
    for index in range(2):
        visit_id = f"anatomy-v{index}"
        assert (
            client.post(
                f"/analysis/synthetic-anatomy/anatomy-qc/{visit_id}", json={"visualReviewConfirmed": True}
            ).status_code
            == 200
        )
        rating = directory / f"rating_{index}"
        rating.mkdir(parents=True, exist_ok=True)
        for filename, value in (
            ("rating_mni_dof_6.nii", b"synthetic alignment"),
            ("rating_mni_dof_6.mat", b"synthetic transform"),
            ("rating.csv", b"mta_left_mean,mta_right_mean,pa_mean\n1.25,2.5,1.75\n"),
        ):
            (rating / filename).write_bytes(value)
        with session_factory() as db:
            job = db.get(Analysis, "synthetic-anatomy")
            result = ProgressionResult.model_validate(job.result_json)
            visit = result.anatomy.visits[index]
            provenance = {
                "source_sha256": visit.source_sha256,
                "method": "AVRA-v0.8-upstream",
                "runtime_digest": "sha256:" + "e" * 64,
                "weights_sha256": {"mta/model.pth.tar": "f" * 64},
                "alignment_qc": "pending_review",
                **{
                    key + "_sha256": sha256(rating / filename)
                    for key, filename in (
                        ("aligned", "rating_mni_dof_6.nii"),
                        ("matrix", "rating_mni_dof_6.mat"),
                        ("csv", "rating.csv"),
                    )
                },
            }
            write_json(rating / "provenance.json", provenance)
            visit.ratings = RatingEstimate(
                status="pending_alignment_qc", provenance_sha256=sha256(rating / "provenance.json")
            )
            job.result_json = result.model_dump()
            db.commit()


def test_alignment_review_unblocks_continuous_scores_and_binds_provenance(
    authenticated, anatomy_job, session_factory
):
    prepare_ratings(authenticated, anatomy_job, session_factory)
    base = "/analysis/synthetic-anatomy"
    assert authenticated.get(base + "/visits/anatomy-v0/rating-alignment").status_code == 200
    assert (
        authenticated.post(base + "/rating-qc/anatomy-v0", json={"visualReviewConfirmed": False}).status_code
        == 422
    )
    response = authenticated.post(base + "/rating-qc/anatomy-v0", json={"visualReviewConfirmed": True})
    assert response.status_code == 200, response.text
    scores = response.json()["resultJson"]["anatomy"]["visits"][0]["ratings"]
    assert scores["mtaLeft"] == 1.25 and scores["posteriorAtrophy"] == 1.75
    assert scores["reviewerId"] == "researcher-a" and scores["provenanceSha256"]
    assert scores["agreementValidated"] is False
    assert (
        authenticated.post(base + "/rating-qc/anatomy-v0", json={"visualReviewConfirmed": True}).status_code
        == 409
    )
    provenance = anatomy_job / "rating_1/provenance.json"
    original = json.loads(provenance.read_text())
    write_json(provenance, {**original, "source_sha256": "e" * 64})
    assert (
        authenticated.post(base + "/rating-qc/anatomy-v1", json={"visualReviewConfirmed": True}).status_code
        == 409
    )
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get(base + "/visits/anatomy-v0/rating-alignment").status_code == 404


def test_forecast_requires_release_review_and_freezes_cutoff_without_running_in_http(
    authenticated, anatomy_job, session_factory, monkeypatch
):
    import backend.app.services.anatomy_forecast as service

    base = "/analysis/synthetic-anatomy/forecast"
    assert authenticated.post(base, json={"intervalDays": 365}).status_code == 409
    prepare_ratings(authenticated, anatomy_job, session_factory)
    for index in range(2):
        assert (
            authenticated.post(
                f"/analysis/synthetic-anatomy/rating-qc/anatomy-v{index}",
                json={"visualReviewConfirmed": True},
            ).status_code
            == 200
        )
    monkeypatch.setattr(
        service,
        "readiness",
        lambda: {"status": "unavailable", "reason": "Synthetic release blocker", "intervalsDays": []},
    )
    assert authenticated.post(base, json={"intervalDays": 365}).status_code == 409
    monkeypatch.setattr(
        service,
        "readiness",
        lambda: {"status": "available", "releaseSha256": "e" * 64, "intervalsDays": [0, 365]},
    )
    assert authenticated.post(base, json={"intervalDays": 731}).status_code == 422
    assert (
        authenticated.post(base, json={"intervalDays": 365, "cutoffVisitId": "anatomy-v0"}).status_code == 409
    )
    assert authenticated.post(base, json={"intervalDays": 365, "cutoffVisitId": "unknown"}).status_code == 422
    # A later pending observation must not enter the selected earlier cutoff.
    with session_factory() as db:
        source = db.get(Analysis, "synthetic-anatomy")
        result = ProgressionResult.model_validate(source.result_json)
        later = result.anatomy.visits[-1].model_copy(
            update={"visit_id": "hidden-later", "days_from_baseline": 1200, "qc": "pending_review"}
        )
        result.anatomy.visits.append(later)
        result.anatomy.forecast.cutoff_visit_id = later.visit_id
        result.visit_ids.append(later.visit_id)
        result.days_from_baseline.append(1200)
        result.selected_visit = later.visit_id
        source.result_json = result.model_dump()
        source.input_json = [
            *source.input_json,
            {"visit_id": later.visit_id, "days_from_baseline": 1200, "mri_key": "raw/hidden.nii.gz"},
        ]
        # Fixture's original input snapshot needs actual chronology for worker validation.
        source.input_json = [
            {**item, "days_from_baseline": day, "source_sha256": visit.source_sha256}
            for item, day, visit in zip(source.input_json, result.days_from_baseline, result.anatomy.visits)
        ]
        expected_hash = result_hash(source.result_json)
        db.commit()
    response = authenticated.post(base, json={"intervalDays": 365, "cutoffVisitId": "anatomy-v1"})
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    assert "inputJson" not in response.json()
    with session_factory() as db:
        child = db.get(Analysis, response.json()["id"])
        assert len(child.input_json) == 2
        assert child.input_json[-1]["forecast_spec"]["source_result_sha256"] == expected_hash
        assert child.visit_id == "anatomy-v1"
        source = db.get(Analysis, "synthetic-anatomy")
        source.result_json = {**source.result_json, "caveats": ["source changed after enqueue"]}
        db.commit()
    # A changed reviewed source must fail before any expensive predictor runs.
    runner.execute(response.json()["id"])
    assert authenticated.get("/analysis/" + response.json()["id"]).json()["status"] == "failed"


def test_future_artifacts_never_fall_back_to_observed_mri(authenticated, anatomy_job):
    assert authenticated.get("/analysis/synthetic-anatomy/forecast-comparison").status_code == 404
    response = authenticated.get("/analysis/synthetic-anatomy/future/mri")
    assert response.status_code == 404
    assert authenticated.get("/patients/anatomy-patient/anatomy-forecasts").json() == []
    assert authenticated.get("/anatomy-model/readiness").json()["status"] == "unavailable"
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get("/patients/anatomy-patient/anatomy-forecasts").status_code == 404
    assert authenticated.get("/analysis/synthetic-anatomy/forecast-comparison").status_code == 404


def test_available_future_artifact_hashes_owner_isolation_and_report(
    authenticated, anatomy_job, session_factory
):
    import nibabel as nib
    import numpy as np
    from ml.anatomy.contracts import ForecastArtifact, StructuralForecast
    from ml.anatomy.model import VERSION as MODEL_VERSION
    from ml.anatomy.registration import nifti
    from ml.anatomy.spatial import mesh
    from pypdf import PdfReader
    from src.fastsurfer.regions import REGIONS

    prepare_ratings(authenticated, anatomy_job, session_factory)
    for index in range(2):
        assert (
            authenticated.post(
                f"/analysis/synthetic-anatomy/rating-qc/anatomy-v{index}",
                json={"visualReviewConfirmed": True},
            ).status_code
            == 200
        )
    root = anatomy_job / "future"
    root.mkdir(exist_ok=True)
    image = nifti(np.random.default_rng(42).random((24,) * 3).astype(np.float32), np.eye(4))
    nib.save(image, root / "mri.nii.gz")
    nib.save(nifti(np.zeros((24,) * 3, np.int16), np.eye(4)), root / "labels.nii.gz")
    nib.save(nifti(np.zeros((24, 24, 24, 3), np.float32), np.eye(4)), root / "pull.nii.gz")
    brain = np.zeros((24,) * 3, np.uint8)
    brain[4:20, 4:20, 4:20] = 1
    mesh(nifti(brain, np.eye(4)), root / "brain_mesh.gii")
    entries = {
        name: {"relative_path": name + suffix, "sha256": sha256(root / (name + suffix)), "kind": kind}
        for name, suffix, kind in (
            ("mri", ".nii.gz", "mri"),
            ("labels", ".nii.gz", "labels"),
            ("pull", ".nii.gz", "field"),
            ("brain_mesh", ".gii", "mesh"),
        )
    }
    with session_factory() as db:
        job = db.get(Analysis, "synthetic-anatomy")
        result = ProgressionResult.model_validate(job.result_json)
        result.anatomy.forecast = StructuralForecast(
            status="available",
            cutoff_visit_id="anatomy-v1",
            interval_days=365,
            warnings=["Synthetic integration fixture, never patient inference."],
            volumes_mm3={name: 3700.0 for name in REGIONS},
            prediction_intervals={name: (3500.0, 3900.0) for name in REGIONS},
            interval_evidence={
                "evaluated": True,
                "method": "synthetic coverage fixture",
                "level": 0.8,
                "subjects": 8,
            },
            spatial_model_version=MODEL_VERSION,
            model_sha256="a" * 64,
            release_sha256="e" * 64,
            artifacts=[
                ForecastArtifact(name=name, kind=entry["kind"], sha256=entry["sha256"])
                for name, entry in entries.items()
            ],
        )
        job.result_json = result.model_dump()
        db.commit()
        write_json(
            root / "future-artifacts.json",
            {
                "version": MODEL_VERSION,
                "cutoff_visit_id": "anatomy-v1",
                "interval_days": 365,
                "model_sha256": "a" * 64,
                "release_sha256": "e" * 64,
                "source_sha256": [v.source_sha256 for v in result.anatomy.visits],
                "artifacts": entries,
            },
        )
    response = authenticated.get("/analysis/synthetic-anatomy/future/mri")
    assert response.status_code == 200 and "no-store" in response.headers["cache-control"]
    assert response.content == (root / "mri.nii.gz").read_bytes()
    assert authenticated.get("/analysis/synthetic-anatomy/future/brain_mesh").status_code == 200
    assert authenticated.get("/analysis/synthetic-anatomy/future/not-present").status_code == 404
    assert len(authenticated.get("/patients/anatomy-patient/anatomy-forecasts").json()) == 1
    report = authenticated.post("/reports/anatomy-patient?analysis_id=synthetic-anatomy")
    assert report.status_code == 201
    content = "\n".join(
        p.extract_text() for p in PdfReader(resolve_key(f"reports/{report.json()['id']}.pdf")).pages
    )
    assert (
        "Predicted anatomy - available" in content
        and "synthetic coverage fixture" in content
        and "brain_mesh" in content
    )
    (root / "mri.nii.gz").write_bytes(b"tampered")
    assert authenticated.get("/analysis/synthetic-anatomy/future/mri").status_code == 404
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get("/analysis/synthetic-anatomy/future/brain_mesh").status_code == 404
