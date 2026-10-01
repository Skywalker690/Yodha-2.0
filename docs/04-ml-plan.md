# ML and Explainability Plan

## MVP strategy

Build a credible end-to-end research pipeline, not a publishable clinical model. Use a pretrained or lightweight 3D encoder, a small temporal LSTM, and cached demo outputs when full training is incomplete.

## New primary research objective

The user has now requested strict baseline-MCI to future Alzheimer dementia forecasting at 12/24/36 months. The existing OASIS models below remain separate retrospective experiments, not initial weights or validated predictors for this new endpoint. No strict forecasting training has started.

Start only after authorized data acquisition, diagnosis-code review and an auditable cohort/follow-up assessment. Use one eligible baseline per participant, baseline-available inputs only, patient-level splits, training-only imputation/scaling and masked unknown outcomes. First establish regularized clinical and clinical-plus-verified-MRI-summary baselines on matched subjects. Calibration and model selection use development data; preserve an independent final test set. A horizon with insufficient event/nonevent support remains unavailable rather than receiving fabricated probabilities or metrics. See [13 Strict forecasting data](13-strict-forecasting-data.md).

## Processing stages

1. Load NIfTI with NiBabel.
2. Validate shape, affine, and finite values.
3. Apply documented MONAI transforms.
4. Normalize intensity.
5. Resample or crop to a standard shape.
6. Extract per-visit features.
7. Preserve visit order.
8. Aggregate the sequence with an LSTM or transparent baseline.
9. Produce risk scores and structural metrics.
10. Generate or retrieve an explanation artifact.

## Analysis worker integration

The ML pipeline runs inside an analysis worker. It receives an analysis ID and storage keys, then returns a validated result contract. The worker persists results through the backend service layer. The browser never runs PyTorch directly.

## Baseline hierarchy

1. Deterministic demo outputs for UI development.
2. Feature-delta baseline over visits.
3. Small trained temporal model when data and labels are ready.
4. Grad-CAM tied to the selected model output.

Do not build a large 3D CNN and Transformer simultaneously.

## Explainability rules

Grad-CAM may explain the spatial encoder for the selected scan. If a heatmap is cached or generated as a saliency proxy, label it as a research visualization. Do not claim it fully explains the temporal model unless that relationship is implemented and tested.

## Evaluation

Use subject-level splits to prevent visits from the same subject appearing in both training and testing. Report accuracy, precision, recall, F1, ROC-AUC, and calibration/longitudinal metrics only when actually calculated. Always show sample size and limitations.

## Output honesty

Every result includes `output_mode`: `demo`, `precomputed`, or `inference`. The UI displays this provenance. Example values such as 22%, 41%, and 67% are illustrative until produced by the documented pipeline.

## Implemented baseline: feature-delta-v1

The default local inference follows the permitted transparent-baseline tier:

1. NiBabel validation and canonical RAS orientation.
2. Clip at 1st/99.5th intensity percentiles and scale to [0, 1].
3. MONAI trilinear `Resize` to 64 x 64 x 64. Shape normalization is not physical resampling or anatomical registration.
4. PyTorch adaptive average pooling to 4 x 4 x 4 (64 explicit spatial features), with no learned weights.
5. `delta_t = mean(abs(features_t - features_baseline))`.
6. `score_t = clip(5 * delta_t, 0, 1)`: baseline is zero by definition. Scores need not increase monotonically. The UI shows the required progression-risk estimate label and an uncalibrated-index caveat; percentages are not disease probabilities.
7. Foreground fraction is the share of normalized voxels above 0.2, an intensity proxy rather than tissue segmentation.
8. Central axial slices and absolute intensity-difference overlays versus baseline. Motion, acquisition and alignment can cause differences.

Observed OASIS nWBV/eTIV are source-attributed and shown separately. CDR/MMSE are optional observed metadata, not fabricated risk targets. No diagnostic accuracy, ROC-AUC or calibration numbers are calculated or displayed.

Small CNN (`SpatialEncoder`) and LSTM (`TemporalModel`) interfaces are included and tensor-tested. Offline MRI-only and multimodal training runners now save experimental checkpoints. The application continues to use `feature-delta-v1`; trained-checkpoint integration and model-specific Grad-CAM remain separate work.

The demonstration training runner is now provided by `scripts/train_longitudinal_model.py`. It caches all visits for the 56 subjects with at least three visits, uses a deterministic stratified 40/8/8 subject split, and trains `SpatialEncoder(32)+LSTM(16)` against the research-only observed CDR-increase target. Its checkpoint and metrics are local artifacts under `data/training/`; they are not clinical validation evidence.

Evaluate the checkpoint with `python -m scripts.evaluate_longitudinal_model`. The evaluator reports confusion-matrix metrics and ROC-AUC on the untouched eight-subject test split alongside a majority-class baseline. The small holdout is for workflow verification only; it is not sufficient evidence of generalization.

The audited multimodal experiment is run with `python -m scripts.train_multimodal_model`. It reads the original saved split, trains the MRI encoder, demographic MLP, packed LSTM and head together in bounded batches, and standardizes all 11 usable demographic/visit covariates using training-only statistics. CDR defines the target; Group and identifiers are excluded from features. All visits are inputs, so this is retrospective recognition of observed CDR change, not prospective prediction. See [12 Multimodal training](12-multimodal-training.md) for commands, artifacts and evaluation limitations.

Caches use SHA-256 keys derived from model version and ordered immutable MRI storage keys. Precomputed mode requires a matching result and visualization artifacts, with no demo fallback. Demo risk scores are fixed between 22% and 67% and visibly illustrative. Baseline confidence is null and hidden.

The 3D extension also saves absolute intensity-difference volumes on the existing 64-cube grid. MONAI `align_corners=False` maps resized voxel centers to `(i + 0.5) * source_shape / 64 - 0.5`; composing this transform with the canonical source affine preserves the selected scan's display field of view. Tests cover canonical axis permutations/flips and field-of-view boundaries. This does not register visits or change feature extraction/scoring, so `feature-delta-v1` remains unchanged. Old results default to no volumetric overlay until recomputed.
