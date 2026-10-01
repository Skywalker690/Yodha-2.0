from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd

from src.common import command, config, resolve, sha256
from src.fastsurfer.feature_map import FEATURE_SET, VOLUME_LABELS
from src.fastsurfer.manifest import scans, subject_dir


def parse_stats(path: Path) -> dict[str, float]:
    headers = None
    units = {}
    columns = {}
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if line.startswith("# ColHeaders"):
            headers = parts[2:]
        elif line.startswith("# TableCol") and len(parts) >= 5:
            index, field, value = parts[2], parts[3], parts[4]
            if field == "ColHeader":
                columns[index] = value
            elif field == "Units":
                units[index] = value
        elif parts and not line.startswith("#"):
            if headers is None or len(parts) != len(headers):
                raise ValueError("Malformed FastSurfer statistics row")
            row = dict(zip(headers, parts))
            if "SegId" not in row or "StructName" not in row or "Volume_mm3" not in row:
                raise ValueError("Missing volume statistics columns")
            label = int(row["SegId"])
            if label in records:
                raise ValueError("Duplicate segmentation label")
            records[label] = row
    volume_column = next((i for i, name in columns.items() if name == "Volume_mm3"), None)
    if volume_column is None or units.get(volume_column) not in ("mm^3", "mm3"):
        raise ValueError("Physical volume units are unverified")
    features = {}
    for feature, (label, name) in VOLUME_LABELS.items():
        row = records.get(label)
        if row is None or row["StructName"] != name:
            raise ValueError("Required exact anatomical label is missing or mismatched")
        value = float(row["Volume_mm3"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Invalid anatomical measurement")
        features[feature] = value
    features["hippocampus_total_mm3"] = features["hippocampus_left_mm3"] + features["hippocampus_right_mm3"]
    return features


def build_features(cfg: dict) -> dict:
    rows = []
    for scan in scans(cfg).to_dict("records"):
        directory = subject_dir(cfg, scan["scan_id"])
        row = {
            "patient_id": scan["patient_id"],
            "scan_id": scan["scan_id"],
            "qc": "unavailable",
            "fastsurfer_version": cfg["version"],
            "feature_set_version": FEATURE_SET,
        }
        try:
            provenance = json.loads((directory / "processing.json").read_text())
            stats_path = directory / "stats/aseg+DKT.stats"
            if provenance["status"] != "completed" or provenance["version"] != cfg["version"]:
                raise ValueError("Processing incomplete or version mismatch")
            if provenance["patient_id"] != scan["patient_id"] or provenance["scan_id"] != scan["scan_id"]:
                raise ValueError("Source/patient mismatch")
            source = resolve(scan["source_mri_path"])
            if sha256(source) != provenance["source_sha256"]:
                raise ValueError("Source MRI changed after processing")
            if (
                source.suffix == ".hdr"
                and sha256(source.with_suffix(".img")) != provenance["source_pair_sha256"]
            ):
                raise ValueError("Source image pair changed after processing")
            if not re.search(r"@sha256:[0-9a-f]{64}$", provenance["digest"]):
                raise ValueError("Container digest missing")
            for key, expected_hash in provenance["output_sha256"].items():
                path = (directory / key).resolve()
                if not path.is_relative_to(directory.resolve()) or sha256(path) != expected_hash:
                    raise ValueError("Changed FastSurfer output")
            features = parse_stats(stats_path)
            review = (
                json.loads((directory / "qc.json").read_text()) if (directory / "qc.json").exists() else {}
            )
            passed = review.get("status") == "passed" and review.get("stats_sha256") == sha256(stats_path)
            row.update(
                features,
                qc="passed" if passed else "pending_review",
                digest=provenance["digest"],
                stats_sha256=sha256(stats_path),
            )
        except (OSError, ValueError, KeyError):
            row["qc"] = "unavailable" if not directory.exists() else "failed"
        rows.append(row)
    frame = pd.DataFrame(rows)
    for feature in (*VOLUME_LABELS, "hippocampus_total_mm3"):
        if feature not in frame:
            frame[feature] = None
    frame.to_csv(resolve(cfg["processed_dir"]) / "fastsurfer_features.csv", index=False)
    return frame["qc"].value_counts().to_dict()


if __name__ == "__main__":
    print(build_features(config(command("configs/fastsurfer.yaml").config)))
