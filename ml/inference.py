from collections.abc import Callable
from pathlib import Path

import nibabel as nib
import numpy as np

from ml.contracts import MODEL_VERSION, ProgressionResult, TrainedPrediction, VisitInput
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
    predictor: Callable[[list[np.ndarray]], TrainedPrediction] | None = None,
    model_version: str = MODEL_VERSION,
) -> ProgressionResult:
    if mode not in {"demo", "inference", "trained"}:
        raise ValueError("Precomputed results must come from a validated cache")
    if (mode == "trained") != (predictor is not None):
        raise ValueError("Trained mode requires a loaded trained predictor; fallback is not permitted")
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
    prediction = predictor(volumes) if predictor is not None else None
    if prediction is None:
        scores, changes = feature_delta_scores(np.stack(features))
    else:
        scores = []  # This checkpoint predicts a sequence, not a per-visit trajectory.
        changes = np.mean(np.abs(np.stack(features) - features[0]), axis=1).astype(float).tolist()
    caveats = CAVEATS.copy()
    if prediction is not None:
        caveats[1] = (
            "The trained score recognizes observed first-to-last CDR increase; it is uncalibrated, not a future Alzheimer's probability."
        )
        caveats.extend(
            [
                f"Experimental checkpoint with poor generalization: the reused {prediction.test_subjects}-subject holdout scored {prediction.test_accuracy:.0%} accuracy versus {prediction.majority_baseline_accuracy:.0%} for the majority baseline.",
                "MRI and demographic measurements from the observed final visit are inputs. No 12/24/36-month forecasting is provided.",
                "Training-subject predictions are in-sample demonstrations, not evidence of accuracy. No clinical or independent validation exists.",
                "Intensity-difference overlays and structural proxies are separate image calculations, not explanations of the trained model.",
            ]
        )
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
        model_version=model_version,
        volume_overlays_ready=True,
        prediction=prediction,
    )
