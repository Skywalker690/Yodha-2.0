"""Validated, local inference for the frozen 40-subject retrospective experiment."""

from __future__ import annotations

import hashlib
import io
import json
import math
import pickle
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from ml.contracts import ProgressionResult, TrainedPrediction, VisitInput
from ml.inference import run_pipeline
from ml.multimodal import (
    CATEGORY_LEVELS,
    EXCLUDED_FEATURES,
    MODEL_VERSION,
    NUMERIC_FEATURES,
    DemographicPreprocessor,
    MultimodalClassifier,
    feature_names,
)

COVARIATE_FIELDS = (*NUMERIC_FEATURES, *CATEGORY_LEVELS)
IMAGE_PREPROCESSING = {
    "version": "canonical-percentile-resize-64-v1",
    "shape": [64, 64, 64],
    "orientation": "RAS",
    "percentiles": [1, 99.5],
    "resize": "trilinear-align_corners_false",
    "registered": False,
}
BUNDLE_FILES = ("metrics.json", "status.json", "subject_split.csv")


def _bundle_bytes(path: Path) -> dict[str, bytes]:
    files = {"checkpoint": path, **{name: path.parent / name for name in BUNDLE_FILES}}
    try:
        if any(not item.is_file() or item.stat().st_size > 100 * 1024 * 1024 for item in files.values()):
            raise ValueError(
                "Trained model bundle is missing or exceeds its loading limit. Configure a complete audited run."
            )
        return {name: item.read_bytes() for name, item in files.items()}
    except OSError:
        raise ValueError("Trained model bundle is unavailable. Check local model configuration.") from None


