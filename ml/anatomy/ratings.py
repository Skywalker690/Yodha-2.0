"""AVRA candidate availability and output validation; never volume-derived scores."""

import csv
import importlib.util
import shutil
import sys
import json
import re
import subprocess
from uuid import uuid4
from pathlib import Path

from ml.anatomy.contracts import RatingEstimate
from src.common import sha256, write_json


def readiness() -> RatingEstimate:
    warnings = []
    if sys.platform == "win32":
        warnings.append("AVRA upstream requires a Linux/macOS FSL runtime; native Windows is unsupported.")
    if shutil.which("flirt") is None:
        warnings.append("FSL FLIRT and its MNI template are unavailable; AC-PC alignment cannot run.")
    for name in ("nipype", "h5py"):
        if importlib.util.find_spec(name) is None:
            warnings.append(f"AVRA dependency {name} is unavailable.")
    warnings.extend(
        [
            "Released AVRA v0.8 weights exist upstream but are not installed/pinned in a verified local rating runtime.",
            "Alignment quality gate and checkpoint compatibility have not been validated locally.",
            "Released PA combines axial, coronal and sagittal stacks into one posterior estimate, not left/right outputs.",
        ]
    )
    return RatingEstimate(warnings=warnings)


def parse_avra_csv(path: Path, *, alignment_verified: bool = False) -> RatingEstimate:
    """Preserve continuous means, reject invalid ranges; no clipping or integer rounding."""
    if not alignment_verified:
        return RatingEstimate(
            status="pending_alignment_qc",
            warnings=["AC-PC alignment has not passed verified quality checks."],
        )
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1:
            raise ValueError("Exactly one case expected")
        row = rows[0]
        return RatingEstimate(
            status="ok",
            method="AVRA-v0.8-ensemble-continuous",
            mta_left=float(row["mta_left_mean"]),
            mta_right=float(row["mta_right_mean"]),
            posterior_atrophy=float(row["pa_mean"]),
            warnings=["Automatic model estimates; rating agreement is unverified on this dataset."],
        )
    except (ValueError, KeyError, OSError):
        return RatingEstimate(
            status="invalid", warnings=["AVRA returned missing, nonfinite or out-of-scale outputs."]
        )


def run_rating(source: Path, output: Path, runtime_manifest: Path | None = None) -> RatingEstimate:
    """Execute the upstream scorer in a pinned Linux runtime with private read-only inputs.

    Scoring is automatic. Alignment QC is an independent prerequisite, not a patient
    scoring input. Failed or unchecked alignment cannot expose numerical estimates.
    The manifest is local operator configuration, never an uploaded patient field.
    """
    if runtime_manifest is None:
        return readiness()
    try:
        runtime = json.loads(runtime_manifest.read_text(encoding="utf-8"))
        image = runtime["image"]
        if not re.fullmatch(r"(?:[^\s@]+@)?sha256:[a-f0-9]{64}", image):
            raise ValueError("AVRA runtime requires a registry digest")
        weights = Path(runtime["weights_dir"]).resolve()
        expected = runtime["weights_sha256"]
        if not expected or not all(
            any(name.startswith(scale + "/") for name in expected) for scale in ("mta", "pa", "gca-f")
        ):
            raise ValueError("The upstream AVRA ensemble requires all released scale checkpoints")
        for name, fingerprint in expected.items():
            path = (weights / name).resolve()
            if (
                not path.is_relative_to(weights)
                or not path.is_file()
                or not re.fullmatch(r"[a-f0-9]{64}", fingerprint)
                or sha256(path) != fingerprint
            ):
                raise ValueError("AVRA checkpoint changed")
        if source.suffixes[-2:] != [".nii", ".gz"] and source.suffix != ".nii":
            raise ValueError("AVRA requires an original NIfTI T1 volume")
        output.mkdir(parents=True, exist_ok=True)
        if (output / "rating.csv").exists():
            raise ValueError("An AVRA attempt is immutable; use a new analysis directory")
        container_name = "yodha-avra-" + uuid4().hex
        command = [
            "docker",
            "run",
            "--name",
            container_name,
            "--rm",
            "--network",
            "none",
            "--user",
            "1000:1000",
            "--mount",
            f"type=bind,source={source.resolve().parent},target=/input,readonly",
            "--mount",
            f"type=bind,source={weights},target=/weights,readonly",
            "--mount",
            f"type=bind,source={output.resolve()},target=/output",
            "--entrypoint",
            "python",
            image,
            "/opt/avra/avra.py",
            "--input-file",
            f"/input/{source.name}",
            "--model-dir",
            "/weights",
            "--output-dir",
            "/output",
            "--uid",
            "rating",
        ]
        with (output / "execution.log").open("w", encoding="utf-8") as stream:
            try:
                subprocess.run(command, check=True, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
            except subprocess.TimeoutExpired:
                subprocess.run(
                    ["docker", "stop", "--time", "5", container_name],
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=15,
                    check=False,
                )
                raise
        aligned, matrix, csv_path = (
            output / "rating_mni_dof_6.nii",
            output / "rating_mni_dof_6.mat",
            output / "rating.csv",
        )
        import nibabel as nib
        import numpy as np
        from ml.anatomy.masks import geometry

        geometry(nib.load(aligned))
        transform = np.loadtxt(matrix)
        if transform.shape != (4, 4) or not np.isfinite(transform).all():
            raise ValueError("Invalid AVRA alignment transform")
        # Positive determinant is necessary but is not evidence of AC-PC anatomical quality.
        if np.linalg.det(transform[:3, :3]) <= 0:
            raise ValueError("AVRA alignment reflected anatomy")
        provenance = {
            "method": "AVRA-v0.8-upstream",
            "runtime_digest": image,
            "source_sha256": sha256(source),
            "aligned_sha256": sha256(aligned),
            "matrix_sha256": sha256(matrix),
            "csv_sha256": sha256(csv_path),
            "weights_sha256": expected,
            "alignment_qc": "pending_review",
        }
        write_json(output / "provenance.json", provenance)
        # Upstream's own diagonal test cannot establish registration quality.
        return parse_avra_csv(csv_path, alignment_verified=False)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return RatingEstimate(
            status="invalid",
            warnings=[
                "AVRA runtime, pinned checkpoints, preprocessing or alignment failed; inspect the private rating log."
            ],
        )
