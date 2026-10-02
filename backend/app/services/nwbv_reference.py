"""Attach source-matched nWBV context after inference, outside every model's inputs."""

import logging
from functools import lru_cache
from math import isfinite
from typing import Any

from ml.contracts import ProgressionResult
from ml.nwbv_contract import NWBV_REFERENCE_KEY, NwbvAgeReferenceBiomarker

logger = logging.getLogger(__name__)
OASIS_SOURCE_METHOD = "oasis2_csv_nwbv_fraction_v1"


@lru_cache(maxsize=1)
def reference() -> Any:
    from az_nwbv_reference import NwbvReference

    return NwbvReference.bundled()


def finite_number(value: Any) -> bool:
    try:
        return type(value) in {int, float} and isfinite(value)
    except OverflowError:
        return False


def evaluate(visit_id: str, inputs: dict) -> NwbvAgeReferenceBiomarker:
    age, nwbv = inputs.get("age"), inputs.get("nwbv")
    method = inputs.get("measurement_method") or "unknown"
    if not isinstance(method, str):
        method = "unknown"
    # The importer stores all numeric covariates as float. Normalize integral
    # numeric ages only; do not coerce strings, booleans or fractional ages.
    valid_age = finite_number(age) and float(age).is_integer()
    valid_nwbv = finite_number(nwbv)
    normalized_age = int(age) if valid_age else None
    normalized_nwbv = float(nwbv) if valid_nwbv else None
    try:
        payload = reference().evaluate(age=normalized_age, nwbv=normalized_nwbv, measurement_method=method)
        if age is None or nwbv is None:
            payload.update(
                status="missing_input", reason="Recorded age and source nWBV are required for this visit."
            )
        return NwbvAgeReferenceBiomarker.model_validate(
            {**payload, "visit_id": visit_id, "measurement_method": method}
        )
    except Exception:
        logger.exception("Optional nWBV reference unavailable for visit %s", visit_id)
        return NwbvAgeReferenceBiomarker(
            visit_id=visit_id,
            measurement_method=method,
            status="unavailable",
            reason="The local nWBV reference package/profile is unavailable or invalid; inspect worker logs.",
        )


def attach(result: ProgressionResult, snapshot: list[dict]) -> ProgressionResult:
    item = next(s for s in snapshot if s["visit_id"] == result.selected_visit)
    inputs = item.get("nwbv_reference_input")
    if inputs is None:
        # Compatibility for queued anatomy snapshots created before integration.
        # These flags identify metadata frozen by the existing OASIS importer.
        metadata = item.get("metadata") or {}
        if "Age" in metadata or "nWBV" in metadata:
            inputs = {
                "age": metadata.get("Age"),
                "nwbv": metadata.get("nWBV"),
                "measurement_method": OASIS_SOURCE_METHOD
                if item.get("source_units_verified") and item.get("etiv_unit") == "cm3"
                else "unknown",
            }
    if inputs is None:
        result.biomarkers.pop(NWBV_REFERENCE_KEY, None)
    else:
        result.biomarkers[NWBV_REFERENCE_KEY] = evaluate(result.selected_visit, inputs)
    return ProgressionResult.model_validate(result.model_dump())
