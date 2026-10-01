import numpy as np
import torch
from torch import nn


def feature_delta_scores(features: np.ndarray) -> tuple[list[float], list[float]]:
    """Index of change from the first scan, not a calibrated disease probability."""
    delta = np.mean(np.abs(features - features[0]), axis=1)
    scores = np.clip(delta * 5.0, 0, 1)
    return scores.astype(float).tolist(), delta.astype(float).tolist()


class TemporalModel(nn.Module):
    """Small LSTM interface for a future independently evaluated trained checkpoint."""

    def __init__(self, feature_dim: int = 32, hidden_dim: int = 16) -> None:
        super().__init__()
        self.lstm = nn.LSTM(feature_dim, hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        hidden, _ = self.lstm(sequence)
        return torch.sigmoid(self.head(hidden)).squeeze(-1)
