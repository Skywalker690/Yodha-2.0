from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from ml.contracts import ProgressionResult, VisitInput
from ml.data import read_manifest
from ml.encoder import SpatialEncoder
from ml.inference import run_pipeline
from ml.preprocessing import load_validated, normalize, prepare
from ml.temporal_model import TemporalModel, feature_delta_scores


def test_preprocessing_shape_range_and_source_unchanged(mri):
    before = mri.read_bytes()
    processed = prepare(mri)
    assert processed.volume.shape == (64, 64, 64)
    assert np.isfinite(processed.volume).all()
    assert 0 <= processed.volume.min() <= processed.volume.max() <= 1
    assert mri.read_bytes() == before


@pytest.mark.parametrize("flipped", [False, True])
def test_resized_affine_preserves_canonical_field_of_view(tmp_path, flipped):
    data = np.random.default_rng(42).random((16, 24, 32)).astype(np.float32)
    affine = np.array([[0, -2, 0, 48], [3, 0, 0, -24], [0, 0, 1.5, -12], [0, 0, 0, 1.]])
    if flipped:
        affine[2, 2] *= -1
    path = tmp_path / "geometry.nii.gz"
    source = nib.Nifti1Image(data, affine)
    nib.save(source, path)
    canonical = nib.as_closest_canonical(source)
    prepared = prepare(path)
    for fraction in [0, 0.5, 1]:
        native = np.append(np.array(canonical.shape) * fraction - 0.5, 1)
        resized = np.append(np.array([64, 64, 64]) * fraction - 0.5, 1)
        assert prepared.affine @ resized == pytest.approx(canonical.affine @ native)
    assert nib.aff2axcodes(prepared.affine) == ("R", "A", "S")


def test_old_result_does_not_claim_volumetric_artifacts():
    result = ProgressionResult(
        patient_id="p", visit_ids=["v"], selected_visit="v", risk_scores=[0],
        biomarkers={}, days_from_baseline=[0], output_mode="precomputed", caveats=[],
    )
    assert not result.volume_overlays_ready


def test_invalid_missing_nonfinite_and_four_dimensional(tmp_path):
    with pytest.raises(ValueError, match="missing"):
        load_validated(tmp_path / "absent.nii")
    bad = tmp_path / "bad.nii"
    bad.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        load_validated(bad)
    data = np.random.default_rng(42).random((16, 16, 16)).astype(np.float32)
    data[2, 2, 2] = np.nan
    nib.save(nib.Nifti1Image(data, np.eye(4)), bad)
    with pytest.raises(ValueError, match="non-finite"):
        load_validated(bad)
    nib.save(nib.Nifti1Image(np.ones((16, 16, 16, 2), dtype=np.float32), np.eye(4)), bad)
    with pytest.raises(ValueError, match="3D"):
        load_validated(bad)


def test_scores_baseline_identical_and_change():
    scores, changes = feature_delta_scores(np.array([[0.2, 0.3], [0.2, 0.3], [0.4, 0.5], [5, 5]]))
    assert scores[0] == scores[1] == changes[0] == 0
    assert 0 < scores[2] <= 1 and scores[3] == 1


def test_chronology_determinism_provenance_and_artifacts(mri, tmp_path):
    visits = [
        VisitInput(visit_id="v2", days_from_baseline=600, mri_path=str(mri)),
        VisitInput(visit_id="v0", days_from_baseline=0, mri_path=str(mri)),
        VisitInput(visit_id="v1", days_from_baseline=300, mri_path=str(mri)),
    ]
    result = run_pipeline("p", visits, tmp_path / "one", "demo")
    repeated = run_pipeline("p", visits, tmp_path / "two", "demo")
    assert result == repeated
    assert result.visit_ids == ["v0", "v1", "v2"]
    assert result.risk_scores == pytest.approx([0.22, 0.445, 0.67])
    assert result.confidence is None
    assert len(list((tmp_path / "one").glob("*.png"))) == 6
    assert result.volume_overlays_ready
    for index in range(3):
        image = nib.load(tmp_path / "one" / f"{index}-difference.nii.gz")
        assert image.shape == (64, 64, 64)
        assert np.isfinite(image.get_fdata()).all()
        assert np.count_nonzero(image.get_fdata()) == 0
        assert image.affine == pytest.approx(prepare(mri).affine)
        assert b"not registered" in image.header["descrip"].tobytes()
    inference = run_pipeline("p", visits, tmp_path / "three")
    assert inference.risk_scores == [0, 0, 0]
    assert inference.output_mode == "inference"
    assert all(0 <= x <= 1 for x in inference.biomarkers["foreground_fraction"])


def test_result_rejects_misalignment_and_nonfinite():
    with pytest.raises(ValueError):
        ProgressionResult(
            patient_id="p",
            visit_ids=["v"],
            selected_visit="v",
            risk_scores=[float("nan")],
            biomarkers={},
            days_from_baseline=[0],
            output_mode="inference",
            caveats=[],
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"biomarkers": {"foreground_fraction": [float("inf")]}},
        {"biomarkers": {"foreground_fraction": [0.2, 0.3]}},
        {"confidence": 1.1},
        {"days_from_baseline": [-1]},
    ],
)
def test_result_rejects_invalid_biomarkers_confidence_and_days(changes):
    values = dict(
        patient_id="p",
        visit_ids=["v"],
        selected_visit="v",
        risk_scores=[0.1],
        biomarkers={"foreground_fraction": [0.2]},
        days_from_baseline=[0],
        output_mode="inference",
        caveats=[],
    )
    with pytest.raises(ValueError):
        ProgressionResult(**(values | changes))


def test_subject_level_manifest_split_and_order(tmp_path: Path):
    data = [
        {
            "patient_id": "p",
            "visit_id": "v2",
            "visit_index": 1,
            "days_from_baseline": 100,
            "mri_path": "a",
            "split": "train",
        },
        {
            "patient_id": "p",
            "visit_id": "v1",
            "visit_index": 0,
            "days_from_baseline": 0,
            "mri_path": "b",
            "split": "train",
        },
    ]
    path = tmp_path / "m.csv"
    pd.DataFrame(data).to_csv(path, index=False)
    assert read_manifest(path).visit_id.tolist() == ["v1", "v2"]
    data[1]["split"] = "test"
    pd.DataFrame(data).to_csv(path, index=False)
    with pytest.raises(ValueError, match="leakage"):
        read_manifest(path)


def test_normalization_constant_rejected():
    with pytest.raises(ValueError, match="intensity"):
        normalize(np.ones((8, 8, 8)))


def test_trainable_interfaces_tensor_shapes():
    import torch

    encoder, temporal = SpatialEncoder(), TemporalModel()
    encoded = encoder(torch.ones(3, 1, 16, 16, 16))
    assert encoded.shape == (3, 32)
    assert temporal(encoded[None]).shape == (1, 3)
