"""Native anatomical measurements in the existing worker, never an HTTP request."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from ml.anatomy.contracts import AnatomyResult, AnatomyVisit, StructuralForecast, VERSION
from ml.anatomy.masks import export_masks
from ml.anatomy.measurements import asymmetry, changes, etiv_mm3
from ml.anatomy.ratings import AUTOMATIC_RESEARCH_RATING_POLICY, run_rating
from ml.contracts import ProgressionResult
from src.common import ROOT, config, sha256, write_json
from src.fastsurfer.feature_map import STATS_RELATIVE
from src.fastsurfer.parse_stats import parse_stats
from src.fastsurfer.regions import REGIONS
from src.fastsurfer.runner import run_scan


def run_anatomy(
    patient_id: str,
    inputs: list[dict],
    output: Path,
    progress: Callable[[int, str], None],
    *,
    rating_runtime: Path | None = None,
    automatic_research_values: bool = False,
) -> ProgressionResult:
    if not 1 <= len(inputs) <= 5:
        raise ValueError("Anatomy supports at most five visits")
    if any(b["days_from_baseline"] <= a["days_from_baseline"] for a, b in zip(inputs, inputs[1:])):
        raise ValueError("Chronological visit timing required")
    cfg = config(ROOT / "configs/fastsurfer.yaml")
    # Analysis-owned copies/settings, no baseline manifest or output mutations.
    cfg.update(output_dir=str(output / "fastsurfer"), processed_dir=str(output), surface=False)
    subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=30)
    active = subprocess.run(
        ["docker", "ps", "--filter", f"ancestor={cfg['image']}", "--format", "{{.ID}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if active.stdout.strip():
        raise ValueError("FastSurfer is busy with another pilot/job. Retry after it finishes.")
    if shutil.disk_usage(output.parent).free < 4 * 1024**3:
        raise ValueError("Insufficient local disk headroom for native anatomy processing")
    inspected = subprocess.run(
        ["docker", "image", "inspect", cfg["image"], "--format", "{{json .RepoDigests}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    digests = json.loads(inspected.stdout)
    if not digests:
        raise ValueError("Pinned official image must be pulled explicitly before analysis")
    visits, artifacts = [], {}
    output.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(inputs):
        source = Path(item["mri_path"])
        if sha256(source) != item["source_sha256"]:
            raise ValueError("MRI changed since anatomy enqueue")
        progress(10 + index * 70 // len(inputs), "Native T1 segmentation (not the 64-cube proxy)")
        scan_id = f"scan_{index}"
        outcome = run_scan(
            cfg, {"scan_id": scan_id, "patient_id": patient_id, "source_mri_path": str(source)}, digests[0]
        )
        if outcome["status"] != "completed":
            raise ValueError("FastSurfer failed; inspect the private execution log")
        directory = output / "fastsurfer" / scan_id
        seg = directory / "mri/aparc.DKTatlas+aseg.deep.mgz"
        stats = directory / STATS_RELATIVE
        processing = json.loads((directory / "processing.json").read_text())
        if (
            processing.get("status") != "completed"
            or processing.get("version") != cfg["version"]
            or processing.get("digest") != digests[0]
            or processing.get("scan_id") != scan_id
            or processing.get("patient_id") != patient_id
            or processing.get("source_sha256") != item["source_sha256"]
            or processing.get("output_sha256", {}).get(STATS_RELATIVE) != sha256(stats)
            or processing.get("output_sha256", {}).get("mri/aparc.DKTatlas+aseg.deep.mgz") != sha256(seg)
        ):
            raise ValueError("FastSurfer provenance does not match pinned native outputs")
        volumes = parse_stats(stats, REGIONS)
        masks = output / f"visit_{index}"
        mask_volumes = export_masks(
            source, seg, masks, source_units_verified=item.get("source_units_verified", False)
        )
        observed = item.get("metadata", {})
        etiv = etiv_mm3(observed.get("eTIV")) if item.get("etiv_unit") == "cm3" else None
        progress(
            10 + index * 70 // len(inputs) + 35 // len(inputs), "AVRA alignment and MTA/Koedam estimation"
        )
        ratings = run_rating(
            source,
            output / f"rating_{index}",
            rating_runtime,
            allow_unreviewed_research=automatic_research_values,
        )
        visit = AnatomyVisit(
            visit_id=item["visit_id"],
            days_from_baseline=item["days_from_baseline"],
            qc="automated_checks_only" if automatic_research_values else "pending_review",
            source_sha256=item["source_sha256"],
            segmentation_sha256=sha256(seg),
            statistics_sha256=sha256(stats),
            container_digest=digests[0],
            fastsurfer_version=cfg["version"],
            method=f"FastSurfer-{cfg['version']}-native-T1",
            volumes_mm3=volumes,
            mask_volumes_mm3=mask_volumes,
            etiv_mm3=etiv,
            head_size_ratios={k: v / etiv for k, v in volumes.items()} if etiv else {},
            hippocampal_asymmetry_percent=asymmetry(
                volumes["hippocampus_left_mm3"], volumes["hippocampus_right_mm3"]
            ),
            observed_metadata=observed,
            ratings=ratings,
        )
        visits.append(visit)
        files = [
            masks / "regions.nii.gz",
            masks / "segmentation.nii.gz",
            *(masks / f"{name}.nii.gz" for name in REGIONS),
        ]
        artifacts[item["visit_id"]] = {
            p.stem.removesuffix(".nii"): {
                "relative_path": p.relative_to(output).as_posix(),
                "sha256": sha256(p),
            }
            for p in files
        }
    write_json(output / "anatomy-artifacts.json", {"version": VERSION, "visits": artifacts})
    anatomy = AnatomyResult(
        visits=visits,
        changes=changes(visits),
        forecast=StructuralForecast(
            cutoff_visit_id=visits[-1].visit_id,
            interval_days=inputs[-1]["future_interval_days"],
            warnings=[
                "Reviewed longitudinal training/evaluation anatomy is not ready.",
                "No evaluated score-conditioned structural or spatial predictor exists; future geometry is incomplete.",
                "No-change/trend comparisons are offline baselines, not serving fallbacks.",
            ],
        ),
    )
    return ProgressionResult(
        patient_id=patient_id,
        visit_ids=[v.visit_id for v in visits],
        risk_scores=[],
        biomarkers={},
        selected_visit=visits[-1].visit_id,
        output_mode="anatomy",
        model_version=VERSION,
        days_from_baseline=[v.days_from_baseline for v in visits],
        anatomy=anatomy,
        caveats=[
            (
                "Measured anatomy uses automated checks only; visual segmentation and alignment review were skipped by research policy."
                if automatic_research_values
                else "Measured anatomy is pending visual segmentation QC; automated checks are not approval."
            ),
            "Scalar volumes are not registered tissue movement. Thickness and future anatomy unavailable.",
            (
                f"MTA/Koedam values use {AUTOMATIC_RESEARCH_RATING_POLICY}; alignment and rating agreement are unreviewed."
                if automatic_research_values
                else "Automatic ratings unavailable until AVRA preprocessing/runtime and alignment QC are verified."
            ),
            "Research estimates only; not a medical diagnosis or clinical validation.",
        ],
    )
