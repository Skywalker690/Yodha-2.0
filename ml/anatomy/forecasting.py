"""Real native artifact generation and serving only from a hash-bound evaluated release."""

import json
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from nibabel.processing import resample_from_to

from ml.anatomy.contracts import AnatomyVisit, ForecastArtifact, StructuralForecast
from ml.anatomy.integrity import checked_file
from ml.anatomy.model import FeatureScaler, SpatialPredictor, VERSION
from ml.anatomy.registration import VERSION as REGISTRATION_VERSION, nifti
from ml.anatomy.spatial import jacobians, mesh, warp
from ml.anatomy.structural import RegularizedMixedEffects, history_features
from ml.anatomy.study import cutoff_inputs, physical_source
from src.common import sha256, write_json
from src.fastsurfer.regions import REGIONS

RELEASE_VERSION = "anatomy-research-release-v2-score-conditioned"


def load_models(
    directory: Path, *, with_scores: bool = True
) -> tuple[SpatialPredictor, FeatureScaler, dict, RegularizedMixedEffects]:
    name = "with_scores" if with_scores else "without_scores"
    checkpoint = torch.load(directory / f"{name}.pt", map_location="cpu", weights_only=True)
    if (
        checkpoint["version"] != VERSION
        or checkpoint["with_scores"] is not with_scores
        or not 16 <= checkpoint["grid_size"] <= 128
    ):
        raise ValueError("Invalid score-conditioned spatial checkpoint")
    scaler = FeatureScaler.from_dict(checkpoint["scaler"])
    if len(checkpoint["feature_names"]) != len(scaler.median):
        raise ValueError("Saved conditioning schema changed")
    model = SpatialPredictor(len(scaler.median) * 2)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    structural = RegularizedMixedEffects.from_dict(json.loads((directory / f"{name}.json").read_text()))
    if structural.with_scores is not with_scores or structural.feature_names != checkpoint["feature_names"]:
        raise ValueError("Scalar/spatial feature schemas do not match")
    return model, scaler, checkpoint, structural


def native_field(field: np.ndarray, learning_affine: np.ndarray, source: nib.Nifti1Image) -> nib.Nifti1Image:
    # Resampling vectors does NOT rotate/scale them: they already represent RAS mm.
    components = [
        np.asarray(
            resample_from_to(
                nifti(field[..., i], learning_affine), (source.shape, source.affine), order=1, mode="nearest"
            ).dataobj,
            dtype=np.float32,
        )
        for i in range(3)
    ]
    result = nifti(np.stack(components, axis=-1), source.affine)
    result.header.set_intent("vector")
    return result


