"""Freeze a scan-count-based study independently of historical disease classifiers."""

import csv
import hashlib
from collections import Counter
from pathlib import Path

from ml.data import read_metadata
from scripts.train_longitudinal_model import _find_volume
from src.common import sha256, write_json

VERSION = "anatomy-score-history-cohort-v2"
SEED = 20261002


def create_cohort(metadata: Path, dataset: Path, output: Path) -> dict:
    """Use all >=3-scan subjects; reserve representative subject-level holdouts."""
    if output.exists():
        raise ValueError("Anatomy cohort is immutable; choose a fresh output directory")
    frame = read_metadata(metadata).sort_values(["Subject ID", "MR Delay"])
    if frame["MRI ID"].duplicated().any():
        raise ValueError("MRI identifiers must be unique")
    subjects = {}
    for subject, visits in frame.groupby("Subject ID", sort=True):
        if len(visits) < 3:
            continue
        days = visits["MR Delay"].to_numpy()
        if len(visits) > 5 or any(b <= a for a, b in zip(days, days[1:])):
            raise ValueError("Three-to-five chronological source visits required")
        subjects[str(subject)] = [
            {
                "visit_id": str(row["MRI ID"]),
                "days_from_baseline": int(row["MR Delay"]),
                "mri_path": str(_find_volume(dataset, str(row["MRI ID"])).resolve()),
            }
            for _, row in visits.iterrows()
        ]
    distribution = Counter(len(v) for v in subjects.values())
    if distribution != {3: 43, 4: 9, 5: 4}:
        raise ValueError("Supplied cohort changed; audit membership before creating another study")
    buckets = {
        count: sorted(
            (s for s, v in subjects.items() if len(v) == count),
            key=lambda s: hashlib.sha256(f"{SEED}:{s}".encode()).hexdigest(),
        )
        for count in (3, 4, 5)
    }
    roles = {s: "train" for s in subjects}
    for role, start, number in (("selection", 0, 3), ("calibration", 3, 3), ("test", 6, 2)):
        for subject in buckets[3][start : start + number]:
            roles[subject] = role
    for subject, role in zip(buckets[4][:3], ("selection", "calibration", "test")):
        roles[subject] = role
    roles[buckets[5][0]] = "test"
    order = sorted(subjects, key=lambda s: (-len(subjects[s]), s))
    output.mkdir(parents=True)
    split_path = output / "subject_split.csv"
    with split_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["subject_id", "split", "scan_count"])
        writer.writeheader()
        writer.writerows({"subject_id": s, "split": roles[s], "scan_count": len(subjects[s])} for s in order)
    with (output / "app-manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["patient_id", "visit_id", "visit_index", "days_from_baseline", "mri_path"]
        )
        writer.writeheader()
        for subject in order:
            for index, visit in enumerate(subjects[subject]):
                writer.writerow({"patient_id": subject, "visit_index": index, **visit})
    result = {
        "version": VERSION,
        "seed": SEED,
        "model_policy": "MTA-Koedam-conditioned-only",
        "selection_policy": "all subjects with >=3 scans, processed by descending scan count",
        "metadata_sha256": sha256(metadata),
        "split_sha256": sha256(split_path),
        "app_manifest_sha256": sha256(output / "app-manifest.csv"),
        "counts": dict(Counter(roles.values())),
        "scan_count_distribution": dict(distribution),
        "subjects": [{"subject_id": s, "role": roles[s], "visits": subjects[s]} for s in order],
        "independent_clinical_validation": False,
    }
    write_json(output / "cohort.json", result)
    return result
