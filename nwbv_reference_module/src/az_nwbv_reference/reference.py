"""Versioned, method-aware age-bin comparison for OASIS-2 nWBV values."""

from __future__ import annotations

import json
import math
from importlib import resources
from pathlib import Path
from typing import Any

OASIS2_NWBV_METHOD = "oasis2_csv_nwbv_fraction_v1"
SCHEMA_VERSION = 1
DEFAULT_USE = "support_value"


class NwbvReference:
    """Compare a source-compatible nWBV fraction with the local CDR-0 cohort.

    The resulting Z-score describes position within a small research sample.
    It is not a percentile, disease probability, diagnosis, or prognosis.
    """

    def __init__(self, profile: dict[str, Any]):
        if profile.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported reference schema")
        if profile.get("metric") != "nWBV" or profile.get("unit") != "fraction":
            raise ValueError("Reference metric or unit mismatch")
        if not isinstance(profile.get("measurement_method"), str) or not profile["measurement_method"]:
            raise ValueError("A measurement method ID is required")
        if not isinstance(profile.get("profile_id"), str) or not profile["profile_id"]:
            raise ValueError("A versioned profile ID is required")
        if profile.get("cohort_definition") != "baseline_visit_1_cdr_0":
            raise ValueError("Reference cohort definition mismatch")
        if profile.get("default_use") != DEFAULT_USE:
            raise ValueError("nWBV reference must default to support-value use")
        if not isinstance(profile.get("min_bin_n"), int) or profile["min_bin_n"] < 2:
            raise ValueError("Invalid minimum age-bin size")
        if not isinstance(profile.get("source_sha256"), str) or len(profile["source_sha256"]) != 64:
            raise ValueError("Missing source fingerprint")
        bins = profile.get("bins")
        if not isinstance(bins, list) or len(bins) != 7:
            raise ValueError("Expected seven five-year age bins")
        for index, age_bin in enumerate(bins):
            lower = 60 + index * 5
            if age_bin.get("age_min") != lower or age_bin.get("age_max_exclusive") != lower + 5:
                raise ValueError("Age bins must be consecutive and non-overlapping")
            n = age_bin.get("n")
            mean = age_bin.get("mean")
            sd = age_bin.get("sample_std")
            if not isinstance(n, int) or n < 0:
                raise ValueError("Invalid reference count")
            if n and (not isinstance(mean, (int, float)) or not math.isfinite(mean)
                      or not 0 < mean < 1):
                raise ValueError("Invalid reference mean")
            if n >= profile["min_bin_n"] and (not isinstance(sd, (int, float))
                                               or not math.isfinite(sd) or sd <= 0):
                raise ValueError("Invalid reference spread")
        self.profile = profile

    @classmethod
    def from_file(cls, path: str | Path) -> "NwbvReference":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def bundled(cls) -> "NwbvReference":
        data = resources.files("az_nwbv_reference").joinpath("data/oasis2_baseline_cdr0_v1.json")
        return cls(json.loads(data.read_text(encoding="utf-8")))

    def evaluate(self, *, age: int, nwbv: float, measurement_method: str) -> dict[str, Any]:
        """Return a JSON-ready result, including explicit unsupported states."""
        base = {
            "schema_version": SCHEMA_VERSION,
            "metric": "nWBV",
            "task": "descriptive_age_reference",
            "intended_use": DEFAULT_USE,
            "feature_use_allowed": False,
            "feature_use_policy": "Use as a model feature only with a fold-specific reference built from training patients.",
            "reference_cohort": self.profile["cohort_definition"],
            "reference_profile_id": self.profile["profile_id"],
            "reference_source_sha256": self.profile["source_sha256"],
            "reference_method": self.profile["measurement_method"],
            "age_years": age,
            "nwbv_fraction": nwbv,
            "z_score": None,
            "relative_volume_band": None,
            "reference_bin": None,
            "clinical_risk": None,
        }

        def unavailable(status: str, reason: str) -> dict[str, Any]:
            return {**base, "status": status, "reason": reason}

        if (isinstance(age, bool) or not isinstance(age, int)
                or isinstance(nwbv, bool) or not isinstance(nwbv, (int, float))
                or not math.isfinite(nwbv) or not 0 < nwbv < 1):
            return unavailable("invalid_input", "Age must be an integer and nWBV a finite fraction between 0 and 1.")
        if measurement_method != self.profile["measurement_method"]:
            return unavailable("method_mismatch", "The patient nWBV was produced by a different or unknown measurement method.")
        if not 60 <= age < 95:
            return unavailable("unsupported_age", "Reference ages cover 60 through 94 years.")

        age_bin = self.profile["bins"][(age - 60) // 5]
        bin_info = {
            "age_min": age_bin["age_min"],
            "age_max_inclusive": age_bin["age_max_exclusive"] - 1,
            "n": age_bin["n"],
            "mean_fraction": age_bin["mean"],
            "sample_std_fraction": age_bin["sample_std"],
        }
        base["reference_bin"] = bin_info
        if age_bin["n"] < self.profile["min_bin_n"]:
            return unavailable("insufficient_reference", f"This age bin has fewer than {self.profile['min_bin_n']} reference subjects.") | {"reference_bin": bin_info}
        z = (nwbv - age_bin["mean"]) / age_bin["sample_std"]
        if z < -2:
            band = "more_than_2_sd_below_reference_mean"
        elif z < -1:
            band = "between_1_and_2_sd_below_reference_mean"
        else:
            band = "at_or_above_1_sd_below_reference_mean"
        return {**base, "status": "ok", "reason": None, "z_score": z,
                "relative_volume_band": band}