def generate(
    directory: Path,
    subject_id: str,
    history: list[AnatomyVisit],
    sources: list[dict],
    interval: int,
    output: Path,
    *,
    with_scores: bool = True,
    allow_unreviewed_research: bool = False,
) -> dict:
    """Shared serving/evaluation path. Never receives a later MRI or target features."""
    if len(history) != len(sources) or not 2 <= len(history) <= 5 or not 0 <= interval <= 3650:
        raise ValueError("Bounded reviewed cutoff history required")
    for visit, record in zip(history, sources):
        if (
            record["visit_id"] != visit.visit_id
            or sha256(Path(record["mri_path"])) != visit.source_sha256
            or sha256(Path(record["labels_path"])) != record["labels_sha256"]
        ):
            raise ValueError("Cutoff MRI/labels changed")
    model, scaler, checkpoint, structural = load_models(directory, with_scores=with_scores)
    # zero-time is identity, but still requires the same verified inputs/release.
    row, names = history_features(
        history, max(interval, 1), with_scores, require_review=not allow_unreviewed_research
    )
    if names != checkpoint["feature_names"]:
        raise ValueError("Conditioning schema changed")
    images = [
        physical_source(Path(s["mri_path"]), verified_units=s["source_units_verified"]) for s in sources
    ]
    labels = nib.load(sources[-1]["labels_path"])
    if labels.shape != images[-1].shape or not np.allclose(labels.affine, images[-1].affine):
        raise ValueError("Native categorical grid does not match cutoff MRI")
    channels, current, _, registration = cutoff_inputs(
        images, labels, [v.days_from_baseline for v in history], checkpoint["grid_size"]
    )
    with torch.inference_mode():
        predicted = (
            model(
                torch.from_numpy(channels)[None],
                torch.from_numpy(scaler.transform(row))[None],
                torch.tensor([interval / 365.25], dtype=torch.float32),
            )[0]
            .numpy()
            .transpose(1, 2, 3, 0)
        )
    if interval == 0 and np.any(predicted):
        raise ValueError("Zero-time identity failed")
    field = native_field(predicted, current.affine, images[-1])
    predicted_mri = warp(images[-1], field, categorical=False)
    predicted_labels = warp(labels, field, categorical=True)
    data = np.asarray(predicted_labels.dataobj)
    before = np.asarray(labels.dataobj)
    volumes = (
        dict(history[-1].volumes_mm3)
        if interval == 0
        else structural.predict(
            subject_id, history, interval, allow_unreviewed_research=allow_unreviewed_research
        )
    )
    physical_volume = abs(float(np.linalg.det(labels.affine[:3, :3])))
    consistency = {}
    for region, (identifier, _) in REGIONS.items():
        if not np.any(before == identifier) or not np.any(data == identifier):
            raise ValueError("A required native region disappeared")
        ratio = (data == identifier).sum() / (before == identifier).sum()
        expected = volumes[region] / history[-1].volumes_mm3[region]
        consistency[region] = float(abs(ratio - expected))
    if max(consistency.values()) > 0.12:
        raise ValueError("Native mask/scalar relative-change agreement exceeds 12 percentage points")
    output.mkdir(parents=True, exist_ok=False)
    nib.save(predicted_mri, output / "mri.nii.gz")
    nib.save(predicted_labels, output / "labels.nii.gz")
    nib.save(field, output / "pull.nii.gz")
    # Keep independently retrievable categorical regional masks as well as labels.
    for region, (identifier, _) in REGIONS.items():
        nib.save(
            nifti((data == identifier).astype(np.uint8), labels.affine), output / f"{region}_mask.nii.gz"
        )
    meshes = {
        "brain_mesh": mesh(nifti((data > 0).astype(np.uint8), labels.affine), output / "brain_mesh.gii")
    }
    for region, (identifier, _) in REGIONS.items():
        meshes[region] = mesh(
            nifti((data == identifier).astype(np.uint8), labels.affine), output / f"{region}.gii"
        )
    artifacts = {
        p.stem.removesuffix(".nii"): {
            "relative_path": p.name,
            "sha256": sha256(p),
            "kind": "mesh"
            if p.suffix == ".gii"
            else "mri"
            if p.name == "mri.nii.gz"
            else "field"
            if p.name == "pull.nii.gz"
            else "labels",
        }
        for p in output.iterdir()
        if p.is_file()
    }
    manifest = {
        "version": VERSION,
        "registration_version": REGISTRATION_VERSION,
        "cutoff_visit_id": history[-1].visit_id,
        "interval_days": interval,
        "with_scores": with_scores,
        "allow_unreviewed_research": allow_unreviewed_research,
        "model_sha256": sha256(directory / ("with_scores.pt" if with_scores else "without_scores.pt")),
        "source_sha256": [v.source_sha256 for v in history],
        "feature_names": names,
        "score_method": [v.ratings.method for v in history],
        "registration": registration,
        "minimum_jacobian": float(jacobians(np.asarray(field.dataobj), field.affine).min()),
        "coverage": "complete; no extrapolation",
        "mesh_checks": meshes,
        "volume_change_discrepancy": consistency,
        "volumes_mm3": volumes,
        "native_mask_volumes_mm3": {
            r: float((data == identifier).sum() * physical_volume) for r, (identifier, _) in REGIONS.items()
        },
        "artifacts": artifacts,
    }
    write_json(output / "future-artifacts.json", manifest)
    return manifest


