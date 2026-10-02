"""Physical deformation verification helpers, NOT a trained spatial predictor."""

from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import map_coordinates

from ml.anatomy.masks import geometry


def jacobians(pull_mm: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """Jacobian of future-world -> current-world: x_current=x_future+u(x_future)."""
    if (
        pull_mm.ndim != 4
        or pull_mm.shape[-1] != 3
        or min(pull_mm.shape[:3]) < 2
        or not np.isfinite(pull_mm).all()
    ):
        raise ValueError("Finite XYZ vector field required")
    if (
        affine.shape != (4, 4)
        or not np.isfinite(affine).all()
        or abs(np.linalg.det(affine[:3, :3])) < 1e-8
        or not np.allclose(affine[3], [0, 0, 0, 1])
    ):
        raise ValueError("Invalid field affine")
    derivatives = np.stack([np.stack(np.gradient(pull_mm[..., i]), axis=-1) for i in range(3)], axis=-2)
    world = derivatives @ np.linalg.inv(affine[:3, :3])
    return np.linalg.det(world + np.eye(3))


def warp(
    source: nib.spatialimages.SpatialImage, pull: nib.Nifti1Image, *, categorical: bool
) -> nib.Nifti1Image:
    """Pull field in mm defined on FUTURE grid; do not use a forward field as a sampler."""
    geometry(source)
    displacement = np.asarray(pull.dataobj)
    if np.prod(displacement.shape[:3]) > 32_000_000 or min(displacement.shape[:3]) < 2:
        raise ValueError("Bounded physical field required")
    if source.header.get_xyzt_units()[0] != "mm" or pull.header.get_xyzt_units()[0] != "mm":
        raise ValueError("Explicit millimetre source/field units required")
    if not np.isfinite(displacement).all() or np.any(jacobians(displacement, pull.affine) <= 0):
        raise ValueError("Nonpositive Jacobian/folding")
    grid = np.indices(displacement.shape[:3]).reshape(3, -1).T
    future_world = nib.affines.apply_affine(pull.affine, grid)
    current_world = future_world + displacement.reshape(-1, 3)
    current_voxel = nib.affines.apply_affine(np.linalg.inv(source.affine), current_world)
    shape = np.array(source.shape)
    if np.any(current_voxel < -1e-5) or np.any(current_voxel > shape - 1 + 1e-5):
        raise ValueError("Missing source coverage: no extrapolation outside MRI")
    data = np.asarray(source.dataobj)
    if not np.isfinite(data).all() or (categorical and not np.equal(data, np.rint(data)).all()):
        raise ValueError("Invalid source intensities/categorical labels")
    sampled = map_coordinates(
        data, current_voxel.T, order=0 if categorical else 1, mode="nearest", prefilter=False
    ).reshape(displacement.shape[:3])
    result = nib.Nifti1Image(sampled.astype(data.dtype if categorical else np.float32), pull.affine)
    result.header.set_xyzt_units("mm")
    return result


def mesh(mask: nib.Nifti1Image, destination: Path) -> dict:
    """Closed mask boundary, NOT a reconstructed cortical surface. No smoothing/scaling twice."""
    from skimage.measure import marching_cubes
    from scipy.ndimage import label

    geometry(mask)
    data = np.asarray(mask.dataobj)
    if not np.isin(data, [0, 1]).all() or not data.any():
        raise ValueError("Nonempty binary mask required")
    if any(np.take(data, edge, axis=axis).any() for axis in range(3) for edge in (0, -1)):
        raise ValueError("Mask intersects field-of-view boundary; surface is not closed")
    components = int(label(data)[1])
    vertices, faces, _, _ = marching_cubes(data.astype(np.float32), 0.5, gradient_direction="ascent")
    vertices = nib.affines.apply_affine(mask.affine, vertices).astype(np.float32)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, edge_counts = np.unique(edges, axis=0, return_counts=True)
    if np.any(edge_counts != 2):
        raise ValueError("Mesh is not a closed two-manifold surface")
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    if np.any(np.linalg.norm(np.cross(b - a, c - a), axis=1) <= 1e-8):
        raise ValueError("Mesh contains degenerate faces")
    signed_volume = float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6)
    if signed_volume < 0:
        faces = faces[:, [0, 2, 1]]
    measured = float(data.sum() * abs(np.linalg.det(mask.affine[:3, :3])))
    relative_error = abs(abs(signed_volume) - measured) / measured
    if relative_error > 0.05:
        raise ValueError("Mesh differs from mask voxel volume by more than 5%; no simplification accepted")
    arrays = [
        nib.gifti.GiftiDataArray(vertices, intent="NIFTI_INTENT_POINTSET"),
        nib.gifti.GiftiDataArray(faces.astype(np.int32), intent="NIFTI_INTENT_TRIANGLE"),
    ]
    nib.save(nib.gifti.GiftiImage(darrays=arrays), destination)
    return {
        "coordinate_units": "mm",
        "components": components,
        "voxel_volume_mm3": measured,
        "mesh_volume_mm3": abs(signed_volume),
        "relative_volume_error": relative_error,
        "surface_kind": "categorical mask boundary, not cortical reconstruction",
    }
