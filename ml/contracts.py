from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MODEL_VERSION = "feature-delta-v1"


class VisitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_id: str
    days_from_baseline: int = Field(ge=0)
    mri_path: str
    covariates: dict[str, float | str | None] = Field(default_factory=dict)


class TrainedPrediction(BaseModel):
    """One retrospective sequence prediction, never a future-disease probability."""

    model_config = ConfigDict(extra="forbid")
    target: Literal["observed_cdr_increase"] = "observed_cdr_increase"
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    decision_threshold: float = Field(ge=0, le=1, allow_inf_nan=False)
    predicted_increase: bool
    checkpoint_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    cohort_role: Literal["train", "validation", "test", "unassigned"]
    training_subjects: int = Field(ge=1)
    training_visits: int = Field(ge=1)
    test_subjects: int = Field(ge=1)
    test_accuracy: float = Field(ge=0, le=1, allow_inf_nan=False)
    test_balanced_accuracy: float = Field(ge=0, le=1, allow_inf_nan=False)
    test_roc_auc: float = Field(ge=0, le=1, allow_inf_nan=False)
    majority_baseline_accuracy: float = Field(ge=0, le=1, allow_inf_nan=False)
    quality_status: Literal["experimental_poor_generalization"] = "experimental_poor_generalization"

    @model_validator(mode="after")
    def validate_decision(self) -> "TrainedPrediction":
        if self.predicted_increase != (self.score >= self.decision_threshold):
            raise ValueError("Classification must use the saved validation-selected threshold")
        return self


class ProgressionResult(BaseModel):
    patient_id: str
    visit_ids: list[str]
    risk_scores: list[float]
    biomarkers: dict[str, list[float]]
    selected_visit: str
    heatmap_url: str | None = None
    output_mode: Literal["demo", "precomputed", "inference", "trained"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    caveats: list[str]
    model_version: str = "feature-delta-v1"
    days_from_baseline: list[int]
    volume_overlays_ready: bool = False
    prediction: TrainedPrediction | None = None

    @model_validator(mode="after")
    def validate_series(self) -> "ProgressionResult":
        n = len(self.visit_ids)
        if not n or len(set(self.visit_ids)) != n or self.selected_visit not in self.visit_ids:
            raise ValueError("Visit identifiers must be unique and selected visit must exist")
        if len(self.days_from_baseline) != n:
            raise ValueError("Series lengths must match")
        if self.prediction is not None:
            if self.output_mode != "trained" or self.risk_scores or n < 3 or self.confidence is not None:
                raise ValueError(
                    "Trained results require three visits, one prediction and no fabricated trajectory/confidence"
                )
        elif self.output_mode == "trained" or len(self.risk_scores) != n:
            raise ValueError("Scores must match visits, or trained mode must provide one sequence prediction")
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
