"""Optional experimental 128³ branch; never selected without a validated artifact."""

import torch
from torch import nn


class BaselineFusion(nn.Module):
    def __init__(self, numeric_features: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv3d(1, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv3d(16, 32, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv3d(32, 64, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
        )
        self.numeric = nn.Sequential(nn.Linear(numeric_features, 16), nn.ReLU())
        self.head = nn.Linear(80, 3)

    def forward(self, volumes: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        if volumes.shape[1:] != (1, 128, 128, 128):
            raise ValueError("Optional MRI tensor must be [B,1,128,128,128]")
        return self.head(torch.cat((self.encoder(volumes), self.numeric(features)), dim=1))


def masked_loss(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    mask = torch.isfinite(labels)
    if not mask.any():
        raise ValueError("Batch has no known outcome labels")
    if not torch.isin(labels[mask], torch.tensor([0.0, 1.0], device=labels.device)).all():
        raise ValueError("Known labels must be binary")
    return nn.functional.binary_cross_entropy_with_logits(logits[mask], labels[mask])
