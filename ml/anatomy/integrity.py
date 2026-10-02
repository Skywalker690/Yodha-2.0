"""Shared integrity checks for reviewed, analysis-owned measurements and ratings."""

import json
from pathlib import Path

from ml.anatomy.contracts import AnatomyVisit, VERSION
from src.common import sha256
from src.fastsurfer.regions import REGIONS


def checked_file(root: Path, entry: dict) -> Path:
    relative = Path(entry["relative_path"])
    path = (root / relative).resolve()
    if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact escapes its owned directory")
    if not path.is_file() or sha256(path) != entry["sha256"]:
        raise ValueError("Artifact content changed")
    return path


def measurement_files(
    root: Path, patient_id: str, index: int, visit: AnatomyVisit, source: Path
) -> dict[str, Path]:
    if sha256(source) != visit.source_sha256:
        raise ValueError("Reviewed raw MRI changed")
    scan = root / f"fastsurfer/scan_{index}"
    processing = json.loads((scan / "processing.json").read_text())
    expected = {
        "stats/aseg+DKT.VINN.stats": visit.statistics_sha256,
        "mri/aparc.DKTatlas+aseg.deep.mgz": visit.segmentation_sha256,
    }
    if (
        processing.get("status") != "completed"
        or processing.get("version") != visit.fastsurfer_version
        or processing.get("digest") != visit.container_digest
        or processing.get("scan_id") != f"scan_{index}"
        or processing.get("patient_id") != patient_id
        or processing.get("source_sha256") != visit.source_sha256
        or any(
            processing.get("output_sha256", {}).get(key) != digest or sha256(scan / key) != digest
            for key, digest in expected.items()
        )
    ):
        raise ValueError("Native measurement provenance changed")
    manifest = json.loads((root / "anatomy-artifacts.json").read_text())
    entries = manifest["visits"][visit.visit_id]
    if manifest.get("version") != VERSION or set(entries) != {"regions", "segmentation", *REGIONS}:
        raise ValueError("Incomplete measurement artifact manifest")
    if any(entry["relative_path"] != f"visit_{index}/{name}.nii.gz" for name, entry in entries.items()):
        raise ValueError("Unexpected measurement artifact path")
    return {name: checked_file(root, entry) for name, entry in entries.items()}


def rating_files(root: Path, index: int, visit: AnatomyVisit, *, reviewed: bool = False) -> dict:
    directory = root / f"rating_{index}"
    if (
        visit.ratings.provenance_sha256
        and sha256(directory / "provenance.json") != visit.ratings.provenance_sha256
    ):
        raise ValueError("Rating provenance changed")
    provenance = json.loads((directory / "provenance.json").read_text())
    if provenance["source_sha256"] != visit.source_sha256 or provenance["method"] != "AVRA-v0.8-upstream":
        raise ValueError("Rating source changed")
    for key, filename in (
        ("aligned", "rating_mni_dof_6.nii"),
        ("matrix", "rating_mni_dof_6.mat"),
        ("csv", "rating.csv"),
    ):
        if sha256(directory / filename) != provenance[key + "_sha256"]:
            raise ValueError("Rating/alignment content changed")
    if not provenance.get("runtime_digest") or not provenance.get("weights_sha256"):
        raise ValueError("Unpinned automatic rating")
    if reviewed and (
        provenance.get("alignment_qc") != "passed"
        or not provenance.get("reviewer_id")
        or not provenance.get("reviewed_at")
    ):
        raise ValueError("Automatic rating alignment is not reviewed")
    return provenance
