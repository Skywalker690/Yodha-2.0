"""Frozen training-baseline age reference and shared anatomy feature contract."""

import hashlib
import json
import math
from collections import Counter

import numpy as np
from az_nwbv_reference.reference import NwbvReference, OASIS2_NWBV_METHOD

from ml.anatomy.contracts import AnatomyVisit

VERSION = "anatomy-input-v4-train-age-reference"
MIN_BIN_N = 2  # Sample SD needs two observations; the ten-subject cutoff is removed.


def reference_hash(profile: dict) -> str:
    return hashlib.sha256(json.dumps(profile, sort_keys=True, allow_nan=False).encode()).hexdigest()


def fit_reference_baselines(baselines: dict[str, dict], split: dict[str, str]) -> dict:
    """Fit original baseline measurements of declared training subjects only."""
    if not baselines or any(split.get(subject) != "train" for subject in baselines):
        raise ValueError("Age reference accepts training subjects only; held-out subjects forbidden")
    eligible, excluded, bins = [], {}, []
    for subject, record in sorted(baselines.items()):
        age, value = record.get("Age"), record.get("nWBV")
        if record.get("Visit") != 1 or record.get("days_from_baseline") != 0:
            excluded[subject] = "original_baseline_unavailable"
        elif record.get("CDR") != 0:
            excluded[subject] = "baseline_CDR_not_zero"
        elif not _number(age) or not float(age).is_integer() or not _number(value) or not 0 < value < 1:
            excluded[subject] = "invalid_baseline_measurement"
        elif not 60 <= age < 95:
            excluded[subject] = "unsupported_baseline_age"
        else:
            eligible.append(
                {
                    "subject_id": subject,
                    "age": int(age),
                    "nwbv": float(value),
                    "visit_id": record.get("visit_id"),
                }
            )
    for lower in range(60, 95, 5):
        values = [r["nwbv"] for r in eligible if lower <= r["age"] < lower + 5]
        sd = float(np.std(values, ddof=1)) if len(values) >= 2 else None
        bins.append(
            {
                "age_min": lower,
                "age_max_exclusive": lower + 5,
                "n": len(values),
                "mean": float(np.mean(values)) if values else None,
                "sample_std": sd,
                "status": "ok"
                if sd is not None and sd > 0
                else "invalid_spread"
                if sd == 0
                else "insufficient_reference",
            }
        )
    source_hash = reference_hash(
        {"training_subjects": sorted(baselines), "eligible": eligible, "excluded": excluded}
    )
    profile = {
        "schema_version": 1,
        "profile_id": f"{VERSION}-{source_hash[:16]}",
        "cohort_definition": "baseline_visit_1_cdr_0",
        "metric": "nWBV",
        "unit": "fraction",
        "measurement_method": OASIS2_NWBV_METHOD,
        "default_use": "support_value",
        "source_sha256": source_hash,
        "sample_std_ddof": 1,
        "min_bin_n": MIN_BIN_N,
        "training_subjects": sorted(baselines),
        "reference_subject_ids": [r["subject_id"] for r in eligible],
        "reference_subjects": len(eligible),
        "baseline_measurements": eligible,
        "excluded_subjects": excluded,
        "bins": bins,
        "feature_contract": VERSION,
        "reference_policy": "training_baseline_cdr0",
        "reference_origin": "frozen_training_baseline_cdr0_measurements",
        "fit_scope": "frozen_training_original_baselines_only",
        "independent_population_norm": False,
        "heldout_reference_overlap_possible": False,
    }
    validate_reference(profile)
    return profile


def fit_reference(histories: dict[str, list[AnatomyVisit]], split: dict[str, str]) -> dict:
    baselines = {}
    for subject, history in histories.items():
        if not history:
            raise ValueError("Training history has no baseline")
        first = min(history, key=lambda visit: visit.days_from_baseline)
        baselines[subject] = {
            **first.observed_metadata,
            "days_from_baseline": first.days_from_baseline,
            "visit_id": first.visit_id,
        }
    return fit_reference_baselines(baselines, split)


