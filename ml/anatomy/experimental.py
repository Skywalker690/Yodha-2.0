"""Explicit inference compatibility for the frozen historical fixed-reference v3 candidate."""

import json
from pathlib import Path

import numpy as np
import torch
from az_nwbv_reference.reference import NwbvReference, OASIS2_NWBV_METHOD

from ml.anatomy.contracts import AnatomyVisit
from ml.anatomy.features import reference_hash
from ml.anatomy.model import FeatureScaler, SpatialPredictor
from ml.anatomy.structural import history_features
from src.common import sha256
from src.fastsurfer.regions import REGIONS

VERSION = "conditioned-pull-cnn-v3-fixed-age-reference"
FEATURE_VERSION = "anatomy-input-v3-fixed-age-reference"
INTERVALS = [0, 183, 365, 731, 1096]


def features(history: list[AnatomyVisit], interval: int, reference: dict) -> tuple[np.ndarray, list[str]]:
    # v3/v4 have the same 129-column structure. Substitute only the frozen v3
    # reference evaluation; do not refit it or pass it to the current v4 validator.
    row, names = history_features(history, max(interval, 1), True, require_review=False)
    last = history[-1].observed_metadata
    age = last.get("Age")
    if (
        isinstance(age, (int, float))
        and not isinstance(age, bool)
        and np.isfinite(age)
        and float(age).is_integer()
    ):
        age = int(age)
    result = NwbvReference(reference).evaluate(
        age=age, nwbv=last.get("nWBV"), measurement_method=OASIS2_NWBV_METHOD
    )
    row[names.index("nwbv_age_z")] = result["z_score"] if result["z_score"] is not None else np.nan
    return row, names


class FrozenScalar:
    """Use saved fixed/random coefficients and preprocessing; never fit new weights."""

    def __init__(self, data: dict):
        self.reference = data["nwbv_reference"]
        self.feature_names = data["feature_names"]
        self.subjects, self.regions = data["subjects"], data["regions"]
        self.with_scores = data["with_scores"]
        self.fixed_width = data["fixed_width"]
        self.random_penalty = data["random_penalty"]
        self.median, self.scale, self.coefficients = (
            np.asarray(data[key], dtype=float) for key in ("median", "scale", "coefficients")
        )
        width = len(self.feature_names)
        if (
            data["feature_contract"] != FEATURE_VERSION
            or self.with_scores is not True
            or self.median.shape != (width,)
            or self.scale.shape != (width,)
            or self.fixed_width != 1 + 2 * width
            or self.random_penalty <= 0
            or self.coefficients.shape != (self.fixed_width + len(self.subjects), len(self.regions))
            or set(self.regions) != set(REGIONS)
            or np.any(self.scale <= 0)
            or not all(np.isfinite(v).all() for v in (self.median, self.scale, self.coefficients))
        ):
            raise ValueError("Invalid frozen historical scalar checkpoint")

    def rate(self, history: list[AnatomyVisit], interval: int) -> np.ndarray:
        row, names = features(history, interval, self.reference)
        if names != self.feature_names:
            raise ValueError("Historical candidate feature schema changed")
        clean = np.where(np.isfinite(row), row, self.median)
        fixed = np.r_[1, (clean - self.median) / self.scale, ~np.isfinite(row)]
        return fixed @ self.coefficients[: self.fixed_width]

    def predict(
        self, subject_id: str, history: list[AnatomyVisit], interval: int, **kwargs
    ) -> dict[str, float]:
        rate = self.rate(history, interval)
        if subject_id in self.subjects:
            rate += self.coefficients[self.fixed_width + self.subjects.index(subject_id)]
        elif len(history) >= 3:
            residuals = []
            for index in range(2, len(history)):
                gap = history[index].days_from_baseline - history[index - 1].days_from_baseline
                actual = np.array(
                    [
                        (history[index].volumes_mm3[k] - history[index - 1].volumes_mm3[k]) / (gap / 365.25)
                        for k in self.regions
                    ]
                )
                residuals.append(actual - self.rate(history[:index], gap))
            rate += np.sum(residuals, axis=0) / (len(residuals) + self.random_penalty)
        values = {
            k: float(history[-1].volumes_mm3[k] + rate[i] * interval / 365.25)
            for i, k in enumerate(self.regions)
        }
        if any(not np.isfinite(v) or v <= 0 for v in values.values()):
            raise ValueError("Experimental scalar forecast is nonfinite/nonpositive")
        return values


def load_models(directory: Path) -> tuple:
    checkpoint = torch.load(directory / "with_scores.pt", map_location="cpu", weights_only=True)
    reference = checkpoint["nwbv_reference"]
    if (
        checkpoint["version"] != VERSION
        or checkpoint["feature_contract"] != FEATURE_VERSION
        or checkpoint["with_scores"] is not True
        or not 16 <= checkpoint["grid_size"] <= 128
        or reference["feature_contract"] != FEATURE_VERSION
        or reference["reference_policy"] != "fixed_supplied_age_bins"
        or reference_hash(reference) != checkpoint["nwbv_reference_sha256"]
    ):
        raise ValueError("Explicit preview requires the exact saved historical v3 contract")
    NwbvReference(reference)
    scaler = FeatureScaler.from_dict(checkpoint["scaler"])
    scalar = FrozenScalar(json.loads((directory / "with_scores.json").read_text()))
    if (
        len(scaler.median) != 129
        or scalar.feature_names != checkpoint["feature_names"]
        or scalar.reference != reference
    ):
        raise ValueError("Historical scalar/spatial schemas or references differ")
    model = SpatialPredictor(len(scaler.median) * 2)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    return model, scaler, checkpoint, scalar


def candidate(directory: Path) -> tuple[dict, str]:
    """Require paired trained weights and the original evaluation fingerprints."""
    report = json.loads((directory / "evaluation.json").read_text())
    expected = report.get("candidate_sha256", {})
    if (
        report["synthetic"] is not False
        or report["version"] != VERSION
        or set(expected) != {"with_scores.pt", "with_scores.json"}
        or any(sha256(directory / name) != digest for name, digest in expected.items())
    ):
        raise ValueError("Historical candidate missing or changed since evaluation")
    load_models(directory)
    fingerprint = reference_hash({**expected, "evaluation.json": sha256(directory / "evaluation.json")})
    return report, fingerprint
