"""Train-only preprocessing, subject selection/calibration/test and gated candidates."""

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from ml.anatomy.evaluation import calibrate_intervals, geometry_metrics, interval_coverage
from ml.anatomy.features import (
    VERSION as FEATURE_VERSION,
    availability_summary,
    feature_availability,
    fit_reference,
    reference_hash,
    validate_reference_split,
)
from ml.anatomy.model import FeatureScaler, SpatialPredictor, VERSION, spatial_loss
from ml.anatomy.registration import nifti
from ml.anatomy.spatial import warp
from ml.anatomy.structural import RegularizedMixedEffects, history_features, simple_baselines
from ml.anatomy.study import load_case
from src.common import sha256, write_json

SEED = 42
# Predeclared research-release criteria, NOT clinically validated thresholds.
GATES = {
    "minimum_train_subjects": 44,
    "selection_subjects": 4,
    "calibration_subjects": 4,
    "test_subjects": 4,
    "minimum_epochs": 15,
    "minimum_mean_dice": 0.70,
    "maximum_mean_assd_mm": 3.0,
    "interval_level": 0.80,
    "interval_tolerance_days": 90,
    "minimum_horizon_subjects": {"train": 10, "selection": 3, "test": 3},
}
HORIZONS = (183, 365, 731, 1096)


def development_roles(split: dict[str, str]) -> dict[str, str]:
    if "selection" in split.values() or "calibration" in split.values():
        if any(list(split.values()).count(role) != 4 for role in ("selection", "calibration", "test")):
            raise ValueError("Four independent selection/calibration/test subjects required")
        return dict(split)
    subjects = sorted(
        (s for s, r in split.items() if r == "validation"),
        key=lambda s: hashlib.sha256(f"{SEED}:{s}".encode()).hexdigest(),
    )
    if len(subjects) != 8:
        raise ValueError("Eight frozen development subjects required: four selection, four calibration")
    return {**split, **{s: "selection" if i < 4 else "calibration" for i, s in enumerate(subjects)}}


def _features(example, with_scores: bool, reference: dict) -> tuple[np.ndarray, list[str]]:
    return history_features(
        example.history,
        example.interval_days,
        with_scores,
        require_review=not example.allow_unreviewed_research,
        reference=reference,
    )


def predict_field(
    model: SpatialPredictor,
    scaler: FeatureScaler,
    example,
    data: dict,
    with_scores: bool,
    device: str,
    reference: dict | None = None,
) -> np.ndarray:
    if reference is None:
        raise ValueError("Spatial prediction requires the saved training reference")
    row, _ = _features(example, with_scores, reference)
    with torch.inference_mode():
        field = model(
            torch.from_numpy(data["images"])[None].to(device),
            torch.from_numpy(scaler.transform(row))[None].to(device),
            torch.tensor([example.interval_days / 365.25], dtype=torch.float32, device=device),
        )
    return field[0].cpu().numpy().transpose(1, 2, 3, 0)


def _spatial_evaluation(
    model, scaler, cases: list, with_scores: bool, device: str, reference: dict | None = None
) -> dict:
    errors, baseline, invalid = defaultdict(list), defaultdict(list), 0
    for _, example, data in cases:
        try:
            field = predict_field(model, scaler, example, data, with_scores, device, reference)
            predicted = warp(
                nifti(data["labels"], data["affine"]), nifti(field, data["affine"]), categorical=True
            )
            target = nifti(data["target_labels"], data["affine"])
            errors[example.subject_id].extend(geometry_metrics(predicted, target).values())
            baseline[example.subject_id].extend(
                geometry_metrics(nifti(data["labels"], data["affine"]), target).values()
            )
        except ValueError:
            invalid += 1

    def summary(rows: dict[str, list[dict]]) -> dict | None:
        if not rows:
            return None
        return {
            key: float(np.mean([np.mean([v[key] for v in subject]) for subject in rows.values()]))
            for key in next(iter(rows.values()))[0]
        }

    return {
        "cases": len(cases),
        "subjects": len({example.subject_id for _, example, _ in cases}),
        "aggregation": "mean within subject, then mean across subjects",
        "invalid_cases": invalid,
        "mean": summary(errors),
        "no_change_mean": summary(baseline),
        "surface_distance_method": "physical voxel-boundary bidirectional nearest-neighbour",
        "grid": "learning grid; native validation required for release",
    }


