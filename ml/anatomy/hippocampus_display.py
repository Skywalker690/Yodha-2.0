"""Local scalar-guided illustration; not an evaluated spatial MRI prediction."""

import nibabel as nib
import numpy as np
from scipy.ndimage import distance_transform_edt, map_coordinates

from ml.anatomy.spatial import jacobians

REGIONS = {"hippocampus_left_mm3": 17, "hippocampus_right_mm3": 53}
VERSION = "hippocampus-scalar-illustration-v1"


def _image(data: np.ndarray, affine: np.ndarray) -> nib.Nifti1Image:
    image = nib.Nifti1Image(data, affine)
    image.header.set_xyzt_units("mm")
    return image


def hippocampus_display(
    source: nib.Nifti1Image,
    labels: nib.Nifti1Image,
    observed_volumes: dict[str, float],
    scalar_volumes: dict[str, float],
) -> tuple[nib.Nifti1Image, nib.Nifti1Image, nib.Nifti1Image, dict]:
    """Local contraction/expansion based on scalar ratios; skull is unchanged.

    Categorical volumes are fitted on the native grid, rather than silently using
    scalar partial-volume values as voxel-mask volumes. The presentation mapping
    has no independent forecast validation and is reported separately.
    """
    if source.shape != labels.shape or not np.allclose(source.affine, labels.affine):
        raise ValueError("Exact acquired MRI/label grid required")
    if source.header.get_xyzt_units()[0] != "mm" or labels.header.get_xyzt_units()[0] != "mm":
        raise ValueError("Explicit millimetre grids required")
    data = np.asarray(labels.dataobj)
    intensity = np.asarray(source.dataobj, dtype=np.float32)
    if not np.isfinite(intensity).all() or not np.equal(data, np.rint(data)).all():
        raise ValueError("Finite MRI and integer labels required")
    hippocampus = np.isin(data, list(REGIONS.values()))
    occupied = np.argwhere(hippocampus)
    if not len(occupied) or any(not np.any(data == identifier) for identifier in REGIONS.values()):
        raise ValueError("Both acquired hippocampus masks required")
    spacing = np.linalg.norm(source.affine[:3, :3], axis=0)
    pad = np.ceil(8 / spacing).astype(int) + 2
    lower = np.maximum(occupied.min(axis=0) - pad, 0)
    upper = np.minimum(occupied.max(axis=0) + pad + 1, source.shape)
    slices = tuple(slice(int(lo), int(hi)) for lo, hi in zip(lower, upper))
    crop = data[slices]
    grid = np.indices(crop.shape, dtype=np.float32).reshape(3, -1).T + lower
    world = nib.affines.apply_affine(source.affine, grid)
    inverse = np.linalg.inv(source.affine[:3, :3])
    brain = crop > 0
    brain_distance = distance_transform_edt(brain, sampling=spacing)
    brain_weight = np.clip(brain_distance / 4, 0, 1)
    brain_weight = brain_weight * brain_weight * (3 - 2 * brain_weight)
    components, targets, original_counts = {}, {}, {}
    for region, identifier in REGIONS.items():
        original_counts[region] = int(np.count_nonzero(crop == identifier))
        ratio = scalar_volumes[region] / observed_volumes[region]
        if not np.isfinite(ratio) or not 0.5 <= ratio <= 1.5:
            raise ValueError("Scalar ratio outside the supported illustration range")
        targets[region] = original_counts[region] * ratio
        distance = distance_transform_edt(crop != identifier, sampling=spacing)
        weight = np.clip(1 - distance / 8, 0, 1)
        weight = weight * weight * (3 - 2 * weight) * brain_weight
        center = nib.affines.apply_affine(source.affine,
            np.argwhere(crop == identifier).mean(axis=0) + lower)
        components[region] = (world - center) * weight.reshape(-1, 1)
    strengths = {region: 0.0 for region in REGIONS}

    def sample() -> tuple[np.ndarray, np.ndarray]:
        displacement = sum(components[r] * strengths[r] for r in REGIONS)
        coordinates = grid + displacement @ inverse.T
        if np.any(coordinates < 0) or np.any(coordinates > np.array(source.shape) - 1):
            raise ValueError("Local deformation leaves source coverage")
        sampled = map_coordinates(data, coordinates.T, order=0, prefilter=False)
        return sampled, displacement

    # Reconcile both regions after any small overlap in their transition bands.
    for _ in range(2):
        for region, identifier in REGIONS.items():
            lo, hi = -0.2, 0.5
            best = (float("inf"), strengths[region])
            for attempt in range(21):
                strength = 0.0 if attempt == 0 else (lo + hi) / 2
                strengths[region] = strength
                sampled, _ = sample()
                count = int(np.count_nonzero(sampled == identifier))
                error = abs(count - targets[region])
                if error < best[0]:
                    best = (error, strength)
                if count > targets[region]:
                    lo = strength
                else:
                    hi = strength
            strengths[region] = best[1]
    sampled, displacement = sample()
    field_crop = displacement.reshape((*crop.shape, 3)).astype(np.float32)
    minimum_jacobian = float(jacobians(field_crop, source.affine).min())
    if minimum_jacobian <= 0:
        raise ValueError("Local hippocampus illustration folds")
    metadata = {"version": VERSION, "minimum_jacobian": minimum_jacobian,
        "support_mm": 8, "outside_roi_max_abs_difference": 0.0, "regions": {}}
    voxel_volume = abs(float(np.linalg.det(source.affine[:3, :3])))
    for region, identifier in REGIONS.items():
        count = int(np.count_nonzero(sampled == identifier))
        if count == 0 or abs(count - targets[region]) / original_counts[region] > 0.01:
            raise ValueError("Hippocampus illustration misses the scalar volume target")
        metadata["regions"][region] = {
            "input_mask_mm3": original_counts[region] * voxel_volume,
            "display_mask_mm3": count * voxel_volume,
            "scalar_change_percent": 100 * (scalar_volumes[region] / observed_volumes[region] - 1),
            "display_change_percent": 100 * (count / original_counts[region] - 1),
        }
    coordinates = grid + displacement @ inverse.T
    affected = np.any(field_crop != 0, axis=-1)
    warped = map_coordinates(intensity, coordinates.T, order=1, prefilter=False).reshape(crop.shape)
    mri = intensity.copy()
    mri_crop = mri[slices]
    mri_crop[affected] = warped[affected]
    future_labels = data.copy()
    label_crop = future_labels[slices]
    label_crop[affected] = sampled.reshape(crop.shape)[affected]
    field = np.zeros((*source.shape, 3), dtype=np.float32)
    field[slices] = field_crop
    # Non-brain head/skull voxels must be exactly identical to the acquired input.
    if not np.array_equal(mri[data == 0], intensity[data == 0]):
        raise ValueError("Local display changed the non-brain head")
    return _image(mri, source.affine), _image(future_labels, source.affine), _image(field, source.affine), metadata