def validate_reference(profile: dict) -> None:
    # The library validates the supported-bin spreads. Zero spread remains an
    # explicit unavailable state rather than making the whole reference invalid.
    checked = {**profile, "bins": [dict(b) for b in profile["bins"]]}
    for b in checked["bins"]:
        if b.get("status") == "invalid_spread":
            b.update(n=1, sample_std=None)
    NwbvReference(checked)
    if (
        profile.get("feature_contract") != VERSION
        or profile.get("reference_policy") != "training_baseline_cdr0"
        or profile.get("min_bin_n") != MIN_BIN_N
        or profile.get("heldout_reference_overlap_possible") is not False
    ):
        raise ValueError("Incompatible anatomy age-reference contract")
    training, reference = profile.get("training_subjects", []), profile.get("reference_subject_ids", [])
    if (
        len(set(training)) != len(training)
        or len(set(reference)) != len(reference)
        or not set(reference) <= set(training)
    ):
        raise ValueError("Reference subject membership is inconsistent")


def validate_reference_split(profile: dict, split: dict[str, str]) -> None:
    validate_reference(profile)
    if any(split.get(subject) != "train" for subject in profile["training_subjects"]):
        raise ValueError("Reference contains held-out or unknown subjects")


def _number(value: object) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def z_score(visit: AnatomyVisit, profile: dict | None) -> dict:
    age, nwbv = visit.observed_metadata.get("Age"), visit.observed_metadata.get("nWBV")
    if profile is None:
        return {"status": "reference_unavailable", "z_score": None, "age_years": age, "nwbv_fraction": nwbv}
    validate_reference(profile)
    age = int(age) if _number(age) and float(age).is_integer() else age
    checked = {**profile, "bins": [dict(b) for b in profile["bins"]]}
    for b in checked["bins"]:
        if b.get("status") == "invalid_spread":
            b.update(n=1, sample_std=None)
    result = NwbvReference(checked).evaluate(age=age, nwbv=nwbv, measurement_method=OASIS2_NWBV_METHOD)
    if (
        result["status"] == "insufficient_reference"
        and profile["bins"][(age - 60) // 5].get("status") == "invalid_spread"
    ):
        result.update(
            status="invalid_reference_spread",
            z_score=None,
            relative_volume_band=None,
            reason="The training age group has zero standard deviation.",
        )
        result["reference_bin"]["sample_std_fraction"] = 0.0
        result["reference_bin"]["n"] = profile["bins"][(age - 60) // 5]["n"]
    return {
        **result,
        "task": "training_reference_anatomy_feature",
        "intended_use": "anatomy_forecast_input",
        "feature_use_allowed": True,
        "reference_policy": profile["reference_policy"],
        "independent_population_norm": False,
        "heldout_reference_overlap_possible": False,
    }


def availability(history: list[AnatomyVisit], profile: dict) -> list[dict]:
    return [
        {
            "visit_id": visit.visit_id,
            "nwbv_age_z": z_score(visit, profile),
            "MMSE": {
                "status": "ok"
                if _number(visit.observed_metadata.get("MMSE")) and 0 <= visit.observed_metadata["MMSE"] <= 30
                else "invalid_or_missing"
            },
        }
        for visit in history
    ]


def feature_availability(rows: np.ndarray, names: list[str]) -> dict:
    return {
        name: {
            "available_rows": int(np.isfinite(rows[:, i]).sum()),
            "missing_rows": int((~np.isfinite(rows[:, i])).sum()),
            "all_missing": bool(not np.isfinite(rows[:, i]).any()),
        }
        for i, name in enumerate(names)
    }


def availability_summary(histories: list[list[AnatomyVisit]], profile: dict) -> dict:
    return dict(Counter(z_score(h[-1], profile)["status"] for h in histories))
