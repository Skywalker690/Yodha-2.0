import hashlib

import numpy as np
import pandas as pd
import pytest
import torch

from ml.contracts import ProgressionResult, VisitInput
from ml.preprocessing import prepare
from ml.trained_inference import checkpoint_identity, load_bundle, run_trained_pipeline, validate_covariates
from scripts.import_oasis import create_training_manifest, import_manifest, source_covariates


def covariates(step: int) -> dict:
    return {
        "Age": 70 + step,
        "EDUC": 12,
        "SES": None,
        "MMSE": 28 - step,
        "eTIV": 1500,
        "nWBV": 0.75,
        "ASF": 1.1,
        "MR Delay": step * 365,
        "Visit": step + 1,
        "M/F": "F",
        "Hand": "R",
    }


def inputs(mri) -> list[VisitInput]:
    return [
        VisitInput(visit_id=f"v{i}", days_from_baseline=i * 365, mri_path=str(mri), covariates=covariates(i))
        for i in range(3)
    ]


def test_trained_pipeline_uses_checkpoint_and_saved_demographics(trained_bundle_path, mri, tmp_path):
    before = mri.read_bytes()
    version = checkpoint_identity(trained_bundle_path)
    bundle = load_bundle(trained_bundle_path, version)
    visits = inputs(mri)
    expected = bundle.predict([prepare(mri).volume] * 3, [v.covariates for v in visits], "SYNTH_train_20")
    result = run_trained_pipeline(
        "p", list(reversed(visits)), tmp_path / "trained", trained_bundle_path, version, "SYNTH_train_20"
    )
    assert result.prediction == expected
    assert result.prediction.cohort_role == "train"
    assert result.output_mode == "trained" and result.model_version == version
    assert result.risk_scores == [] and result.confidence is None
    assert result.prediction.training_subjects == 40 and result.prediction.training_visits == 132
    assert result.prediction.test_accuracy == 0.25
    assert result.visit_ids == ["v0", "v1", "v2"]
    assert len(result.biomarkers["feature_change"]) == 3
    assert result.volume_overlays_ready and len(list((tmp_path / "trained").glob("*-difference.nii.gz"))) == 3
    assert mri.read_bytes() == before
    assert "in-sample" in " ".join(result.caveats)
    assert "No 12/24/36-month" in " ".join(result.caveats)
    restored = ProgressionResult.model_validate_json(result.model_dump_json())
    assert restored == result


def test_predictions_use_saved_weights_not_feature_delta(trained_bundle_path, mri):
    bundle = load_bundle(trained_bundle_path)
    volumes = [prepare(mri).volume] * 3
    fields = [covariates(i) for i in range(3)]
    first = bundle.predict(volumes, fields, "unknown")
    assert first.cohort_role == "unassigned"
    with torch.no_grad():
        bundle.model.head.bias.add_(2)
    second = bundle.predict(volumes, fields, "unknown")
    assert second.score > first.score
    assert first.score > 0


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "label",
        "nonfinite",
        "wrong_date",
        "wrong_order",
        "invalid_category",
        "few_visits",
        "missing_age",
        "fractional_visit",
    ],
)
def test_bad_model_inputs_are_rejected(mri, kind):
    visits = inputs(mri)
    if kind == "missing":
        del visits[0].covariates["SES"]
    elif kind == "label":
        visits[0].covariates["CDR"] = 1
    elif kind == "nonfinite":
        visits[0].covariates["MMSE"] = float("inf")
    elif kind == "wrong_date":
        visits[0].covariates["MR Delay"] = 100
    elif kind == "wrong_order":
        visits.reverse()
    elif kind == "invalid_category":
        visits[0].covariates["Hand"] = "invented"
    elif kind == "few_visits":
        visits.pop()
    elif kind == "missing_age":
        visits[0].covariates["Age"] = None
    elif kind == "fractional_visit":
        visits[0].covariates["Visit"] = 1.5
    with pytest.raises(ValueError):
        validate_covariates(visits)


