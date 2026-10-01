"""MRI/demographic sequence model and serializable train-only feature preprocessing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

from ml.encoder import SpatialEncoder

NUMERIC_FEATURES = ("Age", "EDUC", "SES", "MMSE", "eTIV", "nWBV", "ASF", "MR Delay", "Visit")
CATEGORY_LEVELS = {"M/F": ("M", "F"), "Hand": ("R", "L", "A")}
EXCLUDED_FEATURES = ("Subject ID", "MRI ID", "Group", "CDR")
MODEL_VERSION = "multimodal-cdr-retrospective-v2"


def feature_names() -> list[str]:
    return [
        *NUMERIC_FEATURES,
        *(f"missing_{name}" for name in NUMERIC_FEATURES),
        *(
            f"{name}_{level}"
            for name, levels in CATEGORY_LEVELS.items()
            for level in (*levels, "missing", "other")
        ),
    ]


def _numeric(frame: pd.DataFrame) -> np.ndarray:
    required = set(NUMERIC_FEATURES) | set(CATEGORY_LEVELS)
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError("Demographic data is empty or lacks required covariates")
    values = frame.loc[:, list(NUMERIC_FEATURES)].apply(pd.to_numeric, errors="raise")
    result = values.to_numpy(dtype=np.float64)
    if np.isinf(result).any():
        raise ValueError("Demographic measurements must be finite or missing")
    return result


@dataclass(frozen=True)
class DemographicPreprocessor:
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    all_missing: np.ndarray

    @classmethod
    def fit(cls, training_frame: pd.DataFrame) -> DemographicPreprocessor:
        """Caller supplies only the training split, never validation/test rows."""
        numeric = _numeric(training_frame)
        all_missing = np.isnan(numeric).all(axis=0)
        medians = np.array(
            [
                0.0 if all_missing[index] else float(np.nanmedian(numeric[:, index]))
                for index in range(numeric.shape[1])
            ]
        )
        imputed = np.where(np.isnan(numeric), medians, numeric)
        means, scales = imputed.mean(axis=0), imputed.std(axis=0)
        scales[scales < 1e-8] = 1.0
        return cls(medians, means, scales, all_missing)

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        numeric = _numeric(frame)
        missing = np.isnan(numeric)
        numeric = (np.where(missing, self.medians, numeric) - self.means) / self.scales
        columns = [numeric, missing.astype(np.float64)]
        for name, levels in CATEGORY_LEVELS.items():
            categories = np.zeros((len(frame), len(levels) + 2))
            for index, value in enumerate(frame[name]):
                token = "" if pd.isna(value) else str(value).strip().upper()
                column = (
                    len(levels)
                    if not token
                    else (levels.index(token) if token in levels else len(levels) + 1)
                )
                categories[index, column] = 1
            columns.append(categories)
        result = np.concatenate(columns, axis=1).astype(np.float32)
        if not np.isfinite(result).all():
            raise ValueError("Non-finite transformed demographic features")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_names": feature_names(),
            "medians": self.medians.tolist(),
            "means": self.means.tolist(),
            "scales": self.scales.tolist(),
            "all_missing_training_features": self.all_missing.tolist(),
        }

    @classmethod
    def from_dict(cls, state: dict[str, Any]) -> DemographicPreprocessor:
        if state["feature_names"] != feature_names():
            raise ValueError("Checkpoint demographic feature schema does not match")
        arrays = [np.asarray(state[name], dtype=np.float64) for name in ("medians", "means", "scales")]
        if any(array.shape != (len(NUMERIC_FEATURES),) or not np.isfinite(array).all() for array in arrays):
            raise ValueError("Invalid demographic preprocessing statistics")
        if (arrays[2] <= 0).any():
            raise ValueError("Demographic scales must be positive")
        return cls(*arrays, np.asarray(state["all_missing_training_features"], dtype=bool))


class MultimodalClassifier(nn.Module):
    """Jointly trainable 3D encoder, demographic MLP and packed temporal LSTM."""

    def __init__(self, demographic_dim: int | None = None) -> None:
        super().__init__()
        self.encoder = SpatialEncoder(feature_dim=32)
        self.demographics = nn.Sequential(nn.Linear(demographic_dim or len(feature_names()), 16), nn.ReLU())
        self.lstm = nn.LSTM(48, 16, batch_first=True)
        self.head = nn.Linear(16, 1)

    def forward(
        self,
        volumes: torch.Tensor,
        demographics: torch.Tensor,
        lengths: torch.Tensor,
    ) -> torch.Tensor:
        if volumes.ndim != 6 or volumes.shape[2] != 1:
            raise ValueError("Expected batch/visit/channel/3D MRI tensor")
        batch, steps = volumes.shape[:2]
        if demographics.shape[:2] != (batch, steps) or lengths.shape != (batch,):
            raise ValueError("MRI/demographic sequence dimensions disagree")
        if (lengths < 1).any() or (lengths > steps).any():
            raise ValueError("Sequence lengths must include actual visits only")
        valid = torch.arange(steps, device=volumes.device)[None, :] < lengths[:, None]
        # Padded images never pass through the encoder or contribute gradients.
        image_features = self.encoder(volumes[valid])
        demo_features = self.demographics(demographics[valid])
        fused = torch.cat([image_features, demo_features], dim=1)
        indices = torch.nonzero(valid.flatten(), as_tuple=False).flatten()
        sequence = fused.new_zeros((batch * steps, 48)).index_copy(0, indices, fused)
        packed = pack_padded_sequence(
            sequence.reshape(batch, steps, 48),
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, (hidden, _) = self.lstm(packed)
        return self.head(hidden[-1]).squeeze(-1)
