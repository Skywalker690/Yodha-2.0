"""Create source-grid categorical masks; statistics retain partial-volume estimates."""

from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.processing import resample_from_to

from src.fastsurfer.regions import REGIONS


def geometry(image: nib.spatialimages.SpatialImage) -> None:
    if len(image.shape) != 3 or any(d < 2 for d in image.shape) or np.prod(image.shape) > 32_000_000:
        raise ValueError("Bounded 3D geometry required")
    if not np.isfinite(image.affine).all() or abs(np.linalg.det(image.affine[:3, :3])) < 1e-8:
        raise ValueError("Invalid physical affine")
    if not np.allclose(image.affine[3], [0, 0, 0, 1]):
        raise ValueError("Invalid homogeneous affine")


def export_masks(
    source: Path, segmentation: Path, output: Path, *, source_units_verified: bool = False
) -> dict[str, float]:
    image, seg = nib.load(source), nib.load(segmentation)
    geometry(image)
    geometry(seg)
    values = np.asarray(seg.dataobj)
    if (
        not np.isfinite(values).all()
        or not np.equal(values, np.rint(values)).all()
        or np.any(values < 0)
        or np.any(values > 32767)
    ):
        raise ValueError("Segmentation must contain finite categorical labels")
    source_values = np.asarray(image.dataobj)
    if not np.isfinite(source_values).all():
        raise ValueError("Nonfinite source MRI")
    units = image.header.get_xyzt_units()[0]
    if units != "mm" and not (units == "unknown" and source_units_verified):
        raise ValueError("Source physical units are not mm")
    # Imported legacy MRI headers can omit units; FastSurfer scanner-RAS and the
    # importer preserve source affines in mm. Do not rescale them a second time.
    seg_volume = abs(float(np.linalg.det(seg.affine[:3, :3])))
    source_volume = abs(float(np.linalg.det(image.affine[:3, :3])))
    mapped = np.asarray(
        resample_from_to(seg, (image.shape, image.affine), order=0, mode="constant", cval=0).dataobj
    )
    labels = np.zeros(image.shape, dtype=np.int16)
    output.mkdir(parents=True, exist_ok=True)
    measured = {}
    for name, (number, _) in REGIONS.items():
        original = int(np.count_nonzero(values == number)) * seg_volume
        mask = mapped == number
        volume = int(mask.sum()) * source_volume
        if original <= 0 or volume <= 0 or abs(volume - original) / original > 0.10:
            raise ValueError(
                "Regional coverage/physical mask volume changed by more than 10% during source-grid resampling"
            )
        measured[name] = original  # hard-label conformed voxel estimator, not stats
        labels[mask] = number
        artifact = nib.Nifti1Image(mask.astype(np.uint8), image.affine)
        artifact.header.set_xyzt_units("mm")
        nib.save(artifact, output / f"{name}.nii.gz")
    artifact = nib.Nifti1Image(labels, image.affine)
    artifact.header.set_xyzt_units("mm")
    nib.save(artifact, output / "regions.nii.gz")
    all_labels = nib.Nifti1Image(mapped.astype(np.int16), image.affine)
    all_labels.header.set_xyzt_units("mm")
    nib.save(all_labels, output / "segmentation.nii.gz")
    return measured
