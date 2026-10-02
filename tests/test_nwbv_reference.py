"""Source provenance, optional descriptive results, and real worker persistence."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from backend.app.models import Analysis, Biomarker, Patient
from backend.app.services.nwbv_reference import attach, evaluate, OASIS_SOURCE_METHOD
from backend.app.workers import runner
from ml.anatomy.contracts import AnatomyResult, StructuralForecast
from ml.contracts import ProgressionResult
from ml.nwbv_contract import NWBV_REFERENCE_KEY, NwbvAgeReferenceBiomarker
from tests.test_anatomy import measured


def anatomy_result() -> ProgressionResult:
    visits = [measured(0), measured(365)]
    return ProgressionResult(
        patient_id="nwbv-case",
        visit_ids=[v.visit_id for v in visits],
        risk_scores=[],
        biomarkers={},
        selected_visit=visits[-1].visit_id,
        output_mode="anatomy",
        caveats=[],
        model_version="longitudinal-anatomy-v1",
        days_from_baseline=[0, 365],
        anatomy=AnatomyResult(
            visits=visits,
            changes=[],
            forecast=StructuralForecast(
                cutoff_visit_id=visits[-1].visit_id,
                interval_days=365,
                warnings=[],
            ),
        ),
    )


@pytest.mark.parametrize(
    "age,nwbv,method,status",
    [
        (73.0, 0.690, OASIS_SOURCE_METHOD, "ok"),
        (60, 0.7, OASIS_SOURCE_METHOD, "insufficient_reference"),
        (95, 0.7, OASIS_SOURCE_METHOD, "unsupported_age"),
        (73, 0.7, "fastsurfer_brain_over_etiv", "method_mismatch"),
        (73, None, OASIS_SOURCE_METHOD, "missing_input"),
        ("73", 0.7, OASIS_SOURCE_METHOD, "invalid_input"),
        (73.5, 0.7, OASIS_SOURCE_METHOD, "invalid_input"),
        (True, 0.7, OASIS_SOURCE_METHOD, "invalid_input"),
        (73, float("nan"), OASIS_SOURCE_METHOD, "invalid_input"),
        (73, 69, OASIS_SOURCE_METHOD, "invalid_input"),
        (10**400, 0.7, OASIS_SOURCE_METHOD, "invalid_input"),
    ],
)
def test_reference_accepts_source_fractions_and_preserves_unsupported_states(age, nwbv, method, status):
    result = evaluate("recorded-visit", {"age": age, "nwbv": nwbv, "measurement_method": method})
    assert result.status == status
    assert result.clinical_risk is None and result.feature_use_allowed is False
    assert result.intended_use == "support_value"
    json.dumps(result.model_dump(), allow_nan=False)
    if status == "ok":
        assert result.z_score == pytest.approx(-1.6662646038670732)
        assert result.reference_bin.n == 16
        assert result.reference_profile_id == "oasis2_baseline_cdr0_nwbv_v1"
    else:
        assert result.z_score is None


def test_optional_reference_is_bound_to_cutoff_and_does_not_change_predictions():
    result = anatomy_result()
    original = result.model_dump()
    inputs = [
        {
            "visit_id": v,
            "nwbv_reference_input": {
                "age": age,
                "nwbv": 0.69,
                "measurement_method": OASIS_SOURCE_METHOD,
            },
        }
        for v, age in zip(result.visit_ids, (72, 73))
    ]
    inputs.append(
        {
            "visit_id": "hidden-future",
            "nwbv_reference_input": {
                "age": 94,
                "nwbv": 0.1,
                "measurement_method": OASIS_SOURCE_METHOD,
            },
        }
    )
    before = deepcopy(inputs)
    enriched = attach(result, inputs)
    biomarker = enriched.biomarkers[NWBV_REFERENCE_KEY]
    assert biomarker.age_years == 73 and biomarker.visit_id == result.selected_visit
    assert inputs == before
    payload = enriched.model_dump()
    payload["biomarkers"] = {}
    assert payload == original
    with pytest.raises(ValidationError, match="selected observed visit"):
        ProgressionResult.model_validate({**enriched.model_dump(), "selected_visit": result.visit_ids[0]})
    assert (
        NWBV_REFERENCE_KEY
        not in attach(anatomy_result(), [{"visit_id": v} for v in result.visit_ids]).biomarkers
    )


def test_reference_failure_is_explicit_and_does_not_fail_anatomy(monkeypatch):
    from backend.app.services import nwbv_reference

    def unavailable():
        raise ImportError("package unavailable in this test")

    monkeypatch.setattr(nwbv_reference, "reference", unavailable)
    reference = evaluate("visit", {"age": 73, "nwbv": 0.69, "measurement_method": OASIS_SOURCE_METHOD})
    assert reference.status == "unavailable" and reference.z_score is None and reference.reason
    with pytest.raises(ValidationError):
        NwbvAgeReferenceBiomarker.model_validate({**reference.model_dump(), "clinical_risk": 0.5})


def test_enqueue_freezes_reference_inputs_separately_from_features(session_factory, monkeypatch, mri):
    from backend.app.models import Visit
    from backend.app.services import analysis

    monkeypatch.setattr(analysis, "resolve_key", lambda _: mri)
    with session_factory() as db:
        patient = Patient(id="frozen", owner_id="researcher-a", code="FROZEN_REFERENCE", source="oasis-2")
        db.add(patient)
        db.flush()
        visit = Visit(
            id="frozen-v0",
            patient_id=patient.id,
            label="Baseline",
            days_from_baseline=0,
            mri_key="raw/frozen.nii.gz",
            metadata_json={"Age": 73.0, "nWBV": 0.69},
        )
        db.add(visit)
        db.flush()
        job = analysis.enqueue(db, patient, visit, "anatomy")
        db.commit()
        visit.metadata_json = {"Age": 80, "nWBV": 0.1}
        db.commit()
        frozen = job.input_json[0]["nwbv_reference_input"]
        assert frozen == {"age": 73.0, "nwbv": 0.69, "measurement_method": OASIS_SOURCE_METHOD}
        assert "z_score" not in str(job.input_json)
        assert "nwbv_age_reference_v1" not in analysis.COVARIATES
        assert evaluate(visit.id, frozen).age_years == 73


def test_earlier_forecast_clears_later_reference_before_worker_recomputes(
    authenticated,
    session_factory,
    monkeypatch,
    tmp_path,
):
    from backend.app.services import anatomy_forecast as service
    from ml.anatomy import forecasting
    from ml.anatomy.contracts import RatingEstimate

    result = anatomy_result()
    later = result.anatomy.visits[-1].model_copy(update={"visit_id": "future", "days_from_baseline": 730})
    result.anatomy.visits.append(later)
    result.visit_ids.append(later.visit_id)
    result.days_from_baseline.append(730)
    result.selected_visit = later.visit_id
    result.anatomy.forecast.cutoff_visit_id = later.visit_id
    result.biomarkers[NWBV_REFERENCE_KEY] = evaluate(
        later.visit_id,
        {"age": 80, "nwbv": 0.69, "measurement_method": OASIS_SOURCE_METHOD},
    )
    root = tmp_path / "source"
    root.mkdir()
    (root / "anatomy-artifacts.json").write_text("{}")
    snapshots = []
    for index, visit in enumerate(result.anatomy.visits):
        visit.qc = "passed"
        visit.ratings = RatingEstimate(status="ok", mta_left=1, mta_right=1, posterior_atrophy=1)
        snapshots.append({"visit_id": visit.visit_id, "mri_key": f"raw/{index}.nii.gz"})
        if index == 2:
            continue
        for name in (
            f"fastsurfer/scan_{index}/processing.json",
            f"fastsurfer/scan_{index}/stats/aseg+DKT.VINN.stats",
            f"fastsurfer/scan_{index}/mri/aparc.DKTatlas+aseg.deep.mgz",
            *[
                f"rating_{index}/{n}"
                for n in (
                    "rating.csv",
                    "rating_mni_dof_6.nii",
                    "rating_mni_dof_6.mat",
                    "provenance.json",
                )
            ],
        ):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic fixture")
    monkeypatch.setattr(
        service, "measurement_files", lambda *args: {"segmentation": root / "anatomy-artifacts.json"}
    )
    monkeypatch.setattr(service, "rating_files", lambda *args, **kwargs: {})
    seen = []

    def predict(*args):
        seen.extend(v.visit_id for v in args[2])
        return StructuralForecast(cutoff_visit_id=args[2][-1].visit_id, interval_days=365, warnings=[])

    monkeypatch.setattr(forecasting, "predict", predict)
    cutoff = result.visit_ids[1]
    forecast = service.execute_forecast(
        result.model_dump(), snapshots, root, tmp_path / "child", "subject", 365, "pin", cutoff
    )
    assert seen == result.visit_ids[:2]
    assert forecast.selected_visit == cutoff and NWBV_REFERENCE_KEY not in forecast.biomarkers
    assert result.biomarkers[NWBV_REFERENCE_KEY].visit_id == "future"


def test_worker_persists_optional_reference_and_exposes_owned_result(
    session_factory,
    monkeypatch,
    authenticated,
):
    from backend.app.models import Visit
    from ml.anatomy import pipeline

    result = anatomy_result()
    inputs = [
        {
            "visit_id": visit.visit_id,
            "days_from_baseline": visit.days_from_baseline,
            "mri_key": f"raw/nwbv-{index}.nii.gz",
            "source_sha256": visit.source_sha256,
            "future_interval_days": 365,
            "source_units_verified": True,
            "etiv_unit": "cm3",
            "metadata": {"Age": 72.0 + index, "nWBV": 0.690},
        }
        for index, visit in enumerate(result.anatomy.visits)
    ]
    with session_factory() as db:
        db.add(Patient(id=result.patient_id, owner_id="researcher-a", code="NWBV_SOURCE", source="oasis-2"))
        db.flush()
        for item in inputs:
            db.add(
                Visit(
                    id=item["visit_id"],
                    patient_id=result.patient_id,
                    label=item["visit_id"],
                    days_from_baseline=item["days_from_baseline"],
                    mri_key=item["mri_key"],
                )
            )
        db.flush()
        db.add(
            Analysis(
                id="nwbv-analysis",
                patient_id=result.patient_id,
                visit_id=result.selected_visit,
                input_json=inputs,
                output_mode="anatomy",
                model_version=result.model_version,
            )
        )
        db.commit()
    observed = []

    def run(*args, **kwargs):
        observed.append(args[1])
        return result

    monkeypatch.setattr(pipeline, "run_anatomy", run)
    runner.execute("nwbv-analysis")
    assert "nwbv_age_reference_v1" not in str(observed)
    with session_factory() as db:
        job = db.get(Analysis, "nwbv-analysis")
        assert job.status == "completed" and job.score is None
        value = job.result_json["biomarkers"][NWBV_REFERENCE_KEY]
        row = db.scalar(select(Biomarker).where(Biomarker.analysis_id == job.id))
        assert row.name == NWBV_REFERENCE_KEY and row.values_json == value
        assert row.unit == "descriptive_reference" and value["z_score"] == pytest.approx(-1.6662646038670732)
    response = authenticated.get("/analysis/nwbv-analysis")
    assert response.status_code == 200
    assert response.json()["resultJson"]["biomarkers"]["nwbvAgeReferenceV1"]["clinicalRisk"] is None
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get("/analysis/nwbv-analysis").status_code == 404
