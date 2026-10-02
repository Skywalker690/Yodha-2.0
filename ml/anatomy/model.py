"""Small proposed spatial forecast model. Untrained instances are never serving fallbacks."""

from dataclasses import dataclass

import nibabel as nib
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from ml.anatomy.registration import normalize
from src.fastsurfer.regions import REGIONS

VERSION = "conditioned-pull-cnn-v1"
CHANNELS = 6


@dataclass
class FeatureScaler:
    median: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, rows: np.ndarray) -> "FeatureScaler":
        if rows.ndim != 2 or len(rows) < 2 or np.isinf(rows).any():
            raise ValueError("Multiple finite/missing training feature rows required")
        median = np.array([np.median(c[np.isfinite(c)]) if np.isfinite(c).any() else 0.0 for c in rows.T])
        scale = np.std(np.where(np.isfinite(rows), rows, median), axis=0)
        scale[scale < 1e-8] = 1.0
        return cls(median, scale)

    def transform(self, row: np.ndarray) -> np.ndarray:
        if row.shape[-1] != len(self.median) or np.isinf(row).any():
            raise ValueError("Feature schema/nonfinite values changed")
        return np.concatenate(
            [
                (np.where(np.isfinite(row), row, self.median) - self.median) / self.scale,
                (~np.isfinite(row)).astype(float),
            ],
            axis=-1,
        ).astype(np.float32)

    def to_dict(self) -> dict:
        return {"median": self.median.tolist(), "scale": self.scale.tolist()}

    @classmethod
    def from_dict(cls, data: dict) -> "FeatureScaler":
        median, scale = np.array(data["median"]), np.array(data["scale"])
        if (
            median.ndim != 1
            or scale.shape != median.shape
            or not np.isfinite([median, scale]).all()
            or np.any(scale <= 0)
        ):
            raise ValueError("Invalid saved feature scaler")
        return cls(median, scale)


def image_channels(
    current: nib.Nifti1Image, earlier_aligned: nib.Nifti1Image, labels: nib.Nifti1Image, elapsed_days: int
) -> np.ndarray:
    if elapsed_days <= 0 or any(
        v.shape != current.shape or not np.allclose(v.affine, current.affine)
        for v in (earlier_aligned, labels)
    ):
        raise ValueError("Cutoff-local registered history and label grid required")
    current_data = np.asarray(normalize(current).dataobj)
    prior = np.asarray(normalize(earlier_aligned).dataobj)
    categorical = np.asarray(labels.dataobj)
    if not np.isfinite(categorical).all() or not np.equal(categorical, np.rint(categorical)).all():
        raise ValueError("Finite categorical anatomy required")
    return np.stack(
        [
            current_data,
            (current_data - prior) / (elapsed_days / 365.25),
            np.isin(categorical, [17, 53]),
            np.isin(categorical, [4, 43]),
            (categorical >= 1000),
            categorical > 0,
        ]
    ).astype(np.float32)


class SpatialPredictor(nn.Module):
    """Time-conditioned smooth RAS-mm pull displacement; zero time is exactly identity."""

    def __init__(self, feature_count: int):
        super().__init__()
        if not 1 <= feature_count <= 256:
            raise ValueError("Bounded conditioning schema required")
        self.feature_count = feature_count
        self.encoder = nn.Sequential(
            nn.Conv3d(CHANNELS, 8, 3, padding=1),
            nn.GroupNorm(4, 8),
            nn.SiLU(),
            nn.Conv3d(8, 16, 3, stride=2, padding=1),
            nn.GroupNorm(4, 16),
            nn.SiLU(),
            nn.Conv3d(16, 16, 3, padding=1),
            nn.SiLU(),
        )
        self.condition = nn.Sequential(nn.Linear(feature_count, 32), nn.SiLU(), nn.Linear(32, 32))
        self.decoder = nn.Sequential(nn.Conv3d(16, 8, 3, padding=1), nn.SiLU(), nn.Conv3d(8, 3, 3, padding=1))

    def forward(self, images: torch.Tensor, features: torch.Tensor, years: torch.Tensor) -> torch.Tensor:
        if (
            images.ndim != 5
            or images.shape[1] != CHANNELS
            or features.shape != (len(images), self.feature_count)
            or years.shape != (len(images),)
        ):
            raise ValueError("Invalid spatial forecast batch")
        if (
            not torch.isfinite(images).all()
            or not torch.isfinite(features).all()
            or not torch.isfinite(years).all()
            or torch.any(years < 0)
        ):
            raise ValueError("Invalid spatial inputs/time")
        latent = self.encoder(images)
        scale, bias = self.condition(features).chunk(2, dim=1)
        latent = latent * (1 + scale[:, :, None, None, None]) + bias[:, :, None, None, None]
        raw = self.decoder(latent)
        raw = F.interpolate(raw, size=images.shape[2:], mode="trilinear", align_corners=True)
        raw = F.avg_pool3d(raw, 5, stride=1, padding=2)
        # Zero field at FOV boundaries prevents extrapolation; this is a field
        # constraint, not a rule for estimating tissue volume or atrophy scores.
        tapers = [
            torch.sin(torch.linspace(0, torch.pi, n, device=raw.device, dtype=raw.dtype)).square()
            for n in images.shape[2:]
        ]
        taper = tapers[0][:, None, None] * tapers[1][None, :, None] * tapers[2][None, None, :]
        return torch.tanh(raw) * 10.0 * years[:, None, None, None, None] * taper


