from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image

MAX_VOXELS = 32_000_000
STANDARD_SHAPE = (64, 64, 64)


@dataclass
class PreparedVolume:
    volume: np.ndarray
    original_shape: tuple[int, ...]
    voxel_sizes: tuple[float, ...]
    affine: np.ndarray


def load_validated(path: Path, allow_pair: bool = False) -> nib.spatialimages.SpatialImage:
    """Bound memory before loading and reject unsafe or unsupported image structure."""
    if not path.is_file():
        raise ValueError("MRI file is missing")
    name = path.name.lower()
    if not (name.endswith((".nii", ".nii.gz")) or allow_pair and name.endswith((".hdr", ".img"))):
        raise ValueError("Expected a .nii or .nii.gz MRI volume")
    try:
        img = nib.load(str(path))
        shape = img.shape
        if len(shape) == 4 and shape[-1] == 1:
            shape = shape[:3]
        if len(shape) != 3 or min(shape) < 8 or np.prod(shape, dtype=np.int64) > MAX_VOXELS:
            raise ValueError(
                "MRI must be a 3D volume (or a single-volume 4D image), 8+ voxels per axis, at most 32 million voxels"
            )
        if img.get_data_dtype().kind not in {"i", "u", "f"}:
            raise ValueError("MRI must contain real numeric values")
        if not np.isfinite(img.affine).all() or abs(np.linalg.det(img.affine[:3, :3])) < 1e-8:
            raise ValueError("MRI spatial transform is invalid")
        voxels = img.get_fdata(dtype=np.float32, caching="unchanged")
        if not np.isfinite(voxels).all():
            raise ValueError("MRI contains non-finite values")
        if float(np.ptp(voxels)) <= 0:
            raise ValueError("MRI has no intensity variation")
        return img
    except ValueError:
        raise
    except Exception:
        raise ValueError("MRI could not be read. Check file contents and header/image pairing.") from None


def canonical_data(img: nib.spatialimages.SpatialImage) -> np.ndarray:
    return np.squeeze(nib.as_closest_canonical(img).get_fdata(dtype=np.float32, caching="unchanged"))


def convert_paired_volume(source: Path, output: Path) -> None:
    """Convert a validated header/image pair without changing its voxel grid or affine."""
    img = load_validated(source, allow_pair=True)
    if not {"header", "image"}.issubset(img.file_map):
        raise ValueError("The selected files must contain a paired header/image MRI, not a renamed single volume")
    voxels = np.squeeze(img.get_fdata(dtype=np.float32, caching="unchanged"))
    header = nib.Nifti1Header.from_header(img.header)
    converted = nib.Nifti1Image(voxels, img.affine, header=header)
    converted.set_data_dtype(np.float32)
    # get_fdata has already applied the source intensity scaling.
    converted.header.set_slope_inter(1.0, 0.0)
    nib.save(converted, output)


def normalize(data: np.ndarray) -> np.ndarray:
    low, high = np.percentile(data, [1, 99.5])
    if high <= low:
        raise ValueError("MRI has insufficient intensity range")
    return np.clip((data - low) / (high - low), 0, 1).astype(np.float32)


def prepare(path: Path, allow_pair: bool = False) -> PreparedVolume:
    from monai.transforms import Resize
    import torch

    torch.set_num_threads(2)
    img = load_validated(path, allow_pair=allow_pair)
    canonical = nib.as_closest_canonical(img)
    data = normalize(np.squeeze(canonical.get_fdata(dtype=np.float32, caching="unchanged")))
    resized = Resize(STANDARD_SHAPE, mode="trilinear", align_corners=False)(data[None])
    volume = np.asarray(resized[0], dtype=np.float32)
    # MONAI align_corners=False maps new voxel centres to (i + .5) * scale - .5.
    # Preserve that field of view for display; this is not anatomical registration.
    scale = np.asarray(data.shape, dtype=np.float64) / np.asarray(STANDARD_SHAPE)
    transform = np.eye(4)
    transform[:3, :3] = np.diag(scale)
    transform[:3, 3] = (scale - 1) / 2
    return PreparedVolume(
        volume, tuple(img.shape), tuple(float(x) for x in img.header.get_zooms()[:3]),
        canonical.affine @ transform,
    )


def slice_image(volume: np.ndarray, axis: int = 2, fraction: float = 0.5) -> Image.Image:
    index = min(volume.shape[axis] - 1, int(volume.shape[axis] * fraction))
    plane = np.rot90(np.take(volume, index, axis=axis))
    return Image.fromarray((np.clip(plane, 0, 1) * 255).astype(np.uint8)).convert("RGB")


def render_preview(path: Path, output: Path) -> dict:
    img = load_validated(path)
    image = slice_image(normalize(canonical_data(img)))
    image.resize((384, 384), Image.Resampling.BILINEAR).save(output)
    return {"shape": list(img.shape), "voxelSizes": [float(x) for x in img.header.get_zooms()[:3]]}
