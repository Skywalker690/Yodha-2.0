import numpy as np
from PIL import Image

from ml.preprocessing import slice_image


def difference_overlay(volume: np.ndarray, baseline: np.ndarray) -> Image.Image:
    """Display absolute intensity differences; no attribution or registration claim."""
    gray = np.asarray(slice_image(volume)).astype(np.float32)
    difference = np.rot90(np.abs(volume[:, :, volume.shape[2] // 2] - baseline[:, :, baseline.shape[2] // 2]))
    alpha = np.clip(difference * 2.5, 0, 0.8)[..., None]
    color = np.zeros_like(gray)
    color[..., 0] = 250
    color[..., 1] = 100 + 100 * (1 - np.clip(difference, 0, 1))
    color[..., 2] = 60
    return Image.fromarray(np.clip(gray * (1 - alpha) + color * alpha, 0, 255).astype(np.uint8))