def _volume_errors(models: dict, cases: list) -> tuple[dict, dict[str, list[np.ndarray]]]:
    rows: dict[str, list] = defaultdict(list)
    grouped: dict[str, list] = defaultdict(list)
    regions = sorted(cases[0][1].target.volumes_mm3)
    for _, example, _ in cases:
        predicted = simple_baselines(
            example.history,
            example.interval_days,
            allow_unreviewed_research=example.allow_unreviewed_research,
        )
        predicted.update(
            {
                name: model.predict(
                    example.subject_id,
                    example.history,
                    example.interval_days,
                    allow_unreviewed_research=example.allow_unreviewed_research,
                )
                for name, model in models.items()
            }
        )
        target = np.array([example.target.volumes_mm3[k] for k in regions])
        for name, values in predicted.items():
            error = np.array([values[k] for k in regions]) - target
            rows[name].append((example.subject_id, error))
            if name == "with_scores":
                grouped[example.subject_id].append(error)
    # Subject-balanced aggregates: repeated visits never increase a subject's weight.
    metrics = {}
    for name, entries in rows.items():
        subjects = sorted({s for s, _ in entries})
        mae = np.mean(
            [np.mean(np.abs([e for s, e in entries if s == subject]), axis=0) for subject in subjects], axis=0
        )
        mse = np.mean(
            [np.mean(np.square([e for s, e in entries if s == subject]), axis=0) for subject in subjects],
            axis=0,
        )
        metrics[name] = {
            "subjects": len(subjects),
            "cases": len(entries),
            "mean_mae_mm3": float(mae.mean()),
            "regions": {
                region: {"mae_mm3": float(mae[i]), "rmse_mm3": float(np.sqrt(mse[i]))}
                for i, region in enumerate(regions)
            },
        }
    return metrics, dict(grouped)


