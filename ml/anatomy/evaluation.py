"""Physical overlap/surface and structural uncertainty evaluation, never fabricated metrics."""

import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
import nibabel as nib

from src.fastsurfer.regions import REGIONS


def geometry_metrics(predicted: nib.Nifti1Image, target: nib.Nifti1Image) -> dict:
    if any(image.header.get_xyzt_units()[0] != "mm" for image in (predicted, target)):
        raise ValueError("Physical surface evaluation requires explicit millimetre units")
    if predicted.shape != target.shape or not np.allclose(predicted.affine, target.affine):
        raise ValueError("Evaluation requires a documented common physical coordinate grid")
    results = {}
    a, b = np.asarray(predicted.dataobj), np.asarray(target.dataobj)
    if any(not np.isfinite(data).all() or not np.equal(data, np.rint(data)).all() for data in (a, b)):
        raise ValueError("Finite categorical evaluation anatomy required")
    voxel = abs(float(np.linalg.det(target.affine[:3, :3])))
    for name, (identifier, _) in REGIONS.items():
        left, right = a == identifier, b == identifier
        if not left.any() or not right.any():
            raise ValueError("Missing predicted/held-out region")
        boundary_a, boundary_b = left & ~binary_erosion(left), right & ~binary_erosion(right)
        points_a = nib.affines.apply_affine(predicted.affine, np.argwhere(boundary_a))
        points_b = nib.affines.apply_affine(target.affine, np.argwhere(boundary_b))
        distances = np.r_[cKDTree(points_a).query(points_b)[0], cKDTree(points_b).query(points_a)[0]]
        results[name] = {
            "dice": float(2 * (left & right).sum() / (left.sum() + right.sum())),
            "assd_mm": float(distances.mean()),
            "hd95_mm": float(np.percentile(distances, 95)),
            "absolute_volume_error_mm3": float(abs(int(left.sum()) - int(right.sum())) * voxel),
        }
    return results


def calibrate_intervals(errors: dict[str, list[np.ndarray]], level: float = 0.8) -> dict | None:
    """Subject-block split conformal; max over each subject's repeated forecast errors."""
    if not 0 < level < 1 or len(errors) < 4:
        return None
    values = np.array([np.max(np.abs(rows), axis=0) for rows in errors.values()])
    rank = int(np.ceil((len(values) + 1) * level))
    if rank > len(values) or not np.isfinite(values).all():
        return None
    radius = np.sort(values, axis=0)[rank - 1]
    return {
        "level": level,
        "radius_mm3": radius.tolist(),
        "calibration_subjects": len(values),
        "method": "subject-block split conformal",
    }


def interval_coverage(calibration: dict | None, errors: dict[str, list[np.ndarray]]) -> dict | None:
    if calibration is None or len(errors) < 4:
        return None
    radius = np.array(calibration["radius_mm3"])
    values = np.array([np.max(np.abs(rows), axis=0) for rows in errors.values()])
    covered = values <= radius
    return {
        "subjects": len(errors),
        "per_region": covered.mean(axis=0).tolist(),
        "simultaneous": float(covered.all(axis=1).mean()),
        "evaluated": True,
    }
