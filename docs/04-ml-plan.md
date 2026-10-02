# ML and Explainability Plan

## Frozen historical inference (D046)

An explicit compatibility adapter loads original v3 scalar/spatial weights without
fitting. Four training subjects supplied 129 conditioning columns. Its saved fixed
reference is separate from current v4 training-reference construction. Earlier MRIs
register to the latest input; a learned time-conditioned field warps that patient's
MRI and masks. Scalar prediction uses saved mixed-effects coefficients and observed
history adaptation. Future targets never enter inference. Annual horizons remain
exploratory; scalar/mask disagreement is visible and geometry failures block.

Current D044 models use `anatomy-input-v4-train-age-reference`: a frozen
training-baseline-CDR-zero reference with no ten-subject cutoff and no held-out
members. The v3 discussion below is preserved history. The reference uses
baseline metadata from all 44 declared training subjects; a partial fit separately
reports its actual gradient subjects and that wider declared reference cohort.
The full fit requires all 44 subjects. Chronological cutoff rules, physical units
and train-only imputation/scaling are unchanged. See [20](20-training-reference-anatomy-run.md).

The current anatomy implementation is `anatomy-input-v3-fixed-age-reference`;
see D043 and [19 Fixed-reference anatomy run](19-fixed-reference-anatomy-run.md).
Both scalar and spatial models use the same feature builder and saved fixed
reference. The means/SDs are copied from the supplied table without fitting them
to this run. Imputation/scaling still fit on gradient-training subjects only.
Exclude raw nWBV, age and other demographics from conditioning. Reference overlap
with this OASIS-2 holdout is possible and prevents a claim of independent reference
validation. Historical/baseline-classifier feature contracts remain unchanged.

For the separate anatomy extension and its incomplete scientific gates, see
[17 Longitudinal anatomy](17-longitudinal-anatomy.md). Neither historical CDR model
forecasts future geometry. Cutoff-local registration, score-conditioned mixed-effects/3D
training, held-out calibration, native evaluation and gated release are implemented
in `ml/anatomy/`. No real anatomy model is trained/promoted yet. See
[18 Anatomy forecasting lifecycle](18-anatomy-forecast-lifecycle.md) for inputs,
physical mapping, gates and reproducible commands.

## Current FastSurfer baseline study

The default serving policy is now ML-only Clinical + FastSurfer; earlier rule-based
and retrospective models below are not serving fallbacks. Actual processing/training
uses [the durable staged workflow](16-ml-only-serving.md) and explicit release gates.

The October 2 PRD defines a baseline-only OASIS-2 study, implemented in `src/`.
The compact Tier A/B logistic models use known labels only and train-only preprocessing;
FastSurfer is a pinned, offline anatomical processor. The old CNN/MLP/LSTM remains a
retrospective historical experiment, not a source of horizon probabilities. See
[architecture](15-fastsurfer-architecture.md), [endpoint](cohort_definition.md),
[evaluation](evaluation.md) and [blockers](blockers.md). Predictions must not be
described as an Alzheimer diagnosis or a future disease transition.

## MVP strategy

Build a credible end-to-end research pipeline, not a publishable clinical model. Use a pretrained or lightweight 3D encoder, a small temporal LSTM, and cached demo outputs when full training is incomplete.

## OASIS-2 research objective

Use only the supplied OASIS-2 MRI, demographics workbook and recorded clinical
measurements. The supported baseline task predicts later observed CDR conversion
from the earliest CDR-zero visit, using demographics and reviewed FastSurfer
measurements only when available. Later visits establish outcomes and must never
enter baseline predictors. Split by subject, fit preprocessing on training subjects,
compare matched clinical and clinical-plus-MRI models, and suppress unsupported
horizons. CDR conversion is not an Alzheimer-specific diagnosis.

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

The explicitly selected legacy baseline inference follows the permitted transparent-baseline tier:

1. NiBabel validation and canonical RAS orientation.
2. Clip at 1st/99.5th intensity percentiles and scale to [0, 1].
3. MONAI trilinear `Resize` to 64 x 64 x 64. Shape normalization is not physical resampling or anatomical registration.
4. PyTorch adaptive average pooling to 4 x 4 x 4 (64 explicit spatial features), with no learned weights.
5. `delta_t = mean(abs(features_t - features_baseline))`.
6. `score_t = clip(5 * delta_t, 0, 1)`: baseline is zero by definition. Scores need not increase monotonically. The UI shows the required progression-risk estimate label and an uncalibrated-index caveat; percentages are not disease probabilities.
7. Foreground fraction is the share of normalized voxels above 0.2, an intensity proxy rather than tissue segmentation.
8. Central axial slices and absolute intensity-difference overlays versus baseline. Motion, acquisition and alignment can cause differences.

Observed OASIS nWBV/eTIV are source-attributed and shown separately. CDR/MMSE are optional observed metadata, not fabricated risk targets. No diagnostic accuracy, ROC-AUC or calibration numbers are calculated or displayed.

Small CNN (`SpatialEncoder`) and LSTM (`TemporalModel`) interfaces are included and tensor-tested. Offline MRI-only and multimodal training runners save experimental checkpoints. The audited multimodal checkpoint is now integrated through explicitly experimental `trained` mode, initially selected in the workspace; legacy baseline/demo/precomputed modes and historical results remain available. It returns one retrospective sequence score, not a disease probability or future trajectory. Model-specific Grad-CAM remains separate work. See [14 Trained inference](14-trained-inference.md).

The demonstration training runner is now provided by `scripts/train_longitudinal_model.py`. It caches all visits for the 56 subjects with at least three visits, uses a deterministic stratified 40/8/8 subject split, and trains `SpatialEncoder(32)+LSTM(16)` against the research-only observed CDR-increase target. Its checkpoint and metrics are local artifacts under `data/training/`; they are not clinical validation evidence.

Evaluate the checkpoint with `python -m scripts.evaluate_longitudinal_model`. The evaluator reports confusion-matrix metrics and ROC-AUC on the untouched eight-subject test split alongside a majority-class baseline. The small holdout is for workflow verification only; it is not sufficient evidence of generalization.

The audited multimodal experiment is run with `python -m scripts.train_multimodal_model`. It reads the original saved split, trains the MRI encoder, demographic MLP, packed LSTM and head together in bounded batches, and standardizes all 11 usable demographic/visit covariates using training-only statistics. CDR defines the target; Group and identifiers are excluded from features. All visits are inputs, so this is retrospective recognition of observed CDR change, not prospective prediction. See [12 Multimodal training](12-multimodal-training.md) for commands, artifacts and evaluation limitations.

Caches use SHA-256 keys derived from model version and ordered immutable MRI storage keys. Precomputed mode requires a matching result and visualization artifacts, with no demo fallback. Demo risk scores are fixed between 22% and 67% and visibly illustrative. Baseline confidence is null and hidden.

The 3D extension also saves absolute intensity-difference volumes on the existing 64-cube grid. MONAI `align_corners=False` maps resized voxel centers to `(i + 0.5) * source_shape / 64 - 0.5`; composing this transform with the canonical source affine preserves the selected scan's display field of view. Tests cover canonical axis permutations/flips and field-of-view boundaries. This does not register visits or change feature extraction/scoring, so `feature-delta-v1` remains unchanged. Old results default to no volumetric overlay until recomputed.
