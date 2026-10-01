# Experimental trained-model inference

## Scope

On 2026-10-01 the user requested application inference with the existing 40-person trained model. D022 permits explicitly experimental integration of the audited `multimodal-cdr-retrospective-v2` checkpoint; it does not authorize a clinical deployment or satisfy the strict MCI-to-Alzheimer forecasting task.

The exact original 40 training subjects and their 132 visits remain fixed. Validation has eight subjects/29 visits; the reused test holdout has eight subjects/24 visits. Candidate selection is not changed to increase apparent accuracy. Subject selection, target, visit chronology and split are checked against the frozen source manifest. Positive training cases remain six, not forty. In-sample predictions are not evaluation evidence.

## Runtime

The workspace initially selects **Trained** mode. The existing API defaults and upload-time image-processing jobs remain baseline-compatible; the UI explicitly submits `outputMode: "trained"` to run the neural checkpoint. Baseline inference, demo and baseline precomputed modes remain separately selectable and historical results are preserved.

Configure `TRAINED_MODEL_PATH` in the ignored root environment if necessary. The default is `data/training_multimodal/runs/20261001T134908Z/multimodal_model.pt`. A complete run also needs adjacent `metrics.json`, `status.json` and `subject_split.csv`. These are ignored local artifacts, not repository assets. Share checkpoints only through an authorized data/artifact handoff.

The API snapshots whitelisted source covariates, chronological MRI keys and a fingerprint of the weights/evidence/split bundle. The one existing background worker performs inference; it loads weights with PyTorch `weights_only=True`, validates the task/architecture/schema, frozen 40/8/8 membership, train-only preprocessing and validation-selected threshold. Changed/missing/incompatible bundles fail explicitly. No request loads untrained weights, runs training, or silently falls back to a baseline.

MRI preprocessing is identical to training: validate, orient to RAS, normalize at the 1st/99.5th percentiles and resize to 64 cubed. The CNN, demographic MLP, packed LSTM and head all participate in prediction. No preprocessing statistics are fitted on the inference subject.

## Input eligibility

At least three chronological MRI visits are required, with all eleven source covariates present at each visit: Age, EDUC, SES, MMSE, eTIV, nWBV, ASF, MR Delay, Visit, M/F and Hand. Recorded SES/MMSE may explicitly be missing and use the checkpoint's training medians and missingness indicators. Absent ingestion is not equivalent to a documented missing measurement. Other missing/out-of-range inputs fail. Recorded timing and visit order must agree with the requested sequence. Identifiers, Group and CDR never enter the neural inputs.

The application does not infer education, handedness or brain measurements from an uploaded scan, nor substitute a patient's baseline age for later ages. Uploaded cases without source covariates can still use the explicitly named baseline mode; trained mode remains unavailable until the required recorded inputs exist.

## Result semantics

`ProgressionResult.prediction` contains **one** observed-sequence CDR-increase score, saved decision threshold/classification, checkpoint SHA-256, subject cohort role and aggregate test evidence. `risk_scores` is empty for trained results: this checkpoint was not trained to produce a visit-by-visit trajectory. Frontend/dashboard and PDF reports present the sequence prediction separately from per-visit structural proxies. Changing the viewed MRI does not change the completed sequence's prediction.

The saved threshold is approximately 0.514227 and was selected on validation balanced accuracy. The reused eight-person test set gave 25% accuracy, 33.3% balanced accuracy and ROC-AUC 0.0833 at that threshold; majority prediction gave 75% accuracy. The score is uncalibrated and this checkpoint has poor generalization. These limitations are prominent, not hidden behind the percentage. Scores on the original forty subjects are in-sample demonstrations.

No future Alzheimer probability, 12/24/36-month forecast, confidence interval, segmentation or Grad-CAM is produced. Intensity-difference overlays and foreground/feature-change values remain separate, explicitly nonregistered image proxies. nWBV/eTIV are observed source measurements.

## Frozen-cohort import

From the root, with the existing host PostgreSQL and environment:

```powershell
.\.venv\Scripts\python -m scripts.verify_multimodal_run data/training_multimodal/runs/20261001T134908Z
.\.venv\Scripts\python -m scripts.import_oasis --training-cohort
.\.venv\Scripts\python -m scripts.predict_training_cohort
```

The first command audits the original run against raw MRI and workbook fingerprints. The second verifies the source workbook/frozen cohort, imports all visits of exactly the forty training subjects and enriches existing OASIS metadata. It never replaces MRI, splits, accounts, checkpoints or analyses. Validation/test subjects are not imported by this training-cohort option. Existing unrelated cases remain present.

With exactly one updated worker running, the third command queues missing trained results for the forty subjects and verifies their scores against the saved run (tolerance 1e-6). It requires exact database visit coverage and covariate snapshots, prints aggregate progress only, and saves `data/qa-trained-integration.json`. `--verify-only` performs read-only comparison of current results. This command neither retrains nor measures generalization.

To enrich previously prepared five-case metadata without changing that cohort, run `python -m scripts.import_oasis --refresh-covariates`. Never combine `--training-cohort` with `--all` or an alternative manifest. Do not use training-set accuracy to choose different patients or claim generalization.

## Verification

Unit tests use synthetic checkpoint bundles and isolated databases, not production participants. They exercise exact checkpoint/preprocessor inference, changed/missing bundles, label exclusion, eligibility, null-vs-absent covariates, source preservation, empty trained trajectories, safe worker failure, researcher ownership and PDF/UI provenance. Run the checks in [07 Testing and validation](07-testing-validation.md). A live verification must reproduce the saved training scores after import without fitting or tuning on them; that is an integration regression check, not an accuracy experiment.
