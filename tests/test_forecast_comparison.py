"""Saved image comparison is descriptive, without refitting or visual exaggeration."""

import nibabel as nib
import numpy as np
import pytest

from backend.app.services.forecast_comparison import compare
from src.fastsurfer.regions import REGIONS


@pytest.fixture
def comparison_inputs(tmp_path):
    labels = np.zeros((8, 8, 8), dtype=np.int16)
    labels[2:4, 2:4, 2:4] = REGIONS["hippocampus_left_mm3"][0]
    labels[4:6, 4:6, 4:6] = REGIONS["hippocampus_right_mm3"][0]
    arrays = [
        np.full(labels.shape, 100, dtype=np.float32),
        labels,
        np.full(labels.shape, 99, dtype=np.float32),
        labels,
        np.zeros((*labels.shape, 3), dtype=np.float32),
    ]
    paths = []
    for index, array in enumerate(arrays):
        image = nib.Nifti1Image(array, np.eye(4))
        image.header.set_xyzt_units("mm")
        path = tmp_path / f"{index}.nii.gz"
        nib.save(image, path)
        paths.append(path)
    return paths


def evaluate(paths):
    observed = {k: 100.0 for k in REGIONS}
    predicted = {k: 90.0 for k in REGIONS}
    return compare(*paths, observed, predicted, verified_units=True)


def test_mask_and_scalar_changes_stay_separate(comparison_inputs):
    result = evaluate(comparison_inputs)
    assert result["deformation"]["median_mm"] == 0
    assert result["intensity"]["relative_mean_absolute_change_percent"] == 1
    assert all(r["mask_change_percent"] == 0 for r in result["regions"])
    assert all(r["scalar_change_percent"] == pytest.approx(-10) for r in result["regions"])
    assert all(r["observed_mask_mm3"] == 8 for r in result["regions"])


def test_deformation_is_measured_in_millimetres(comparison_inputs):
    path = comparison_inputs[-1]
    field = nib.load(path)
    values = field.get_fdata(dtype=np.float32)
    values[..., 0] = 0.25
    image = nib.Nifti1Image(values, field.affine, field.header)
    nib.save(image, path)
    assert evaluate(comparison_inputs)["deformation"]["p95_mm"] == 0.25


def test_changed_grid_is_rejected(comparison_inputs):
    path = comparison_inputs[2]
    image = nib.load(path)
    affine = image.affine.copy()
    affine[0, 3] = 1
    nib.save(nib.Nifti1Image(image.get_fdata(), affine, image.header), path)
    with pytest.raises(ValueError, match="exact cutoff grid"):
        evaluate(comparison_inputs)


def test_nonfinite_prediction_is_rejected(comparison_inputs):
    path = comparison_inputs[2]
    image = nib.load(path)
    array = image.get_fdata()
    array[0, 0, 0] = np.nan
    nib.save(nib.Nifti1Image(array, image.affine, image.header), path)
    with pytest.raises(ValueError, match="Nonfinite"):
        evaluate(comparison_inputs)