def _identity(blobs: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, data in sorted(blobs.items()):
        digest.update(name.encode())
        digest.update(hashlib.sha256(data).digest())
    return f"{MODEL_VERSION}-{digest.hexdigest()[:16]}"


def checkpoint_identity(path: Path) -> str:
    """Pin weights AND evidence/split bytes, not a mutable filename or 'latest'."""
    return _identity(_bundle_bytes(path))


def validate_covariates(visits: list[VisitInput]) -> None:
    if not 3 <= len(visits) <= 32:
        raise ValueError("Trained research inference requires 3 to 32 chronological MRI visits.")
    if len({v.visit_id for v in visits}) != len(visits):
        raise ValueError("Trained inputs must have unique MRI visits.")
    if any(b.days_from_baseline <= a.days_from_baseline for a, b in zip(visits, visits[1:])):
        raise ValueError("Trained MRI visits must have unique chronological dates.")
    bounds = {
        "Age": (18, 120),
        "EDUC": (0, 40),
        "SES": (1, 5),
        "MMSE": (0, 30),
        "eTIV": (0, None),
        "nWBV": (0, 1),
        "ASF": (0, None),
        "MR Delay": (0, 36500),
        "Visit": (1, 100),
    }
    ordinals = []
    for visit in visits:
        fields = visit.covariates
        if set(fields) != set(COVARIATE_FIELDS):
            raise ValueError(
                "Trained inference needs all 11 source covariates. Import complete demographics; labels and identifiers are not inputs."
            )
        for name, (low, high) in bounds.items():
            value = fields[name]
            if value is None and name in {"SES", "MMSE"}:
                continue
            if value is None or isinstance(value, (str, bool)) or not math.isfinite(value):
                raise ValueError(f"Invalid or absent source covariate: {name}.")
            if value < low or (high is not None and value > high) or (name in {"eTIV", "ASF"} and value == 0):
                raise ValueError(f"Source covariate outside the supported range: {name}.")
            if name in {"MR Delay", "Visit", "EDUC", "SES"} and value != int(value):
                raise ValueError(f"Source covariate must be a recorded integer: {name}.")
        if fields["MR Delay"] != visit.days_from_baseline:
            raise ValueError("Recorded MRI delay does not match the visit date.")
        for name, levels in CATEGORY_LEVELS.items():
            if not isinstance(fields[name], str) or fields[name] not in levels:
                raise ValueError(f"Unsupported or absent source category: {name}.")
        ordinals.append(fields["Visit"])
    if any(b <= a for a, b in zip(ordinals, ordinals[1:])):
        raise ValueError("Recorded visit numbers must increase chronologically.")


@dataclass
class TrainedBundle:
    model: MultimodalClassifier
    preprocessor: DemographicPreprocessor
    version: str
    checkpoint_sha256: str
    threshold: float
    metrics: dict[str, Any]
    roles: dict[str, str]

    def predict(
        self, volumes: list[np.ndarray], covariates: list[dict], subject_code: str
    ) -> TrainedPrediction:
        if any(v.shape != (64, 64, 64) or not np.isfinite(v).all() for v in volumes):
            raise ValueError("Trained MRI inputs must be finite 64-cube volumes.")
        demographics = self.preprocessor.transform(pd.DataFrame(covariates))
        images = torch.from_numpy(np.stack(volumes).astype(np.float32))[None, :, None]
        with torch.inference_mode():
            score = float(
                self.model(images, torch.from_numpy(demographics)[None], torch.tensor([len(volumes)]))
                .sigmoid()
                .item()
            )
        heldout = self.metrics["evaluation"]["test"]["at_validation_threshold"]
        return TrainedPrediction(
            score=score,
            decision_threshold=self.threshold,
            predicted_increase=score >= self.threshold,
            checkpoint_sha256=self.checkpoint_sha256,
            cohort_role=self.roles.get(subject_code, "unassigned"),
            training_subjects=self.metrics["split_counts"]["train"]["subjects"],
            training_visits=self.metrics["split_counts"]["train"]["visits"],
            test_subjects=heldout["subjects"],
            test_accuracy=heldout["accuracy"],
            test_balanced_accuracy=heldout["balanced_accuracy"],
            test_roc_auc=heldout["roc_auc"],
            majority_baseline_accuracy=self.metrics["majority_baseline"]["accuracy"],
        )


def load_bundle(path: Path, expected_version: str | None = None) -> TrainedBundle:
    blobs = _bundle_bytes(path)
    version = _identity(blobs)
    if expected_version is not None and version != expected_version:
        raise ValueError("Trained model bundle changed after this job was queued. Start a new analysis.")
    try:
        checkpoint = torch.load(io.BytesIO(blobs["checkpoint"]), map_location="cpu", weights_only=True)
        metrics = json.loads(blobs["metrics.json"])
        status = json.loads(blobs["status.json"])
        manifest = pd.read_csv(io.BytesIO(blobs["subject_split.csv"]))
        if status != {"status": "completed", "checkpoint_roundtrip": "passed"}:
            raise ValueError("Training did not complete its checkpoint round-trip.")
        if checkpoint["model_version"] != MODEL_VERSION or metrics["model_version"] != MODEL_VERSION:
            raise ValueError("Unsupported trained model version.")
        if checkpoint["target"] != "observed_cdr_increase" or metrics["target"] != checkpoint["target"]:
            raise ValueError("Checkpoint target does not match the retrospective task.")
        if (
            checkpoint["feature_names"] != feature_names()
            or checkpoint["image_preprocessing"] != IMAGE_PREPROCESSING
        ):
            raise ValueError("Checkpoint preprocessing schema is incompatible.")
        if set(checkpoint["excluded_input_fields"]) != set(EXCLUDED_FEATURES):
            raise ValueError("Checkpoint input-exclusion schema is incompatible.")
        if hashlib.sha256(blobs["subject_split.csv"]).hexdigest() != checkpoint["split_sha256"]:
            raise ValueError("Frozen model subject split was changed.")
        required = {"subject_id", "visit_id", "days_from_baseline", "split"}
        if not required.issubset(manifest) or manifest[list(required)].isna().any().any():
            raise ValueError("Frozen model subject split is incomplete.")
        if (
            manifest["visit_id"].duplicated().any()
            or (manifest.groupby("subject_id")["split"].nunique() != 1).any()
        ):
            raise ValueError("Frozen model subject split contains leakage or duplicate visits.")
        if set(manifest["split"]) != {"train", "validation", "test"}:
            raise ValueError("Frozen model subject split has unknown assignments.")
        counts = checkpoint["split_counts"]
        if metrics["split_counts"] != counts:
            raise ValueError("Model evidence and checkpoint cohort counts disagree.")
        for name, subjects in {"train": 40, "validation": 8, "test": 8}.items():
            rows = manifest[manifest["split"] == name]
            if (
                counts[name]["subjects"] != subjects
                or rows["subject_id"].nunique() != subjects
                or len(rows) != counts[name]["visits"]
            ):
                raise ValueError("The model must use the frozen 40/8/8 cohort and complete visits.")
        training_ids = set(manifest.loc[manifest["split"] == "train", "subject_id"])
        if (
            set(checkpoint["preprocessing_fit_subject_ids"]) != training_ids
            or checkpoint["preprocessing_fit_visits"] != counts["train"]["visits"]
        ):
            raise ValueError("Preprocessing must be fitted on training subjects only.")
        threshold = float(checkpoint["decision_threshold"])
        if (
            not math.isfinite(threshold)
            or not 0 <= threshold <= 1
            or metrics["threshold_fit_split"] != "validation"
            or threshold != metrics["validation_selected_threshold"]
        ):
            raise ValueError("Decision threshold must come from the saved validation split.")
        if checkpoint["best_epoch"] != metrics["best_epoch"] or metrics["optimizer_steps"] < 1:
            raise ValueError("Checkpoint training evidence is inconsistent.")
        changes = metrics["trainable_branch_weight_changes_l2"]
        if any(
            not math.isfinite(changes[branch]) or changes[branch] <= 0
            for branch in ("encoder", "demographics", "lstm", "head")
        ):
            raise ValueError("Every model branch must have trained weights.")
        model = MultimodalClassifier()
        weights = checkpoint["model_state_dict"]
        if any(not torch.isfinite(value).all() for value in weights.values()):
            raise ValueError("Trained weights must be finite.")
        model.load_state_dict(weights, strict=True)
        model.eval()
        preprocessor = DemographicPreprocessor.from_dict(checkpoint["demographic_preprocessor"])
        roles = manifest.groupby("subject_id")["split"].first().to_dict()
        bundle = TrainedBundle(
            model,
            preprocessor,
            version,
            hashlib.sha256(blobs["checkpoint"]).hexdigest(),
            threshold,
            metrics,
            roles,
        )
        # Validate public evidence before expensive MRI loading, without exposing individual predictions.
        heldout = metrics["evaluation"]["test"]["at_validation_threshold"]
        TrainedPrediction(
            score=0,
            decision_threshold=threshold,
            predicted_increase=0 >= threshold,
            checkpoint_sha256=bundle.checkpoint_sha256,
            cohort_role="unassigned",
            training_subjects=counts["train"]["subjects"],
            training_visits=counts["train"]["visits"],
            test_subjects=heldout["subjects"],
            test_accuracy=heldout["accuracy"],
            test_balanced_accuracy=heldout["balanced_accuracy"],
            test_roc_auc=heldout["roc_auc"],
            majority_baseline_accuracy=metrics["majority_baseline"]["accuracy"],
        )
        return bundle
    except (
        KeyError,
        TypeError,
        RuntimeError,
        EOFError,
        OSError,
        pickle.UnpicklingError,
        json.JSONDecodeError,
        pd.errors.ParserError,
    ) as exc:
        raise ValueError(
            "Trained checkpoint or its evidence is incompatible or corrupt. No baseline fallback was used."
        ) from exc


def run_trained_pipeline(
    patient_id: str,
    visits: list[VisitInput],
    output_dir: Path,
    checkpoint_path: Path,
    expected_version: str,
    subject_code: str,
    progress: Callable[[int, str], None] | None = None,
) -> ProgressionResult:
    ordered = sorted(visits, key=lambda v: v.days_from_baseline)
    validate_covariates(ordered)
    bundle = load_bundle(checkpoint_path, expected_version)
    return run_pipeline(
        patient_id,
        ordered,
        output_dir,
        "trained",
        progress,
        predictor=lambda volumes: bundle.predict(volumes, [v.covariates for v in ordered], subject_code),
        model_version=bundle.version,
    )
