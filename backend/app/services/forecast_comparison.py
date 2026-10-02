"""Describe actual saved image/deformation changes without modifying the forecast."""

from pathlib import Path

import nibabel as nib
import numpy as np

from ml.anatomy.study import physical_source
from src.fastsurfer.regions import REGIONS


def compare(
    source_path: Path,
    observed_labels_path: Path,
    predicted_path: Path,
    predicted_labels_path: Path,
    field_path: Path,
    observed_volumes: dict[str, float],
    predicted_volumes: dict[str, float],
    *,
    verified_units: bool,
) -> dict:
    source = physical_source(source_path, verified_units=verified_units)
    images = [
        nib.load(path) for path in (observed_labels_path, predicted_path, predicted_labels_path, field_path)
    ]
    if np.prod(source.shape) > 32_000_000 or len(source.shape) != 3:
        raise ValueError("Bounded three-dimensional input MRI required")
    for index, image in enumerate(images):
        expected_shape = (*source.shape, 3) if index == 3 else source.shape
        if (
            image.shape != expected_shape
            or not np.allclose(image.affine, source.affine)
            or image.header.get_xyzt_units()[0] != "mm"
        ):
            raise ValueError("Comparison requires the exact cutoff grid and millimetre units")
    labels, prediction, future_labels, field = [np.asarray(i.dataobj) for i in images]
    original = np.asarray(source.dataobj, dtype=np.float32)
    if not all(np.isfinite(a).all() for a in (original, labels, prediction, future_labels, field)):
        raise ValueError("Nonfinite forecast comparison input")
    if (
        not np.equal(labels, np.rint(labels)).all()
        or not np.equal(future_labels, np.rint(future_labels)).all()
    ):
        raise ValueError("Categorical comparison labels required")
    brain = labels > 0
    if not brain.any():
        raise ValueError("Nonempty cutoff brain mask required")
    displacement = np.linalg.norm(field[brain], axis=-1)
    delta = np.abs(prediction[brain].astype(np.float32) - original[brain])
    input_mean = float(np.mean(np.abs(original[brain])))
    voxel_volume = abs(float(np.linalg.det(source.affine[:3, :3])))
    regions = []
    for region in ("hippocampus_left_mm3", "hippocampus_right_mm3"):
        identifier = REGIONS[region][0]
        observed_mask = float(np.count_nonzero(labels == identifier) * voxel_volume)
        predicted_mask = float(np.count_nonzero(future_labels == identifier) * voxel_volume)
        observed_scalar, predicted_scalar = observed_volumes[region], predicted_volumes[region]
        if min(observed_mask, predicted_mask, observed_scalar, predicted_scalar) <= 0:
            raise ValueError("Positive regional volumes required")
        regions.append(
            {
                "region": region,
                "observed_mask_mm3": observed_mask,
                "predicted_mask_mm3": predicted_mask,
                "mask_change_percent": 100 * (predicted_mask / observed_mask - 1),
                "observed_scalar_mm3": observed_scalar,
                "predicted_scalar_mm3": predicted_scalar,
                "scalar_change_percent": 100 * (predicted_scalar / observed_scalar - 1),
            }
        )
    return {
        "deformation": {
            "median_mm": float(np.median(displacement)),
            "p95_mm": float(np.percentile(displacement, 95)),
            "maximum_mm": float(displacement.max()),
        },
        "intensity": {
            "mean_absolute_change": float(delta.mean()),
            "relative_mean_absolute_change_percent": 100 * float(delta.mean()) / input_mean
            if input_mean > 0
            else None,
        },
        "regions": regions,
        "interpretation": "Image interpolation changes and scalar forecasts are separate estimates. They do not establish measured future atrophy or accuracy.",
    }
