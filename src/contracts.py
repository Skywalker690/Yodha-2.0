from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.common import HORIZONS


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    contract_version: Literal["2"] = "2"
    patient_id: str = Field(min_length=1, max_length=100)
    baseline: dict[str, float | None] = Field(
        description="Baseline source predictors; OASIS-2 eTIV in cm3/mL, nWBV/ASF unitless. No future visits."
    )
    fastsurfer_features: dict[str, float | None] | None = None
    fastsurfer_version: str | None = None
    feature_set_version: str | None = None
    scan_id: str | None = None
    qc: Literal["passed", "pending_review", "failed", "unavailable"] = "unavailable"


class PredictionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    status: Literal["ok", "partial", "unavailable"]
    mode: Literal["live", "unavailable"]
    model_version: str
    preprocessing_version: str
    fastsurfer_version: str | None = None
    used_mri: bool = False
    target: Literal["observed_cdr_conversion"] = "observed_cdr_conversion"
    probabilities: dict[str, float | None]
    raw_probabilities: dict[str, float | None]
    calibration: dict[str, str]
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_probabilities(self) -> "PredictionResult":
        if set(self.probabilities) != {str(h) for h in HORIZONS}:
            raise ValueError("All horizons must be present, with null when unavailable")
        if set(self.raw_probabilities) != set(self.probabilities) or set(self.calibration) != set(
            self.probabilities
        ):
            raise ValueError("Raw probabilities and calibration must cover all horizons")
        if any(p is not None and not 0 <= p <= 1 for p in self.raw_probabilities.values()):
            raise ValueError("Raw probability outside [0,1]")
        known = [p for p in self.probabilities.values() if p is not None]
        if any(not 0 <= p <= 1 for p in known):
            raise ValueError("Probability outside [0,1]")
        chronological = [
            self.probabilities[str(h)] for h in HORIZONS if self.probabilities[str(h)] is not None
        ]
        if chronological != sorted(chronological):
            raise ValueError("Cumulative probabilities must be monotonic")
        return self
