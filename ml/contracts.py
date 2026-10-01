from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MODEL_VERSION = "feature-delta-v1"


class VisitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_id: str
    days_from_baseline: int = Field(ge=0)
    mri_path: str


class ProgressionResult(BaseModel):
    patient_id: str
    visit_ids: list[str]
    risk_scores: list[float]
    biomarkers: dict[str, list[float]]
    selected_visit: str
    heatmap_url: str | None = None
    output_mode: Literal["demo", "precomputed", "inference"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    caveats: list[str]
    model_version: str = "feature-delta-v1"
    days_from_baseline: list[int]
    volume_overlays_ready: bool = False

    @model_validator(mode="after")
    def validate_series(self) -> "ProgressionResult":
        n = len(self.visit_ids)
        if not n or len(set(self.visit_ids)) != n or self.selected_visit not in self.visit_ids:
            raise ValueError("Visit identifiers must be unique and selected visit must exist")
        if len(self.risk_scores) != n or len(self.days_from_baseline) != n:
            raise ValueError("Series lengths must match")
        if any(not 0 <= v <= 1 for v in self.risk_scores):
            raise ValueError("Risk scores must be finite and within [0, 1]")
        if any(len(v) != n for v in self.biomarkers.values()):
            raise ValueError("Biomarker lengths must match visits")
        if any(not isfinite(value) for series in self.biomarkers.values() for value in series):
            raise ValueError("Biomarker values must be finite")
        if any(day < 0 for day in self.days_from_baseline):
            raise ValueError("Visit days must be nonnegative")
        if any(b <= a for a, b in zip(self.days_from_baseline, self.days_from_baseline[1:])):
            raise ValueError("Visits must be strictly chronological")
        return self
