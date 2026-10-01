"""Review gate; statistical validity alone is not segmentation accuracy."""

import argparse
import json

from src.common import config, sha256, write_json
from src.fastsurfer.manifest import subject_dir
from src.fastsurfer.parse_stats import build_features, parse_stats


def approve(cfg: dict, scan_id: str, reviewer: str) -> None:
    if not reviewer.strip():
        raise ValueError("Review attribution required")
    directory = subject_dir(cfg, scan_id)
    record = json.loads((directory / "processing.json").read_text())
    if record.get("status") != "completed":
        raise ValueError("Cannot approve incomplete processing")
    stats = directory / "stats/aseg+DKT.stats"
    parse_stats(stats)
    write_json(
        directory / "qc.json",
        {"status": "passed", "reviewer": reviewer, "stats_sha256": sha256(stats), "visual_review": True},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/fastsurfer.yaml")
    parser.add_argument("--approve-scan", help="Only after visually inspecting the segmentation on T1")
    parser.add_argument("--reviewer", default="")
    args = parser.parse_args()
    cfg = config(args.config)
    if args.approve_scan:
        approve(cfg, args.approve_scan, args.reviewer)
    print(build_features(cfg))
