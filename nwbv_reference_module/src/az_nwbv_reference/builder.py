"""Build a deterministic OASIS-2 baseline-CDR-0 nWBV reference from a source CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

from .reference import DEFAULT_USE, NwbvReference, OASIS2_NWBV_METHOD, SCHEMA_VERSION

REQUIRED = {"Subject ID", "Visit", "MR Delay", "CDR", "Age"}


def build_profile(csv_path: Path, *, min_bin_n: int = 10,
                  metric_column: str = "nWBV",
                  measurement_method: str = OASIS2_NWBV_METHOD,
                  profile_id: str = "oasis2_baseline_cdr0_nwbv_v1") -> dict:
    if min_bin_n < 2:
        raise ValueError("min_bin_n must be at least two")
    if not measurement_method or not profile_id:
        raise ValueError("Measurement method and versioned profile ID are required")
    if measurement_method == OASIS2_NWBV_METHOD and metric_column != "nWBV":
        raise ValueError("The OASIS-2 method ID requires the original nWBV column")
    if measurement_method != OASIS2_NWBV_METHOD and profile_id == "oasis2_baseline_cdr0_nwbv_v1":
        raise ValueError("Use a new profile ID for a different measurement method")
    source_bytes = csv_path.read_bytes()
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = REQUIRED | {metric_column}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError(f"Missing columns: {sorted(required - set(reader.fieldnames or ()))}")
        rows = list(reader)

    by_bin: dict[int, list[float]] = defaultdict(list)
    selected_ids: set[str] = set()
    outside_reference_age = 0
    for row in rows:
        if int(row["Visit"]) != 1:
            continue
        if float(row["MR Delay"]) != 0:
            raise ValueError(f'Baseline visit has nonzero MR Delay: {row["Subject ID"]}')
        if float(row["CDR"]) != 0:
            continue
        subject = row["Subject ID"]
        if subject in selected_ids:
            raise ValueError(f"Duplicate baseline subject: {subject}")
        selected_ids.add(subject)
        age = int(row["Age"])
        nwbv = float(row[metric_column])
        if not math.isfinite(nwbv) or not 0 < nwbv < 1:
            raise ValueError(f"Invalid nWBV for {subject}")
        if not 60 <= age < 95:
            outside_reference_age += 1
            continue
        by_bin[60 + 5 * ((age - 60) // 5)].append(nwbv)

    if not selected_ids:
        raise ValueError("No baseline CDR-0 records found")
    bins = []
    for start in range(60, 95, 5):
        values = by_bin[start]
        bins.append({"age_min": start, "age_max_exclusive": start + 5, "n": len(values),
                     "mean": mean(values) if values else None,
                     "sample_std": stdev(values) if len(values) > 1 else None})
    profile = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "cohort_definition": "baseline_visit_1_cdr_0",
        "metric": "nWBV", "unit": "fraction",
        "measurement_method": measurement_method,
        "default_use": DEFAULT_USE,
        "source_metric_column": metric_column,
        "min_bin_n": min_bin_n,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_rows": len(rows),
        "reference_subjects": len(selected_ids),
        "subjects_outside_age_range": outside_reference_age,
        "sample_std_ddof": 1,
        "bins": bins,
        "interpretation": "descriptive research-cohort comparison; no disease diagnosis or risk probability",
    }
    NwbvReference(profile)
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-bin-n", type=int, default=10)
    parser.add_argument("--metric-column", default="nWBV", help="Column containing a compatible fraction")
    parser.add_argument("--measurement-method", default=OASIS2_NWBV_METHOD)
    parser.add_argument("--profile-id", default="oasis2_baseline_cdr0_nwbv_v1")
    args = parser.parse_args()
    profile = build_profile(args.csv, min_bin_n=args.min_bin_n,
                            metric_column=args.metric_column,
                            measurement_method=args.measurement_method,
                            profile_id=args.profile_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"profile_id": profile["profile_id"],
                      "reference_subjects": profile["reference_subjects"],
                      "source_sha256": profile["source_sha256"],
                      "bin_counts": [b["n"] for b in profile["bins"]]}, indent=2))


if __name__ == "__main__":
    main()
