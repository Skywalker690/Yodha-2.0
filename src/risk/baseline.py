"""Serializable numeric logistic model; no pickle execution at inference."""

from __future__ import annotations

import numpy as np
from scipy.special import expit


def fit_head(x: np.ndarray, y: np.ndarray, regularization_c: float, seed: int) -> dict:
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if np.isnan(x).all(axis=0).any():
        raise ValueError("A predictor is missing in every training row")
    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=regularization_c, max_iter=2000, random_state=seed),
    )
    pipeline.fit(x, y)
    imputer, scaler, model = pipeline.steps[0][1], pipeline.steps[1][1], pipeline.steps[2][1]
    head = {
        "medians": imputer.statistics_.tolist(),
        "means": scaler.mean_.tolist(),
        "scales": scaler.scale_.tolist(),
        "coefficients": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "threshold": 0.5,
        "calibration": "uncalibrated",
    }
    if not np.allclose(pipeline.predict_proba(x)[:, 1], score(head, x), atol=1e-12):
        raise ValueError("Serialized model failed prediction round-trip")
    return head


def transformed(head: dict, x: np.ndarray) -> np.ndarray:
    medians, means, scales = (np.asarray(head[k], dtype=float) for k in ("medians", "means", "scales"))
    if x.shape[-1] != len(medians) or not (len(medians) == len(means) == len(scales)):
        raise ValueError("Model preprocessing dimension mismatch")
    if not all(np.isfinite(v).all() for v in (medians, means, scales)) or (scales <= 0).any():
        raise ValueError("Invalid saved preprocessing")
    return (np.where(np.isnan(x), medians, x) - means) / scales


def score(head: dict, x: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(head["coefficients"], dtype=float)
    if not np.isfinite(coefficients).all() or not np.isfinite(head["intercept"]):
        raise ValueError("Nonfinite model parameters")
    return expit(transformed(head, x) @ coefficients + head["intercept"])


def monotonic(values: dict[str, float | None]) -> dict[str, float | None]:
    result = {}
    previous = 0.0
    for horizon in (12, 24, 36):
        value = values[str(horizon)]
        if value is None:
            result[str(horizon)] = None
        else:
            previous = max(previous, float(value))
            result[str(horizon)] = previous
    return result
