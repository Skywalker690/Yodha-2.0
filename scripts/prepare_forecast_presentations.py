"""Create scalar-bounded presentation variants without changing raw forecasts."""

import argparse
import copy
import json
import os
import shutil
import time
from pathlib import Path

import nibabel as nib

from backend.app.db.session import SessionLocal
from backend.app.models import Analysis
from backend.app.services.compute import gpu_slot
from backend.app.services.storage import resolve_key
from ml.anatomy.contracts import ForecastArtifact
from ml.anatomy.hippocampus_display import hippocampus_display
from ml.anatomy.integrity import checked_file, measurement_files
from ml.anatomy.study import physical_source
from ml.contracts import ProgressionResult
from src.common import sha256, write_json

POLICY = "scalar-guided hippocampus illustration; local MRI/label warp; acquired head unchanged; not a spatial model prediction or diagnosis"


def prepare(analysis_id: str) -> dict:
    """Append a new completed variant; keep prior result and artifacts immutable."""
    with gpu_slot(wait=True):
        with SessionLocal() as db:
            original = db.get(Analysis, analysis_id)
            if not original or original.status != "completed" or original.output_mode != "anatomy":
                raise ValueError("Completed anatomy forecast required")
            result = ProgressionResult.model_validate(original.result_json)
            forecast = result.anatomy.forecast
            if not forecast.experimental or forecast.status != "available":
                raise ValueError("Only explicit experimental forecasts have presentation variants")
            original_root = resolve_key(f"derived/{original.id}")
            manifest = json.loads((original_root / "future/future-artifacts.json").read_text())
            if (
                manifest["model_sha256"] != forecast.model_sha256
                or manifest["release_sha256"] != forecast.release_sha256
                or manifest["cutoff_visit_id"] != forecast.cutoff_visit_id
                or manifest["interval_days"] != forecast.interval_days
                or manifest["source_sha256"] != [v.source_sha256 for v in result.anatomy.visits]
            ):
                raise ValueError("Raw forecast metadata changed")
            for artifact in forecast.artifacts:
                entry = manifest["artifacts"][artifact.name]
                if entry["sha256"] != artifact.sha256 or entry["kind"] != artifact.kind:
                    raise ValueError("Raw forecast artifact changed")
                checked_file(original_root / "future", entry)
            cutoff = result.anatomy.visits[-1]
            if cutoff.visit_id != forecast.cutoff_visit_id:
                raise ValueError("Forecast cutoff must be the last observed input")
            snapshot = original.input_json[-1]
            mri_path = resolve_key(snapshot["mri_key"])
            files = measurement_files(original_root, original.patient_id,
                len(result.anatomy.visits) - 1, cutoff, mri_path)
            inputs = copy.deepcopy(original.input_json)
            inputs[-1]["presentation_parent_id"] = original.id
            variant = Analysis(patient_id=original.patient_id, visit_id=original.visit_id,
                output_mode="anatomy", model_version=original.model_version, input_json=inputs,
                status="processing", stage="Local hippocampus illustration", progress=20)
            db.add(variant)
            db.commit()
            variant_id = variant.id
        try:
            root = resolve_key(f"derived/{variant_id}")
            # Immutable raw files may share local disk blocks. The edited manifest
            # is excluded; writing it must never modify the original manifest.
            shutil.copytree(original_root, root, copy_function=os.link,
                ignore=shutil.ignore_patterns("future-artifacts.json", "*_display.nii.gz"))
            source = physical_source(mri_path, verified_units=snapshot.get("source_units_verified", False))
            mri, labels, field, display_metadata = hippocampus_display(
                source, nib.load(files["segmentation"]), cutoff.volumes_mm3, forecast.volumes_mm3,
            )
            forecast.artifacts = [a for a in forecast.artifacts if not a.name.endswith("_display")]
            manifest["artifacts"] = {k: v for k, v in manifest["artifacts"].items() if not k.endswith("_display")}
            for name, image, kind in (
                ("mri_display", mri, "mri"), ("labels_display", labels, "labels"),
                ("pull_display", field, "field"),
            ):
                destination = root / "future" / f"{name}.nii.gz"
                nib.save(image, destination)
                digest = sha256(destination)
                manifest["artifacts"][name] = {"relative_path": destination.name, "sha256": digest, "kind": kind}
                forecast.artifacts.append(ForecastArtifact(name=name, kind=kind, sha256=digest))
            forecast.display_magnification = 1
            forecast.display_mode = "hippocampus_scalar"
            forecast.display_regions = display_metadata["regions"]
            forecast.warnings.append(POLICY)
            manifest.update(display_magnification=1, display_mode="hippocampus_scalar",
                display_policy=POLICY, display_metadata=display_metadata, presentation_parent_id=analysis_id)
            write_json(root / "future/future-artifacts.json", manifest)
            validated = ProgressionResult.model_validate(result.model_dump())
            with SessionLocal() as db:
                job = db.get(Analysis, variant_id)
                job.result_json = validated.model_dump()
                job.status, job.progress, job.stage = "completed", 100, "Presentation ready"
                db.commit()
            return {"original_id": analysis_id, "analysis_id": variant_id,
                "interval": forecast.interval_days, "display": display_metadata, "status": "completed"}
        except BaseException:
            with SessionLocal() as db:
                job = db.get(Analysis, variant_id)
                job.status, job.stage = "failed", "Presentation unavailable"
                job.error = "Presentation preparation failed; original forecast is preserved."
                db.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print("Waiting for the raw annual batch", flush=True)
    while True:
        try:
            report = json.loads(args.batch_report.read_text())
        except json.JSONDecodeError:
            time.sleep(1)
            continue
        jobs = report["jobs"]
        if len(jobs) == 15 and all(j["status"] not in {"queued", "processing"} for j in jobs):
            break
        time.sleep(10)
    outcomes = []
    for item in jobs:
        if item["status"] != "completed":
            continue
        outcome = {"code": item["code"], **prepare(item["job_id"])}
        outcomes.append(outcome)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"policy": POLICY, "jobs": outcomes}, indent=2), encoding="utf-8")
        print(json.dumps(outcome), flush=True)


if __name__ == "__main__":
    main()
