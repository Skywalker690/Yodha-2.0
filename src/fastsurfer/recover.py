"""Explicit recovery of real outputs after Windows fails on the Linux stats alias.

Never retries segmentation, fabricates anatomy, or approves visual QC. Preserve the
failed record and disclose output-based verification rather than inventing exit status.
"""

import json
import re

import nibabel as nib
import numpy as np

from src.common import command, config, resolve, sha256, write_json
from src.fastsurfer.feature_map import STATS_RELATIVE, VOLUME_LABELS
from src.fastsurfer.manifest import scans, subject_dir
from src.fastsurfer.parse_stats import build_features, parse_stats


def recover(cfg: dict) -> dict:
    recovered = 0
    rejected = 0
    for row in scans(cfg).to_dict("records"):
        directory = subject_dir(cfg, row["scan_id"])
        path = directory / "processing.json"
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") != "failed" or record.get("error") != "OSError":
            continue
        try:
            source = resolve(row["source_mri_path"])
            native = resolve(cfg["processed_dir"]) / "native" / f"{row['scan_id']}.nii.gz"
            if (
                record["version"] != cfg["version"]
                or record["image"] != cfg["image"]
                or record["patient_id"] != row["patient_id"]
                or record["scan_id"] != row["scan_id"]
                or not re.search(r"@sha256:[0-9a-f]{64}$", record["digest"])
                or record["source_sha256"] != sha256(source)
                or record["native_sha256"] != sha256(native)
                or (
                    source.suffix == ".hdr"
                    and record["source_pair_sha256"] != sha256(source.with_suffix(".img"))
                )
            ):
                raise ValueError("Source/version provenance changed")
            stats = directory / STATS_RELATIVE
            parse_stats(stats)
            segmentation = directory / "mri/aparc.DKTatlas+aseg.deep.mgz"
            image = nib.load(str(segmentation))
            labels = np.asanyarray(image.dataobj)
            if labels.ndim != 3 or not np.isfinite(labels).all():
                raise ValueError("Invalid real segmentation")
            if not set(label for label, _ in VOLUME_LABELS.values()).issubset(set(np.unique(labels))):
                raise ValueError("Required anatomical labels absent")
            backup = directory / "processing.io-failed.json"
            if backup.exists():
                raise ValueError("Existing recovery record is immutable")
            write_json(backup, record)
            record.update(
                status="completed",
                verification_method="explicit_output_verification_after_windows_stats_alias_error",
                container_exit_code=record.get("container_exit_code"),
                recovered_error=record.pop("error"),
                output_sha256={
                    STATS_RELATIVE: sha256(stats),
                    "mri/aparc.DKTatlas+aseg.deep.mgz": sha256(segmentation),
                },
            )
            write_json(path, record)
            recovered += 1
        except (OSError, ValueError, KeyError, TypeError):
            rejected += 1
    return {
        "recovered_outputs": recovered,
        "rejected_outputs": rejected,
        "qc": build_features(cfg),
        "visual_qc_approved": False,
    }


if __name__ == "__main__":
    print(recover(config(command("configs/fastsurfer.yaml").config)))
