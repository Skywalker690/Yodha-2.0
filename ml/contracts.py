from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ml.anatomy.contracts import AnatomyResult
from ml.nwbv_contract import NWBV_REFERENCE_KEY, NwbvAgeReferenceBiomarker

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
    biomarkers: dict[str, list[float] | NwbvAgeReferenceBiomarker]
    selected_visit: str
    heatmap_url: str | None = None
    output_mode: Literal["demo", "precomputed", "inference", "trained", "anatomy"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    caveats: list[str]
    model_version: str = "feature-delta-v1"
    days_from_baseline: list[int]
    volume_overlays_ready: bool = False
    prediction: TrainedPrediction | None = None
    anatomy: AnatomyResult | None = None

    @model_validator(mode="after")
    def validate_series(self) -> "ProgressionResult":
        n = len(self.visit_ids)
        if not n or len(set(self.visit_ids)) != n or self.selected_visit not in self.visit_ids:
            raise ValueError("Visit identifiers must be unique and selected visit must exist")
        if len(self.days_from_baseline) != n:
            raise ValueError("Series lengths must match")
        if self.output_mode == "anatomy":
            if (
                self.anatomy is None
                or self.prediction is not None
                or self.risk_scores
                or any(name != NWBV_REFERENCE_KEY for name in self.biomarkers)
                or self.confidence is not None
                or self.volume_overlays_ready
            ):
                raise ValueError("Anatomy does not fabricate legacy risk/proxy/confidence outputs")
            if [v.visit_id for v in self.anatomy.visits] != self.visit_ids or [
                v.days_from_baseline for v in self.anatomy.visits
            ] != self.days_from_baseline:
                raise ValueError("Anatomy history must match immutable inputs")
        elif self.anatomy is not None:
            raise ValueError("Anatomy belongs to its separate versioned analysis")
        elif self.prediction is not None:
            if self.output_mode != "trained" or self.risk_scores or n < 3 or self.confidence is not None:
                raise ValueError(
                    "Trained results require three visits, one prediction and no fabricated trajectory/confidence"
                )
        elif self.output_mode == "trained" or len(self.risk_scores) != n:
            raise ValueError("Scores must match visits, or trained mode must provide one sequence prediction")
        if any(not 0 <= v <= 1 for v in self.risk_scores):
            raise ValueError("Risk scores must be finite and within [0, 1]")
        for name, value in self.biomarkers.items():
            if name == NWBV_REFERENCE_KEY:
                if not isinstance(value, NwbvAgeReferenceBiomarker) or value.visit_id != self.selected_visit:
                    raise ValueError("nWBV reference must describe the selected observed visit")
            elif not isinstance(value, list):
                raise ValueError("Only the versioned nWBV biomarker can contain a structured reference")
        series = [value for value in self.biomarkers.values() if isinstance(value, list)]
        if any(len(v) != n for v in series):
            raise ValueError("Biomarker lengths must match visits")
        if any(not isfinite(value) for values in series for value in values):
            raise ValueError("Biomarker values must be finite")
        if any(day < 0 for day in self.days_from_baseline):
            raise ValueError("Visit days must be nonnegative")
        if any(b <= a for a, b in zip(self.days_from_baseline, self.days_from_baseline[1:])):
            raise ValueError("Visits must be strictly chronological")
        return self
