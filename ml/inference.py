from collections.abc import Callable
from pathlib import Path

import nibabel as nib
import numpy as np

from ml.contracts import MODEL_VERSION, ProgressionResult, VisitInput
from ml.encoder import extract_features
from ml.explainability import difference_overlay
from ml.preprocessing import prepare, slice_image
from ml.temporal_model import feature_delta_scores

CAVEATS = [
    "Research prototype. Not a medical diagnosis. Qualified review and independent validation are required.",
    "Progression-risk estimates are uncalibrated structural-change indices, not probabilities of Alzheimer's disease.",
    "Foreground fraction and feature change are image proxies, not segmented brain volume or measured atrophy.",
    "Images are reoriented and resized, not anatomically registered. Motion, scan settings and alignment can cause changes.",
    "Overlays show intensity differences from baseline. They are research visualizations, not Grad-CAM or model explanations.",
]


def run_pipeline(
    patient_id: str,
    visits: list[VisitInput],
    output_dir: Path,
    mode: str = "inference",
    progress: Callable[[int, str], None] | None = None,
) -> ProgressionResult:
    if mode not in {"demo", "inference"}:
        raise ValueError("Precomputed results must come from a validated cache")
    ordered = sorted(visits, key=lambda v: v.days_from_baseline)
    if not ordered or len({v.days_from_baseline for v in ordered}) != len(ordered):
        raise ValueError("Unique chronological visits are required")
    output_dir.mkdir(parents=True, exist_ok=True)
    volumes, affines, features, foreground = [], [], [], []
    for index, visit in enumerate(ordered):
        if progress:
            progress(10 + int(index / len(ordered) * 65), f"Preparing MRI {index + 1} of {len(ordered)}")
        prepared = prepare(Path(visit.mri_path))
        volumes.append(prepared.volume)
        affines.append(prepared.affine)
        features.append(extract_features(prepared.volume))
        foreground.append(float(np.mean(prepared.volume > 0.2)))
        slice_image(prepared.volume).resize((384, 384)).save(output_dir / f"{index}-mri.png")
    scores, changes = feature_delta_scores(np.stack(features))
    caveats = CAVEATS.copy()
    if mode == "demo":
        scores = [float(x) for x in np.linspace(0.22, 0.67, len(ordered))]
        caveats.insert(0, "DEMO: risk scores are fixed illustrative values, not MRI-derived predictions.")
    if progress:
        progress(85, "Rendering research visualizations")
    for index, volume in enumerate(volumes):
        difference_overlay(volume, volumes[0]).resize((384, 384)).save(output_dir / f"{index}-overlay.png")
        difference = np.abs(volume - volumes[0]).astype(np.float32)
        image = nib.Nifti1Image(difference, affines[index])
        image.header["descrip"] = b"Intensity difference proxy; shape-normalized, not registered"
        nib.save(image, output_dir / f"{index}-difference.nii.gz")
    return ProgressionResult(
        patient_id=patient_id,
        visit_ids=[v.visit_id for v in ordered],
        risk_scores=scores,
        biomarkers={"foreground_fraction": foreground, "feature_change": changes},
        selected_visit=ordered[-1].visit_id,
        days_from_baseline=[v.days_from_baseline for v in ordered],
        output_mode=mode,
        confidence=None,
        caveats=caveats,
        model_version=MODEL_VERSION,
        volume_overlays_ready=True,
    )