def train(
    study: Path,
    output: Path,
    *,
    epochs: int = 20,
    device: str = "cpu",
    synthetic: bool = False,
    allow_unreviewed_research: bool = False,
    allow_partial_cohort: bool = False,
    reference: dict | None = None,
) -> dict:
    if not 1 <= epochs <= 500 or device not in {"cpu", "cuda"}:
        raise ValueError("Bounded epoch count and cpu/cuda device required")
    manifest = json.loads(study.read_text())
    if manifest["synthetic"] != synthetic:
        raise ValueError("Synthetic provenance must be explicit and cannot be removed")
    roles = development_roles(manifest["split"])
    cases = []
    for entry in manifest["cases"]:
        path = checked_case(study.parent, entry)
        item = load_case(path, require_review=not allow_unreviewed_research)
        if item[1].allow_unreviewed_research and not allow_unreviewed_research:
            raise ValueError("Unreviewed research data requires an explicit candidate-only training flag")
        if item[0]["subject_id"] not in roles:
            raise ValueError("Example outside frozen split")
        cases.append(item)
    grouped = {
        role: [c for c in cases if roles[c[0]["subject_id"]] == role]
        for role in ("train", "selection", "calibration", "test")
    }
    active_roles = dict(roles)
    required_roles = ("train", "selection", "test") if allow_partial_cohort else tuple(grouped)
    if (
        any(not grouped[role] for role in required_roles)
        or len({c[0]["subject_id"] for c in grouped["train"]}) < 2
    ):
        raise ValueError("Training, selection, independent calibration and held-out test examples required")
    if output.exists():
        raise ValueError("A training run is immutable; choose a new output directory")
    output.mkdir(parents=True)
    reference = reference or fit_reference({e.subject_id: e.history for _, e, _ in grouped["train"]}, roles)
    validate_reference_split(reference, roles)
    write_json(output / "nwbv-reference.json", reference)
    if (
        not synthetic
        and not allow_partial_cohort
        and any(
            len({c[0]["subject_id"] for c in grouped[role]}) != list(roles.values()).count(role)
            for role in grouped
        )
    ):
        raise ValueError("Complete frozen cohort required; explicitly request provisional partial fitting")
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    if device == "cuda":
        if not torch.cuda.is_available():
            raise ValueError("CUDA is unavailable; no device fallback")
        torch.cuda.manual_seed_all(SEED)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    write_json(
        output / "status.json",
        {
            "stage": "training",
            "synthetic": synthetic,
            "gates": GATES,
            "roles": active_roles,
            "study_sha256": sha256(study),
        },
    )
    structural, spatial, selection = {}, {}, {}
    for with_scores, name in ((True, "with_scores"),):
        # Hyperparameters are selected on selection subjects ONLY.
        candidates = []
        for fixed in (1.0, 10.0, 100.0):
            for random_penalty in (1.0, 10.0, 100.0):
                model = RegularizedMixedEffects(fixed, random_penalty, with_scores).fit(
                    [e for _, e, _ in grouped["train"]], manifest["split"], reference=reference
                )
                try:
                    errors = _volume_errors({name: model}, grouped["selection"])[0][name]["mean_mae_mm3"]
                    candidates.append((errors, model))
                except ValueError:
                    continue
        if not candidates:
            raise ValueError("No valid structural candidate on selection subjects")
        structural[name] = min(candidates, key=lambda item: item[0])[1]
        rows = np.stack([_features(e, with_scores, reference)[0] for _, e, _ in grouped["train"]])
        scaler = FeatureScaler.fit(rows)
        names = _features(grouped["train"][0][1], with_scores, reference)[1]
        write_json(
            output / "preprocessing.json",
            {
                "feature_contract": FEATURE_VERSION,
                "feature_names": names,
                "nwbv_reference_sha256": reference_hash(reference),
                "spatial": scaler.to_dict(),
                "structural": {
                    "median": structural[name].median.tolist(),
                    "scale": structural[name].scale.tolist(),
                },
                "training_feature_availability": feature_availability(rows, names),
                "missing_value_policy": "training medians and per-column missingness; all-missing columns zero",
            },
        )
        torch.manual_seed(SEED)
        model = SpatialPredictor(len(names) * 2).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        best, log = float("inf"), []
        for epoch in range(epochs):
            model.train()
            order = np.random.default_rng(SEED + epoch).permutation(len(grouped["train"]))
            losses = []
            for index in order:
                _, example, data = grouped["train"][index]
                images = torch.from_numpy(data["images"])[None].to(device)
                affine = torch.from_numpy(data["affine"])[None].to(device)
                features = torch.from_numpy(scaler.transform(_features(example, with_scores, reference)[0]))[
                    None
                ].to(device)
                field = model(images, features, torch.tensor([example.interval_days / 365.25], device=device))
                loss, _ = spatial_loss(
                    field,
                    torch.from_numpy(data["target_field"])[None].to(device),
                    images,
                    torch.from_numpy(data["later"])[None].to(device),
                    torch.from_numpy(data["labels"])[None].to(device),
                    affine,
                    torch.from_numpy(data["target_ratios"])[None].to(device),
                )
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite training loss; no checkpoint released")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                losses.append(float(loss.detach()))
            model.eval()
            scores = _spatial_evaluation(model, scaler, grouped["selection"], with_scores, device, reference)
            metric = (
                float("inf")
                if scores["invalid_cases"] or scores["mean"] is None
                else 1 - scores["mean"]["dice"] + scores["mean"]["assd_mm"] / 10
            )
            log.append({"epoch": epoch + 1, "loss": float(np.mean(losses)), "selection": scores})
            if metric < best:
                best = metric
                torch.save(
                    {
                        "version": VERSION,
                        "feature_contract": FEATURE_VERSION,
                        "nwbv_reference": reference,
                        "nwbv_reference_sha256": reference_hash(reference),
                        "with_scores": with_scores,
                        "feature_names": names,
                        "scaler": scaler.to_dict(),
                        "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        "grid_size": data["images"].shape[1],
                        "epoch": epoch + 1,
                    },
                    output / f"{name}.pt",
                )
            write_json(output / f"{name}-training.json", {"epochs": log})
        if not (output / f"{name}.pt").is_file():
            raise ValueError("All selection fields failed geometric checks; training remains incomplete")
        saved = torch.load(output / f"{name}.pt", map_location=device, weights_only=True)
        model.load_state_dict(saved["state_dict"])
        model.eval()
        spatial[name] = (model, scaler)
        selection[name] = _spatial_evaluation(
            model, scaler, grouped["selection"], with_scores, device, reference
        )
        write_json(output / f"{name}.json", structural[name].to_dict())
    calibration_metrics, calibration_errors = (
        _volume_errors(structural, grouped["calibration"]) if grouped["calibration"] else ({}, {})
    )
    calibration = None
    if len(calibration_errors) >= 4:
        calibration = calibrate_intervals(calibration_errors, GATES["interval_level"])
    # Final test is opened only AFTER checkpoints and hyperparameters are frozen.
    test_volume, test_errors = _volume_errors(structural, grouped["test"])
    test_spatial = {
        name: _spatial_evaluation(model, scaler, grouped["test"], name == "with_scores", device, reference)
        for name, (model, scaler) in spatial.items()
    }
    coverage = interval_coverage(calibration, test_errors) if calibration and len(test_errors) >= 4 else None
    interval_release = (
        calibration if coverage and min(coverage["per_region"]) >= GATES["interval_level"] else None
    )
    counts = {r: len({c[0]["subject_id"] for c in values}) for r, values in grouped.items()}
    supported = [
        h
        for h in HORIZONS
        if all(
            len(
                {
                    c[0]["subject_id"]
                    for c in grouped[r]
                    if abs(c[1].interval_days - h) <= GATES["interval_tolerance_days"]
                }
            )
            >= minimum
            for r, minimum in GATES["minimum_horizon_subjects"].items()
        )
    ]
    metrics = test_spatial["with_scores"]
    failures = []
    if synthetic:
        failures.append("Synthetic tests cannot be promoted")
    review_complete = all(
        c[0]["registration_qc"] == "passed"
        and all(v.qc == "passed" and v.ratings.status == "ok" for v in [*c[1].history, c[1].target])
        for c in cases
    )
    if not review_complete:
        failures.append(
            "Visual segmentation/alignment/registration review incomplete; research candidate cannot promote"
        )
    if counts != {"train": 44, "selection": 4, "calibration": 4, "test": 4}:
        failures.append("The complete frozen subject cohort is not reviewed/usable")
    if epochs < GATES["minimum_epochs"]:
        failures.append("Minimum training budget not completed")
    if not supported:
        failures.append("No requested horizon has predeclared subject support")
    if (
        metrics["invalid_cases"]
        or not metrics["mean"]
        or metrics["mean"]["dice"] < GATES["minimum_mean_dice"]
        or metrics["mean"]["assd_mm"] > GATES["maximum_mean_assd_mm"]
    ):
        failures.append("Held-out spatial quality/geometry gate failed")
    if test_volume["with_scores"]["mean_mae_mm3"] > test_volume["no_change"]["mean_mae_mm3"]:
        failures.append("Score-conditioned volumes do not improve the no-change baseline")
    # Native artifact validation is deliberately separate from learning-grid metrics.
    native = {"status": "not_evaluated", "reason": "Run native evaluation before promotion"}
    report = {
        "version": VERSION,
        "feature_contract": FEATURE_VERSION,
        "nwbv_reference_sha256": reference_hash(reference),
        "nwbv_reference_provenance": {
            "reference_subjects": reference["reference_subjects"],
            "reference_origin": reference["reference_origin"],
            "heldout_reference_overlap_possible": False,
            "independent_population_norm": False,
        },
        "nwbv_availability": {
            role: availability_summary([c[1].history for c in values], reference)
            for role, values in grouped.items()
        },
        "synthetic": synthetic,
        "model_policy": "MTA-Koedam-conditioned-only",
        "review_complete": review_complete,
        "allow_unreviewed_research": allow_unreviewed_research,
        "epochs": epochs,
        "seed": SEED,
        "training_runtime": {
            "torch": str(torch.__version__),
            "device": device,
            "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        },
        "counts": counts,
        "example_counts": {role: len(values) for role, values in grouped.items()},
        "actual_training_subjects": sorted({c[0]["subject_id"] for c in grouped["train"]}),
        "reference_training_subjects": reference["training_subjects"],
        "eligible_reference_subjects": reference["reference_subject_ids"],
        "feature_availability": {
            role: feature_availability(np.stack([_features(c[1], True, reference)[0] for c in values]), names)
            if values
            else {}
            for role, values in grouped.items()
        },
        "gates": GATES,
        "candidate_sha256": {name: sha256(output / name) for name in ("with_scores.pt", "with_scores.json")},
        "study_sha256": sha256(study),
        "split": manifest["split"],
        "roles": active_roles,
        "supported_intervals_days": supported,
        "selection": selection,
        "calibration_metrics": calibration_metrics,
        "test_volume": test_volume,
        "test_spatial": test_spatial,
        "interval_calibration": interval_release,
        "interval_coverage": coverage,
        "native": native,
        "release_failures": failures,
        "clinical_validation": False,
    }
    write_json(output / "evaluation.json", report)
    write_json(
        output / "status.json",
        {
            "stage": "candidate_requires_native_evaluation",
            "synthetic": synthetic,
            "release_failures": failures,
        },
    )
    return report


def checked_case(root: Path, entry: dict) -> Path:
    from ml.anatomy.integrity import checked_file

    return checked_file(root, entry)
