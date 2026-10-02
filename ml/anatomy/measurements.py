"""Scalar changes do not imply voxel correspondence or anatomical registration."""

import math

from ml.anatomy.contracts import AnatomyVisit


def etiv_mm3(value_cm3: float | None) -> float | None:
    if value_cm3 is None:
        return None
    if isinstance(value_cm3, bool) or not math.isfinite(value_cm3) or value_cm3 <= 0:
        raise ValueError("eTIV must be a positive source cm3/mL measurement")
    return value_cm3 * 1000.0


def asymmetry(left: float, right: float) -> float:
    if not all(math.isfinite(v) and v > 0 for v in (left, right)):
        raise ValueError("Positive bilateral volumes required")
    return 200 * (left - right) / (left + right)


def changes(visits: list[AnatomyVisit]) -> list[dict]:
    output = []
    for earlier, later in zip(visits, visits[1:]):
        days = later.days_from_baseline - earlier.days_from_baseline
        if (
            days <= 0
            or earlier.method != later.method
            or earlier.dictionary_version != later.dictionary_version
        ):
            raise ValueError("Chronological consistently processed measurements required")
        if earlier.volumes_mm3.keys() != later.volumes_mm3.keys():
            raise ValueError("Regional definitions changed between visits")
        reviewed = earlier.qc == later.qc == "passed"
        automatic_research = earlier.qc == later.qc == "automated_checks_only"
        regions = {}
        if reviewed or automatic_research:
            for name, before in earlier.volumes_mm3.items():
                delta = later.volumes_mm3[name] - before
                regions[name] = {
                    "absolute_mm3": delta,
                    "percent": 100 * delta / before,
                    "annualized_mm3": delta * 365.25 / days,
                    "annualized_percent": 100 * delta / before * 365.25 / days,
                }
        output.append(
            {
                "earlier_visit_id": earlier.visit_id,
                "later_visit_id": later.visit_id,
                "elapsed_days": days,
                "status": "ok"
                if reviewed
                else "automated_checks_only"
                if automatic_research
                else "pending_review",
                "regions": regions,
            }
        )
    return output