def release(directory: Path) -> tuple[dict, str]:
    path = directory / "release.json"
    data = json.loads(path.read_text())
    if data["version"] != RELEASE_VERSION or data["status"] != "promoted" or data["synthetic"] is not False:
        raise ValueError("No promoted real-data anatomy release")
    filenames = {
        "spatial": "with_scores.pt",
        "structural": "with_scores.json",
        "evaluation": "evaluation.json",
    }
    if set(data["files"]) != set(filenames):
        raise ValueError("Complete matched model release required")
    for key, filename in filenames.items():
        if data["files"][key]["relative_path"] != filename:
            raise ValueError("Release does not bind the actual inference files")
        checked_file(directory, data["files"][key])
    report = json.loads(checked_file(directory, data["files"]["evaluation"]).read_text())
    if (
        report["synthetic"] is not False
        or report.get("review_complete") is not True
        or report["release_failures"]
        or report["native"]["status"] != "passed"
        or data["supported_intervals_days"] != report["supported_intervals_days"]
        or not data["supported_intervals_days"]
    ):
        raise ValueError("Anatomy release gates are not satisfied")
    verify_candidate(directory, report)
    return data, sha256(path)


def verify_candidate(directory: Path, report: dict) -> None:
    """Bind evaluation to the exact frozen weights used for native validation."""
    expected = {"with_scores.pt", "with_scores.json"}
    if set(report.get("candidate_sha256", {})) != expected:
        raise ValueError("Evaluation is missing the frozen matched checkpoint fingerprints")
    if any(
        sha256(directory / filename) != fingerprint
        for filename, fingerprint in report["candidate_sha256"].items()
    ):
        raise ValueError("Model changed after evaluation; retraining requires a fresh run")


def predict(
    directory: Path,
    subject_id: str,
    history: list[AnatomyVisit],
    sources: list[dict],
    interval: int,
    output: Path,
    expected_release: str,
) -> StructuralForecast:
    metadata, release_hash = release(directory)
    if release_hash != expected_release or interval not in [0, *metadata["supported_intervals_days"]]:
        raise ValueError("Queued release changed or interval unsupported")
    if any(
        v.method != metadata["measurement_method"]
        or v.dictionary_version != metadata["dictionary_version"]
        or v.ratings.method != metadata["score_method"]
        for v in history
    ):
        raise ValueError("Measurement/rating methodology differs from evaluated training")
    manifest = generate(directory, subject_id, history, sources, interval, output)
    manifest["release_sha256"] = release_hash
    write_json(output / "future-artifacts.json", manifest)
    report = json.loads((directory / "evaluation.json").read_text())
    calibration = report["interval_calibration"] if interval > 0 else None
    bands, evidence = None, None
    if calibration:
        values = manifest["volumes_mm3"]
        candidate = {
            r: (values[r] - calibration["radius_mm3"][i], values[r] + calibration["radius_mm3"][i])
            for i, r in enumerate(sorted(values))
        }
        # Do not clip an invalid lower bound and imply calibrated physical coverage.
        if all(low > 0 for low, _ in candidate.values()):
            bands, evidence = (
                candidate,
                {
                    **report["interval_coverage"],
                    "level": calibration["level"],
                    "method": calibration["method"],
                    "calibration_subjects": calibration["calibration_subjects"],
                },
            )
    return StructuralForecast(
        status="available",
        cutoff_visit_id=history[-1].visit_id,
        interval_days=interval,
        warnings=[
            "Research structural estimates, not a medical diagnosis or clinical validation.",
            "Categorical mask-boundary meshes are not reconstructed cortical surfaces.",
        ],
        volumes_mm3=manifest["volumes_mm3"],
        prediction_intervals=bands,
        interval_evidence=evidence,
        spatial_model_version=VERSION,
        model_sha256=manifest["model_sha256"],
        release_sha256=release_hash,
        artifacts=[
            ForecastArtifact(name=name, kind=entry["kind"], sha256=entry["sha256"])
            for name, entry in manifest["artifacts"].items()
        ],
    )
