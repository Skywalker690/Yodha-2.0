"""Final native-grid testing and promotion. Never selects a model using test labels."""

import json
from datetime import datetime, timezone
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk

from ml.anatomy.evaluation import geometry_metrics
from ml.anatomy.forecasting import RELEASE_VERSION, generate, verify_candidate
from ml.anatomy.registration import resample
from ml.anatomy.study import load_case
from src.common import sha256, write_json


def evaluate_native(study: Path, directory: Path) -> dict:
    from ml.anatomy.training import checked_case

    manifest = json.loads(study.read_text())
    report = json.loads((directory / "evaluation.json").read_text())
    if sha256(study) != report["study_sha256"] or manifest["synthetic"] != report["synthetic"]:
        raise ValueError("Study changed after training")
    verify_candidate(directory, report)
    destination = directory / "native-test"
    if destination.exists():
        raise ValueError("Final native test is immutable; do not repeatedly tune against it")
    destination.mkdir()
    cases, failures = [], []
    for index, entry in enumerate(manifest["cases"]):
        path = checked_case(study.parent, entry)
        unreviewed = report.get("allow_unreviewed_research", False)
        case, example, _ = load_case(path, require_review=not unreviewed)
        if report["roles"][example.subject_id] != "test":
            continue
        try:
            records = case["source_records"]
            inputs = [{**r, "visit_id": r["measurement"]["visit_id"]} for r in records[:-1]]
            artifacts = generate(
                directory,
                example.subject_id,
                example.history,
                inputs,
                example.interval_days,
                destination / str(index),
                allow_unreviewed_research=unreviewed,
            )
            current = nib.load(inputs[-1]["labels_path"])
            target_record = records[-1]
            if sha256(Path(target_record["labels_path"])) != target_record["labels_sha256"]:
                raise ValueError("Hidden target changed")
            target = resample(
                nib.load(target_record["labels_path"]),
                current,
                sitk.ReadTransform(str(path.parent / "later-rigid.tfm")),
                categorical=True,
            )
            metrics = geometry_metrics(nib.load(destination / str(index) / "labels.nii.gz"), target)
            baseline = geometry_metrics(current, target)
            # Exercise the exact same zero-time production path and mesh gates.
            zero = generate(
                directory,
                example.subject_id,
                example.history,
                inputs,
                0,
                destination / f"{index}-zero",
                allow_unreviewed_research=unreviewed,
            )
            if not np.array_equal(
                np.asarray(nib.load(destination / f"{index}-zero" / "labels.nii.gz").dataobj),
                np.asarray(current.dataobj),
            ):
                raise ValueError("Zero-time categorical identity failed")
            if not np.allclose(
                np.asarray(nib.load(destination / f"{index}-zero" / "mri.nii.gz").dataobj),
                np.asarray(nib.load(inputs[-1]["mri_path"]).dataobj),
                rtol=1e-6,
                atol=1e-5,
            ):
                raise ValueError("Zero-time MRI intensity identity failed")
            cases.append(
                {
                    "subject_id": example.subject_id,
                    "interval_days": example.interval_days,
                    "metrics": metrics,
                    "no_change": baseline,
                    "minimum_jacobian": artifacts["minimum_jacobian"],
                    "zero_minimum_jacobian": zero["minimum_jacobian"],
                    "artifact_manifest_sha256": sha256(destination / str(index) / "future-artifacts.json"),
                }
            )
        except (ValueError, OSError, RuntimeError) as exc:
            failures.append({"subject_id": example.subject_id, "case": index, "reason": str(exc)})
    by_subject = {}
    for subject in {c["subject_id"] for c in cases}:
        rows = [v for c in cases if c["subject_id"] == subject for v in c["metrics"].values()]
        by_subject[subject] = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
    mean = (
        {k: float(np.mean([r[k] for r in by_subject.values()])) for k in next(iter(by_subject.values()))}
        if by_subject
        else None
    )
    passed = (
        bool(cases)
        and not failures
        and mean["dice"] >= report["gates"]["minimum_mean_dice"]
        and mean["assd_mm"] <= report["gates"]["maximum_mean_assd_mm"]
    )
    report["native"] = {
        "status": "passed" if passed else "failed",
        "cases": cases,
        "failures": failures,
        "mean_subject_balanced": mean,
        "coordinate_units": "mm",
        "zero_time_tested": bool(cases),
    }
    write_json(directory / "evaluation.json", report)
    write_json(
        directory / "status.json",
        {
            "stage": "candidate_evaluated",
            "synthetic": report["synthetic"],
            "native_status": report["native"]["status"],
            "release_failures": report["release_failures"],
        },
    )
    return report


def promote(directory: Path) -> dict:
    report = json.loads((directory / "evaluation.json").read_text())
    if (
        report["synthetic"] is not False
        or report.get("review_complete") is not True
        or report["release_failures"]
        or report["native"]["status"] != "passed"
    ):
        raise ValueError("Cannot promote: real-data scientific and native artifact gates are incomplete")
    verify_candidate(directory, report)
    if (directory / "release.json").exists():
        raise ValueError("Release is immutable")
    result = {
        "version": RELEASE_VERSION,
        "status": "promoted",
        "synthetic": False,
        "released_at": datetime.now(timezone.utc).isoformat(),
        "clinical_validation": False,
        "supported_intervals_days": report["supported_intervals_days"],
        "measurement_method": "FastSurfer-2.5.4-native-T1",
        "dictionary_version": "dkt-longitudinal-v1",
        "score_method": "AVRA-v0.8-ensemble-continuous",
        "files": {
            key: {"relative_path": filename, "sha256": sha256(directory / filename)}
            for key, filename in (
                ("spatial", "with_scores.pt"),
                ("structural", "with_scores.json"),
                ("evaluation", "evaluation.json"),
            )
        },
    }
    write_json(directory / "release.json", result)
    return result
