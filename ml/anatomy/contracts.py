from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "longitudinal-anatomy-v1"


class RatingEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["unavailable", "invalid", "pending_alignment_qc", "unreviewed_research", "ok"] = (
        "unavailable"
    )
    method: str = "AVRA-v0.8-candidate"
    mta_left: float | None = Field(default=None, allow_inf_nan=False)
    mta_right: float | None = Field(default=None, allow_inf_nan=False)
    posterior_atrophy: float | None = Field(default=None, allow_inf_nan=False)
    warnings: list[str] = Field(default_factory=list)
    agreement_validated: Literal[False] = False
    provenance_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reviewer_id: str | None = None
    reviewed_at: str | None = None

    @model_validator(mode="after")
    def available(self) -> "RatingEstimate":
        values = [self.mta_left, self.mta_right, self.posterior_atrophy]
        if self.status in {"ok", "unreviewed_research"} and any(v is None for v in values):
            raise ValueError("Successful rating requires all released outputs")
        if self.status not in {"ok", "unreviewed_research"} and any(v is not None for v in values):
            raise ValueError("Unverified alignment/invalid ratings must not expose scores")
        outside = any(
            value is not None and not 0 <= value <= upper for value, upper in zip(values, (4, 4, 3))
        )
        if outside and not (
            self.status == "unreviewed_research"
            and self.method == "AVRA-v0.8-ensemble-raw-regression-research"
            and any("outside nominal scale" in warning for warning in self.warnings)
        ):
            raise ValueError(
                "Out-of-scale AVRA estimates require an explicit raw research policy and warning"
            )
        return self


class AnatomyVisit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_id: str
    days_from_baseline: int = Field(ge=0)
    qc: Literal["pending_review", "automated_checks_only", "passed"]
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    segmentation_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    statistics_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    container_digest: str = Field(pattern=r"^[^@\s]+@sha256:[a-f0-9]{64}$")
    method: str = "FastSurfer-2.5.4-native-T1"
    fastsurfer_version: str = "2.5.4"
    dictionary_version: str = "dkt-longitudinal-v1"
    volumes_mm3: dict[str, float]
    mask_volumes_mm3: dict[str, float]
    etiv_mm3: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    head_size_ratios: dict[str, float] = Field(default_factory=dict)
    hippocampal_asymmetry_percent: float = Field(allow_inf_nan=False)
    observed_metadata: dict[str, float | str | None] = Field(default_factory=dict)
    ratings: RatingEstimate = Field(default_factory=RatingEstimate)
    reviewer_id: str | None = None
    reviewed_at: str | None = None

    @model_validator(mode="after")
    def volumes(self) -> "AnatomyVisit":
        import math

        if not self.volumes_mm3 or self.volumes_mm3.keys() != self.mask_volumes_mm3.keys():
            raise ValueError("Both physical estimators require identical regional fields")
        if any(
            not math.isfinite(v) or v <= 0
            for v in [*self.volumes_mm3.values(), *self.mask_volumes_mm3.values()]
        ):
            raise ValueError("Regional volumes must be finite and positive")
        if any(not math.isfinite(v) or not 0 < v < 1 for v in self.head_size_ratios.values()):
            raise ValueError("Head-size ratios must be physical fractions")
        if self.qc == "passed" and (not self.reviewer_id or not self.reviewed_at):
            raise ValueError("Visual review provenance required")
        return self


class ForecastArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=r"^[a-z0-9_-]+$")
    kind: Literal["mri", "labels", "field", "mesh"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class StructuralForecast(BaseModel):
    """No numeric/spatial output can be served without a separate evaluated release."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["unavailable", "available"] = "unavailable"
    cutoff_visit_id: str
    interval_days: int = Field(ge=0, le=3650)
    target: Literal["future_regional_anatomy"] = "future_regional_anatomy"
    warnings: list[str]
    volumes_mm3: dict[str, float] | None = None
    experimental: bool = False
    training_subject_count: int | None = Field(default=None, ge=1)
    prediction_intervals: dict[str, tuple[float, float]] | None = None
    interval_evidence: dict | None = None
    spatial_model_version: str | None = None
    model_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    release_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    feature_contract: str | None = None
    reference_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reference_profile_id: str | None = None
    feature_availability: list[dict] | None = None
    artifacts: list[ForecastArtifact] = Field(default_factory=list, max_length=48)

    @model_validator(mode="after")
    def released(self) -> "StructuralForecast":
        import math
        from src.fastsurfer.regions import REGIONS

        if self.status == "unavailable":
            if (
                any(
                    v is not None
                    for v in (
                        self.volumes_mm3,
                        self.prediction_intervals,
                        self.interval_evidence,
                        self.spatial_model_version,
                        self.model_sha256,
                        self.release_sha256,
                        self.feature_contract,
                        self.reference_sha256,
                        self.reference_profile_id,
                        self.feature_availability,
                    )
                )
                or self.artifacts
            ):
                raise ValueError("Unavailable forecasts cannot expose numeric/spatial substitutes")
            return self
        if (
            not self.volumes_mm3
            or set(self.volumes_mm3) != set(REGIONS)
            or any(not math.isfinite(v) or v <= 0 for v in self.volumes_mm3.values())
            or not all((self.spatial_model_version, self.model_sha256, self.release_sha256))
            or len({a.name for a in self.artifacts}) != len(self.artifacts)
            or not {"mri", "labels", "pull", "brain_mesh"}.issubset({a.name for a in self.artifacts})
        ):
            raise ValueError("Available forecast requires a complete evaluated native artifact set")
        if self.prediction_intervals is not None:
            if (
                not self.interval_evidence
                or self.interval_evidence.get("evaluated") is not True
                or set(self.prediction_intervals) != set(REGIONS)
            ):
                raise ValueError("Intervals require held-out coverage evidence for every region")
            for region, (low, high) in self.prediction_intervals.items():
                if (
                    not math.isfinite(low)
                    or not math.isfinite(high)
                    or not 0 < low <= self.volumes_mm3[region] <= high
                ):
                    raise ValueError("Invalid physical prediction interval")
        elif self.interval_evidence is not None:
            raise ValueError("Evidence without intervals is inconsistent")
        return self


class AnatomyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["longitudinal-anatomy-v1"] = VERSION
    visits: list[AnatomyVisit] = Field(min_length=1, max_length=5)
    changes: list[dict]
    sign_convention: str = "later minus earlier; negative volume change means loss"
    forecast: StructuralForecast
    cortical_thickness: None = None
    spatial_registration: Literal["not_performed", "cutoff_local_rigid"] = "not_performed"

    @model_validator(mode="after")
    def chronology(self) -> "AnatomyResult":
        if len({v.visit_id for v in self.visits}) != len(self.visits):
            raise ValueError("Duplicate anatomy visits")
        if any(b.days_from_baseline <= a.days_from_baseline for a, b in zip(self.visits, self.visits[1:])):
            raise ValueError("Strict chronological anatomy required")
        if self.forecast.cutoff_visit_id != self.visits[-1].visit_id:
            raise ValueError("Forecast cutoff must match latest observed input")
        return self