def test_explicit_missing_measurements_use_serialized_training_imputation(mri, trained_bundle_path):
    visits = inputs(mri)
    visits[0].covariates["MMSE"] = None
    validate_covariates(visits)
    bundle = load_bundle(trained_bundle_path)
    before = bundle.preprocessor.to_dict()
    prediction = bundle.predict([prepare(mri).volume] * 3, [v.covariates for v in visits], "unknown")
    assert np.isfinite(prediction.score)
    assert bundle.preprocessor.to_dict() == before


def test_model_bundle_mutation_and_missing_files_never_fall_back(trained_bundle_path):
    version = checkpoint_identity(trained_bundle_path)
    evidence = trained_bundle_path.parent / "metrics.json"
    original = evidence.read_text(encoding="utf-8")
    evidence.write_text(original + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after"):
        load_bundle(trained_bundle_path, version)
    evidence.unlink()
    with pytest.raises(ValueError, match="missing"):
        load_bundle(trained_bundle_path)


@pytest.mark.parametrize(
    "kind", ["scaler", "weights", "threshold", "split", "schema", "target", "training_ids"]
)
def test_incompatible_checkpoints_are_rejected(trained_bundle_path, kind):
    checkpoint = torch.load(trained_bundle_path, map_location="cpu", weights_only=True)
    if kind == "scaler":
        checkpoint["demographic_preprocessor"]["scales"][0] = 0
    elif kind == "weights":
        checkpoint["model_state_dict"]["head.bias"][0] = float("nan")
    elif kind == "threshold":
        checkpoint["decision_threshold"] = float("nan")
    elif kind == "split":
        checkpoint["split_sha256"] = "b" * 64
    elif kind == "schema":
        checkpoint["feature_names"].append("CDR")
    elif kind == "target":
        checkpoint["target"] = "future_alzheimer_probability"
    else:
        checkpoint["preprocessing_fit_subject_ids"].pop()
    torch.save(checkpoint, trained_bundle_path)
    with pytest.raises(ValueError):
        load_bundle(trained_bundle_path)


def test_trained_result_cannot_invent_a_trajectory(trained_bundle_path, mri, tmp_path):
    result = run_trained_pipeline(
        "p",
        inputs(mri),
        tmp_path / "out",
        trained_bundle_path,
        checkpoint_identity(trained_bundle_path),
        "unknown",
    )
    changed = result.model_dump()
    changed["risk_scores"] = [0.1, 0.2, 0.3]
    with pytest.raises(ValueError, match="fabricated trajectory"):
        ProgressionResult.model_validate(changed)
    changed = result.model_dump()
    changed["prediction"]["predicted_increase"] = not changed["prediction"]["predicted_increase"]
    with pytest.raises(ValueError, match="saved validation"):
        ProgressionResult.model_validate(changed)


def test_import_preserves_all_covariates_and_explicit_missingness():
    row = pd.Series(
        {**covariates(0), "CDR": 1, "Group": "Converted", "MRI ID": "private", "Subject ID": "private"}
    )
    result = source_covariates(row)
    assert len(result) == 11 and result["SES"] is None
    assert not {"CDR", "Group", "MRI ID", "Subject ID"} & set(result)
    del row["Hand"]
    with pytest.raises(ValueError, match="complete"):
        source_covariates(row)


def test_training_manifest_preserves_exact_membership_and_all_visits(
    trained_bundle_path, mri, tmp_path, monkeypatch
):
    from scripts import train_longitudinal_model
    from scripts.train_longitudinal_model import SubjectRecord

    manifest = pd.read_csv(trained_bundle_path.parent / "subject_split.csv")
    records = [
        SubjectRecord(
            code,
            tuple(
                (row["visit_id"], int(row["days_from_baseline"]), mri, float(row["cdr"]))
                for _, row in rows.sort_values("days_from_baseline").iterrows()
            ),
            int(rows.iloc[0]["target"]),
        )
        for code, rows in manifest.groupby("subject_id", sort=True)
    ]
    monkeypatch.setattr(train_longitudinal_model, "load_subjects", lambda metadata, root: records)
    workbook = tmp_path / "synthetic-source.csv"
    workbook.write_text("fully synthetic source fingerprint\n", encoding="utf-8")
    checkpoint = torch.load(trained_bundle_path, weights_only=True)
    checkpoint["metadata_sha256"] = hashlib.sha256(workbook.read_bytes()).hexdigest()
    torch.save(checkpoint, trained_bundle_path)
    output = tmp_path / "training-app.csv"
    create_training_manifest(workbook, tmp_path, trained_bundle_path, output)
    imported = pd.read_csv(output)
    expected = manifest[manifest["split"] == "train"]
    assert imported["patient_id"].nunique() == 40 and len(imported) == 132
    assert set(imported["patient_id"]) == set(expected["subject_id"])
    assert set(imported["visit_id"]) == set(expected["visit_id"])
    assert set(imported["split"]) == {"train"}
    before = output.read_bytes()
    workbook.write_text("changed source\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Workbook no longer matches"):
        create_training_manifest(workbook, tmp_path, trained_bundle_path, output)
    assert output.read_bytes() == before


def test_covariate_refresh_is_idempotent_and_preserves_existing_mri(
    session_factory, mri, tmp_path, monkeypatch
):
    from sqlalchemy import select

    from backend.app.core.config import get_settings
    from backend.app.models import Patient, Visit
    from backend.app.services.storage import resolve_key
    from scripts import import_oasis

    monkeypatch.setattr(get_settings(), "seed_email", "a@example.test")
    monkeypatch.setattr(import_oasis, "SessionLocal", session_factory)
    monkeypatch.setattr(import_oasis, "seed", lambda: None)
    rows = [
        {**covariates(i), "Subject ID": "SYNTH_IMPORT", "MRI ID": f"SYNTH_IMPORT_V{i}", "CDR": 0}
        for i in range(3)
    ]
    metadata = tmp_path / "metadata.csv"
    pd.DataFrame(rows).to_csv(metadata, index=False)
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {
                "patient_id": "SYNTH_IMPORT",
                "visit_id": row["MRI ID"],
                "visit_index": i,
                "days_from_baseline": i * 365,
                "mri_path": str(mri),
            }
            for i, row in enumerate(rows)
        ]
    ).to_csv(manifest, index=False)
    import_manifest(manifest, metadata, tmp_path)
    with session_factory() as db:
        patient = db.scalar(select(Patient).where(Patient.code == "SYNTH_IMPORT"))
        patient.notes = "Preserve these researcher notes"
        visits = list(
            db.scalars(
                select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.days_from_baseline)
            ).all()
        )
        originals = [(v.id, v.mri_key, resolve_key(v.mri_key).read_bytes()) for v in visits]
        # Simulate the previous importer, which omitted some training fields.
        for visit in visits:
            visit.metadata_json = {"CDR": 0, "nWBV": 0.75, "source": "OASIS-2 supplied demographics"}
        db.commit()
    import_manifest(manifest, metadata, tmp_path, refresh_covariates=True)
    import_manifest(manifest, metadata, tmp_path, refresh_covariates=True)
    with session_factory() as db:
        patient = db.scalar(select(Patient).where(Patient.code == "SYNTH_IMPORT"))
        assert patient.notes == "Preserve these researcher notes"
        visits = list(
            db.scalars(
                select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.days_from_baseline)
            ).all()
        )
        assert len(visits) == 3
        for visit, original in zip(visits, originals):
            assert visit.id == original[0] and visit.mri_key == original[1]
            assert resolve_key(visit.mri_key).read_bytes() == original[2]
            assert visit.metadata_json["SES"] is None
            assert set(covariates(0)).issubset(visit.metadata_json)
