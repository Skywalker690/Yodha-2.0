"""Optional descriptive biomarker; never a prediction or training feature."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NWBV_REFERENCE_KEY = "nwbv_age_reference_v1"


class NwbvReferenceBin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_min: int
    age_max_inclusive: int
    n: int = Field(ge=0)
    mean_fraction: float | None = Field(default=None, allow_inf_nan=False)
    sample_std_fraction: float | None = Field(default=None, allow_inf_nan=False)


class NwbvAgeReferenceBiomarker(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_id: str
    origin: Literal["source_provided"] = "source_provided"
    measurement_method: str
    schema_version: Literal[1] = 1
    metric: Literal["nWBV"] = "nWBV"
    task: Literal["descriptive_age_reference"] = "descriptive_age_reference"
    intended_use: Literal["support_value"] = "support_value"
    feature_use_allowed: Literal[False] = False
    clinical_risk: None = None
    status: Literal[
        "ok",
        "missing_input",
        "invalid_input",
        "method_mismatch",
        "unsupported_age",
        "insufficient_reference",
        "unavailable",
    ]
    feature_use_policy: str | None = None
    reference_cohort: str | None = None
    reference_profile_id: str | None = None
    reference_source_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reference_method: str | None = None
    age_years: int | None = None
    nwbv_fraction: float | None = Field(default=None, allow_inf_nan=False)
    z_score: float | None = Field(default=None, allow_inf_nan=False)
    relative_volume_band: (
        Literal[
            "more_than_2_sd_below_reference_mean",
            "between_1_and_2_sd_below_reference_mean",
            "at_or_above_1_sd_below_reference_mean",
        ]
        | None
    ) = None
    reference_bin: NwbvReferenceBin | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def descriptive_only(self) -> "NwbvAgeReferenceBiomarker":
        if self.status != "ok" and (self.z_score is not None or self.relative_volume_band is not None):
            raise ValueError("Unavailable references cannot expose a Z-score or descriptive band")
        if self.status == "ok" and (
            self.z_score is None
            or self.reference_bin is None
            or self.reference_bin.n < 10
            or self.nwbv_fraction is None
            or not 0 < self.nwbv_fraction < 1
            or self.reference_source_sha256 is None
            or self.age_years is None
            or not self.reference_bin.age_min <= self.age_years <= self.reference_bin.age_max_inclusive
            or self.measurement_method != self.reference_method
        ):
            raise ValueError("Successful reference requires supported inputs and method-matched provenance")
        return self
