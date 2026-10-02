"""Immutable cutoff-local examples. Future MRI/labels are targets, never features."""

import csv
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk

from ml.anatomy.contracts import AnatomyVisit
from ml.anatomy.integrity import checked_file
from ml.anatomy.model import image_channels
from ml.anatomy.registration import (
    VERSION as REGISTRATION_VERSION,
    learning_grid,
    nifti,
    normalize,
    resample,
    rigid,
    target_pull,
)
from ml.anatomy.structural import StructuralExample, history_features
from src.common import sha256, write_json
from src.fastsurfer.regions import REGIONS

VERSION = "anatomy-study-v1"


def frozen_split(path: Path) -> dict[str, str]:
    split: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            subject, role = row["subject_id"], row["split"]
            if (
                not subject
                or role not in {"train", "validation", "selection", "calibration", "test"}
                or split.get(subject, role) != role
            ):
                raise ValueError("Invalid/inconsistent frozen subject split")
            split[subject] = role
    counts = {r: list(split.values()).count(r) for r in set(split.values())}
    if counts not in (
        {"train": 40, "validation": 8, "test": 8},
        {"train": 44, "selection": 4, "calibration": 4, "test": 4},
    ):
        raise ValueError("A complete frozen historic or scan-count anatomy study is required")
    return split


def physical_source(path: Path, *, verified_units: bool) -> nib.Nifti1Image:
    image = nib.load(path)
    if image.header.get_xyzt_units()[0] == "unknown" and verified_units:
        image = nifti(np.asarray(image.dataobj), image.affine)
    if image.header.get_xyzt_units()[0] != "mm":
        raise ValueError("MRI millimetre units require verified source provenance")
    return image


def cutoff_inputs(
    images: list[nib.Nifti1Image], labels: nib.Nifti1Image, days: list[int], size: int
) -> tuple[np.ndarray, nib.Nifti1Image, nib.Nifti1Image, list[dict]]:
    """All observed history is registered only to the latest observed MRI."""
    if not 2 <= len(images) <= 5 or len(images) != len(days) or any(b <= a for a, b in zip(days, days[1:])):
        raise ValueError("Chronological observed image history required")
    current = learning_grid(images[-1], size)
    categorical = resample(labels, current, sitk.Transform(3, sitk.sitkIdentity), categorical=True)
    aligned, provenance = [], []
    for image in images[:-1]:
        transform, metadata = rigid(current, image)
        aligned.append(resample(image, current, transform, categorical=False))
        provenance.append(metadata)
    channels = image_channels(current, aligned[-1], categorical, days[-1] - days[-2])
    # Voxel-wise OLS intensity trend uses ALL earlier observed MRIs, not future scans.
    times = (np.asarray(days, dtype=float) - days[-1]) / 365.25
    weights = (times - times.mean()) / np.sum((times - times.mean()) ** 2)
    channels[1] = sum(
        weight * np.asarray(normalize(image).dataobj) for weight, image in zip(weights, [*aligned, current])
    )
    return channels, current, categorical, provenance


