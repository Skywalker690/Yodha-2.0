"""Cutoff-local rigid alignment and target-only nonlinear correspondence in physical space."""

import nibabel as nib
import numpy as np
import SimpleITK as sitk

from ml.anatomy.masks import geometry
from ml.anatomy.spatial import jacobians

RAS_TO_LPS = np.diag([-1.0, -1.0, 1.0])
VERSION = "cutoff-rigid-demons-v1"


def as_sitk(image: nib.Nifti1Image) -> sitk.Image:
    geometry(image)
    if image.header.get_xyzt_units()[0] != "mm":
        raise ValueError("Registration requires verified millimetre units")
    data = np.asarray(image.dataobj, dtype=np.float32)
    if not np.isfinite(data).all():
        raise ValueError("Nonfinite registration image")
    matrix = RAS_TO_LPS @ image.affine[:3, :3]
    spacing = np.linalg.norm(matrix, axis=0)
    direction = matrix / spacing
    if not np.allclose(direction.T @ direction, np.eye(3), atol=1e-5):
        raise ValueError("Sheared affine unsupported; explicit physical resampling required")
    result = sitk.GetImageFromArray(data.transpose(2, 1, 0))
    result.SetSpacing(tuple(spacing))
    result.SetDirection(tuple(direction.ravel()))
    result.SetOrigin(tuple(RAS_TO_LPS @ image.affine[:3, 3]))
    return result


def nifti(data: np.ndarray, affine: np.ndarray) -> nib.Nifti1Image:
    result = nib.Nifti1Image(data, affine)
    result.header.set_xyzt_units("mm")
    return result


def normalize(image: nib.Nifti1Image) -> nib.Nifti1Image:
    data = np.asarray(image.dataobj, dtype=np.float32)
    if not np.isfinite(data).all():
        raise ValueError("Nonfinite MRI")
    foreground = data[data > 0]
    if foreground.size < 64:
        raise ValueError("Insufficient MRI foreground")
    low, high = np.percentile(foreground, [1, 99.5])
    if high <= low:
        raise ValueError("Constant MRI")
    return nifti(np.clip((data - low) / (high - low), 0, 1).astype(np.float32), image.affine)


def learning_grid(image: nib.Nifti1Image, size: int = 96) -> nib.Nifti1Image:
    """Retain cutoff field of view, voxel centres and physical coordinates; no future template."""
    from nibabel.processing import resample_from_to

    if size < 16 or size > 128:
        raise ValueError("Learning grid size must be 16..128")
    geometry(image)
    mapping = np.eye(4)
    mapping[:3, :3] = np.diag((np.array(image.shape) - 1) / (size - 1))
    affine = image.affine @ mapping
    mapped = resample_from_to(image, ((size,) * 3, affine), order=1, mode="nearest")
    return nifti(np.asarray(mapped.dataobj, np.float32), affine)


def rigid(fixed: nib.Nifti1Image, moving: nib.Nifti1Image) -> tuple[sitk.Transform, dict]:
    """Transform maps fixed cutoff LPS coordinates into moving acquisition LPS coordinates."""
    fixed_itk, moving_itk = as_sitk(normalize(fixed)), as_sitk(normalize(moving))
    initial = sitk.CenteredTransformInitializer(
        fixed_itk, moving_itk, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY
    )
    registration = sitk.ImageRegistrationMethod()
    registration.SetNumberOfThreads(2)
    registration.SetMetricAsMattesMutualInformation(32)
    registration.SetMetricSamplingStrategy(registration.RANDOM)
    registration.SetMetricSamplingPercentage(0.2, 42)
    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetOptimizerAsRegularStepGradientDescent(1.0, 0.001, 150)
    registration.SetOptimizerScalesFromPhysicalShift()
    registration.SetShrinkFactorsPerLevel([4, 2, 1])
    registration.SetSmoothingSigmasPerLevel([2, 1, 0])
    registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    registration.SetInitialTransform(initial, inPlace=False)
    transform = registration.Execute(fixed_itk, moving_itk)
    metric = float(registration.GetMetricValue())
    if not np.isfinite(metric):
        raise ValueError("Rigid registration failed")
    return transform, {
        "method": VERSION,
        "metric": metric,
        "stop": registration.GetOptimizerStopConditionDescription(),
        "visual_qc": "pending_review",
    }


def resample(
    moving: nib.Nifti1Image, fixed: nib.Nifti1Image, transform: sitk.Transform, *, categorical: bool
) -> nib.Nifti1Image:
    data = np.asarray(moving.dataobj)
    if categorical and not np.equal(data, np.rint(data)).all():
        raise ValueError("Categorical labels required")
    result = sitk.Resample(
        as_sitk(moving),
        as_sitk(fixed),
        transform,
        sitk.sitkNearestNeighbor if categorical else sitk.sitkLinear,
        0.0,
    )
    values = sitk.GetArrayFromImage(result).transpose(2, 1, 0)
    return nifti(values.astype(np.int16 if categorical else np.float32), fixed.affine)


def target_pull(
    current: nib.Nifti1Image, later_aligned: nib.Nifti1Image, iterations: int = 80
) -> tuple[nib.Nifti1Image, dict]:
    """Hidden later image is a supervision target only. Future -> current pull map."""
    if current.shape != later_aligned.shape or not np.allclose(current.affine, later_aligned.affine):
        raise ValueError("Target and cutoff require the same physical grid")
    fixed, moving = as_sitk(normalize(later_aligned)), as_sitk(normalize(current))
    matcher = sitk.HistogramMatchingImageFilter()
    matcher.SetNumberOfHistogramLevels(256)
    matcher.SetNumberOfMatchPoints(7)
    matcher.ThresholdAtMeanIntensityOn()
    moving = matcher.Execute(moving, fixed)
    demons = sitk.DiffeomorphicDemonsRegistrationFilter()
    demons.SetNumberOfThreads(2)
    demons.SetNumberOfIterations(iterations)
    demons.SetStandardDeviations(1.5)
    field = demons.Execute(fixed, moving)
    ras = sitk.GetArrayFromImage(field).transpose(2, 1, 0, 3) @ RAS_TO_LPS
    jac = jacobians(ras, current.affine)
    if not np.isfinite(ras).all() or np.any(jac <= 0):
        raise ValueError("Nonlinear registration target folds")
    return nifti(ras.astype(np.float32), current.affine), {
        "method": VERSION,
        "direction": "future_to_current_pull_RAS_mm",
        "minimum_jacobian": float(jac.min()),
        "metric": float(demons.GetMetric()),
        "visual_qc": "pending_review",
    }