def sampling_grid(field: torch.Tensor, affine: torch.Tensor) -> torch.Tensor:
    """Torch input axes XYZ; grid_sample's coordinate order is ZYX."""
    shape = field.shape[2:]
    axes = [torch.arange(n, device=field.device, dtype=field.dtype) for n in shape]
    base = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=-1)[None]
    ras = field.permute(0, 2, 3, 4, 1)
    voxel = torch.einsum("bij,bxyzj->bxyzi", torch.linalg.inv(affine[:, :3, :3]), ras)
    locations = base + voxel
    sizes = torch.tensor(shape, device=field.device, dtype=field.dtype)
    normalized = 2 * locations / (sizes - 1) - 1
    return normalized[..., [2, 1, 0]]


def differentiable_warp(data: torch.Tensor, field: torch.Tensor, affine: torch.Tensor) -> torch.Tensor:
    return F.grid_sample(
        data, sampling_grid(field, affine), mode="bilinear", padding_mode="zeros", align_corners=True
    )


def field_jacobians(field: torch.Tensor, affine: torch.Tensor) -> torch.Tensor:
    ras = field.permute(0, 2, 3, 4, 1)
    derivatives = torch.stack(torch.gradient(ras, dim=(1, 2, 3)), dim=-1)
    world = torch.einsum("bxyzci,bij->bxyzcj", derivatives, torch.linalg.inv(affine[:, :3, :3]))
    return torch.linalg.det(world + torch.eye(3, device=field.device, dtype=field.dtype))


def spatial_loss(
    predicted: torch.Tensor,
    target: torch.Tensor,
    images: torch.Tensor,
    later: torch.Tensor,
    labels: torch.Tensor,
    affine: torch.Tensor,
    target_ratios: torch.Tensor,
) -> tuple[torch.Tensor, dict]:
    field_error = F.smooth_l1_loss(predicted, target)
    image_error = F.l1_loss(differentiable_warp(images[:, :1], predicted, affine), later)
    smooth = sum(g.square().mean() for g in torch.gradient(predicted, dim=(2, 3, 4)))
    folding = F.relu(0.05 - field_jacobians(predicted, affine)).square().mean()
    identifiers = torch.tensor([v[0] for _, v in sorted(REGIONS.items())], device=labels.device)
    onehot = (labels[:, None] == identifiers[None, :, None, None, None]).float()
    before = onehot.sum(dim=(2, 3, 4))
    if torch.any(before <= 0):
        raise ValueError("A region disappeared on the learning grid; increase resolution")
    after = differentiable_warp(onehot, predicted, affine).sum(dim=(2, 3, 4))
    volume_error = F.mse_loss(after / before, target_ratios)
    loss = field_error + 0.2 * image_error + 0.02 * smooth + 20 * folding + volume_error
    return loss, {
        "field": float(field_error.detach()),
        "image": float(image_error.detach()),
        "volume": float(volume_error.detach()),
        "folding": float(folding.detach()),
    }
