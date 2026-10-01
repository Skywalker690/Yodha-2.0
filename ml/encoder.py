import numpy as np
import torch
from torch import nn


def extract_features(volume: np.ndarray) -> np.ndarray:
    """A transparent 4x4x4 pooled spatial representation, without untrained weights."""
    tensor = torch.from_numpy(np.ascontiguousarray(volume))[None, None]
    with torch.no_grad():
        return torch.nn.functional.adaptive_avg_pool3d(tensor, (4, 4, 4)).flatten().numpy()


class SpatialEncoder(nn.Module):
    """Trainable extension interface. Never used for inference without trained weights."""

    def __init__(self, feature_dim: int = 32) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv3d(1, 8, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool3d(2),
            nn.Conv3d(8, feature_dim, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.layers(images)