def prepare_case(
    history: list[dict],
    target: dict,
    output: Path,
    size: int = 96,
    *,
    allow_unreviewed_research: bool = False,
) -> dict:
    visits = [AnatomyVisit.model_validate(item["measurement"]) for item in history]
    later_visit = AnatomyVisit.model_validate(target["measurement"])
    example = StructuralExample(history[-1]["subject_id"], visits, later_visit, allow_unreviewed_research)
    interval = example.interval_days
    history_features(visits, interval, True, require_review=not allow_unreviewed_research)
    if any(item["subject_id"] != example.subject_id for item in [*history, target]):
        raise ValueError("Mixed-subject anatomy history")
    for item in [*history, target]:
        if (
            sha256(Path(item["mri_path"])) != item["measurement"]["source_sha256"]
            or sha256(Path(item["labels_path"])) != item["labels_sha256"]
        ):
            raise ValueError("Exported MRI/segmentation changed")
    images = [
        physical_source(Path(item["mri_path"]), verified_units=item["source_units_verified"])
        for item in history
    ]
    labels = nib.load(history[-1]["labels_path"])
    channels, current, categorical, input_registration = cutoff_inputs(
        images, labels, [v.days_from_baseline for v in visits], size
    )
    # From here onward, hidden later data constructs ONLY the supervision target.
    later = physical_source(Path(target["mri_path"]), verified_units=target["source_units_verified"])
    transform, target_registration = rigid(current, later)
    aligned_later = resample(later, current, transform, categorical=False)
    later_labels = resample(nib.load(target["labels_path"]), current, transform, categorical=True)
    field_image, deformation_metadata = target_pull(current, aligned_later)
    field = np.asarray(field_image.dataobj)
    current_labels, target_labels = np.asarray(categorical.dataobj), np.asarray(later_labels.dataobj)
    identifiers = [v[0] for _, v in sorted(REGIONS.items())]
    before = np.array([(current_labels == key).sum() for key in identifiers])
    after = np.array([(target_labels == key).sum() for key in identifiers])
    if np.any(before <= 0) or np.any(after <= 0):
        raise ValueError("A region disappeared on the learning grid; increase resolution")
    output.mkdir(parents=True, exist_ok=False)
    tensor = output / "example.npz"
    np.savez_compressed(
        tensor,
        images=channels,
        affine=current.affine.astype(np.float32),
        labels=current_labels.astype(np.int16),
        target_labels=target_labels.astype(np.int16),
        later=np.asarray(normalize(aligned_later).dataobj)[None].astype(np.float32),
        target_field=field.transpose(3, 0, 1, 2),
        target_ratios=(after / before).astype(np.float32),
    )
    for name, image in (
        ("cutoff", current),
        ("later-target-only", aligned_later),
        ("cutoff-labels", categorical),
        ("later-labels-target-only", later_labels),
    ):
        nib.save(image, output / f"{name}.nii.gz")
    nib.save(field_image, output / "target-pull-mm.nii.gz")
    sitk.WriteTransform(transform, str(output / "later-rigid.tfm"))
    artifacts = {
        path.name: {"relative_path": path.name, "sha256": sha256(path)}
        for path in output.iterdir()
        if path.is_file()
    }
    case = {
        "version": VERSION,
        "subject_id": example.subject_id,
        "history": [v.model_dump() for v in visits],
        "target": later_visit.model_dump(),
        "source_records": [*history, target],
        "interval_days": interval,
        "registration_version": REGISTRATION_VERSION,
        "input_registration": input_registration,
        "target_registration": target_registration,
        "target_deformation": deformation_metadata,
        "artifacts": artifacts,
        "registration_qc": "pending_review",
        "allow_unreviewed_research": allow_unreviewed_research,
        "reviewer_id": None,
        "reviewed_at": None,
    }
    write_json(output / "case.json", case)
    return case


def load_case(
    path: Path, *, require_review: bool = True
) -> tuple[dict, StructuralExample, dict[str, np.ndarray]]:
    case = json.loads(path.read_text())
    if case["version"] != VERSION or case["registration_version"] != REGISTRATION_VERSION:
        raise ValueError("Unsupported study/registration schema")
    if require_review and (
        case["registration_qc"] != "passed" or not case.get("reviewer_id") or not case.get("reviewed_at")
    ):
        raise ValueError("Human longitudinal registration QC is required")
    for entry in case["artifacts"].values():
        checked_file(path.parent, entry)
    example = StructuralExample(
        case["subject_id"],
        [AnatomyVisit.model_validate(v) for v in case["history"]],
        AnatomyVisit.model_validate(case["target"]),
        case.get("allow_unreviewed_research", False),
    )
    if example.interval_days != case["interval_days"]:
        raise ValueError("Case cutoff/target changed")
    history_features(
        example.history, example.interval_days, True, require_review=not example.allow_unreviewed_research
    )
    with np.load(checked_file(path.parent, case["artifacts"]["example.npz"]), allow_pickle=False) as arrays:
        data = {name: arrays[name].copy() for name in arrays.files}
    size = data["images"].shape[1:]
    if (
        len(size) != 3
        or min(size) < 16
        or max(size) > 128
        or data["images"].shape != (6, *size)
        or data["target_field"].shape != (3, *size)
        or data["later"].shape != (1, *size)
        or any(data[key].shape != size for key in ("labels", "target_labels"))
        or data["affine"].shape != (4, 4)
        or data["target_ratios"].shape != (len(REGIONS),)
        or not all(np.isfinite(v).all() for v in data.values())
    ):
        raise ValueError("Invalid bounded training arrays")
    return case, example, data
