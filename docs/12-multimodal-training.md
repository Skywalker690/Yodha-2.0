# Multimodal demonstration training

## Objective and data

Train the small 3D MRI encoder, demographic MLP, LSTM and classification head together on the original 40 training subjects. This offline experiment implements the trained-model tier in the product's research plan. A separately requested experimental integration now exposes the audited checkpoint through Trained mode; see [14 Trained inference](14-trained-inference.md). Training itself still runs offline, never inside an HTTP request.

The exact saved assignments in `data/training/subject_split.csv` are validated against the workbook and raw MRI inventory. The runner rejects leakage, missing/duplicate visits, changed CDR labels, changed dates and wrong split counts. Visit sequences include every available scan in MR Delay order, selecting one acquisition per visit (`mpr-1` where available).

| Split | Subjects | Actual MRI visits | CDR-increase subjects |
|---|---:|---:|---:|
| Training | 40 | 132 | 6 |
| Validation | 8 | 29 | 2 |
| Test | 8 | 24 | 2 |

The 185 visits are across all three splits. Only 132 visits contribute gradients. The 40 subjects constitute 40 training sequences, rather than 132 independently labeled people.

## Workbook columns

| Columns | Use |
|---|---|
| Age, EDUC, SES, MMSE, eTIV, nWBV, ASF | Numeric inputs at each visit |
| MR Delay, Visit | Recorded scan timing and ordinal inputs |
| M/F, Hand | Categorical inputs with explicit missing/other categories |
| Subject ID, MRI ID | Join and audit keys only |
| CDR | Outcome: last recorded CDR greater than first recorded CDR |
| Group | Excluded: outcome-derived status label |

All 15 workbook columns have a documented role. The 11 usable covariates become 27 encoded features (9 numeric, 9 missingness flags, 9 categorical indicators). Handedness is present even though every subject in this supplied dataset is right-handed. Missing SES/MMSE remain missing in source metadata; their model inputs use training-visit medians plus explicit missingness flags. Never convert malformed or infinite measurements into missing values silently.

Numeric medians, means and scales are fitted on the 132 training visits and reused unchanged for validation/test. The fit subject IDs and statistics are saved. Standardization and imputation must learn from the training split only, following [the official leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

## MRI and architecture

Source paired NIfTI files are validated, reoriented to canonical RAS, percentile-normalized independently per volume, and resized to a `64 x 64 x 64` float32 input. Source files remain immutable. Shared cache keys fingerprint both MRI files and the preprocessing version; cached data are checked for shape, dtype, finite values and intensity range. This is shape normalization, not anatomical registration, segmentation or hippocampus measurement.

Each actual visit yields 32 learned MRI features and 16 learned demographic features. Their concatenation feeds a 16-unit LSTM and a binary logit head. Packed sequences ignore padded visits; padded images are not processed by the encoder. All branches are optimized end-to-end.

## Run and artifact inspection

From the root with the existing virtual environment:

```powershell
.\.venv\Scripts\python -m scripts.train_multimodal_model --epochs 40 --min-epochs 15 --patience 8 --batch-size 4 --threads 4
```

Use `--output-dir` to name a fresh experiment directory. Nonempty directories are rejected so old checkpoints/results are preserved. `--split-manifest` points to the frozen original split; retraining does not assign new subjects. A small batch size bounds RAM use on this machine. Source hashes and preprocessing caches are shared across runs. Initialization is reseeded after caching so a cold cache cannot change model initialization.

Optimization uses AdamW (`lr=0.001`, `weight_decay=0.0001`), training-derived positive-class weight (`34/6`), gradient clipping and deterministic seeded ordering. Every epoch processes each of the 40 training subjects once, with ten updates at batch size four. Checkpoint selection minimizes class-weighted validation BCE. Train for at least 15 epochs, with a maximum of 40 and patience of eight epochs. A later best checkpoint can therefore come from an earlier epoch; forcing the last epoch is not model selection.

Each run directory contains:

- `subject_split.csv`: exact original manifest copy.
- `provenance.json`, `preprocessing.json`, `mri_sources.json`: schemas, training IDs, statistics, software versions and source hashes.
- `history.json`: validation metrics, timing, optimizer steps, every subject ID seen and visit coverage per epoch.
- `multimodal_model.pt`: best validation-selected weights, feature/preprocessing schema and threshold.
- `last_checkpoint.pt`: final epoch weights, optimizer state and RNG state for future resume tooling.
- `predictions.csv`: one score per subject, split, actual target and predictions at both thresholds.
- `metrics.json`: confusion matrices, accuracy, precision, recall, specificity, F1, balanced accuracy, ROC-AUC, Brier score and cross-entropy; majority baseline; branch weight-change audit.
- `status.json`: completion and checkpoint/preprocessing round-trip verification.

All artifacts are ignored by Git. Previous MRI-only and first multimodal checkpoints are retained.

## Evaluation scope

Report both the fixed 0.5 threshold and a threshold selected on validation balanced accuracy only. Test subjects never choose an epoch, scaler, class weight or threshold. Compare against a constant classifier fitted to the training positive prevalence. Undefined precision (no positive predictions) is recorded as null rather than silently inventing a value.

The test subjects have already been evaluated during earlier MRI-only and multimodal experiments, so they are a reused holdout. Eight subjects with two positives cannot establish stable generalization or clinical performance. The runner verifies that serialized preprocessing and a freshly loaded checkpoint reproduce saved scores.

Because the input includes MRI/MMSE/nWBV from the final visit, this is **retrospective recognition of observed CDR change**, not prediction of future progression before that visit. A forecasting experiment would require a separate, explicit temporal cutoff and target contract. Class weighting makes scores uncalibrated; do not present them as disease probabilities.

## Verification

```powershell
.\.venv\Scripts\python -m ruff check backend ml scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m scripts.verify_multimodal_run data/training_multimodal/runs/<run-id>
```

The multimodal tests exercise training-only preprocessing, target/identifier exclusion, all-missing/constant/unknown features, split corruption, padding invariance, gradients in both modalities, exact minibatch coverage and known confusion/AUC cases. CPU reproducibility follows the [PyTorch determinism guidance](https://docs.pytorch.org/docs/2.14/notes/randomness.html); results across different software/hardware versions are not promised to be bit-identical.

The read-only `verify_multimodal_run` audit rechecks raw MRI/workbook fingerprints, saved split and per-epoch coverage, training-only statistics, validation-derived threshold, predictions for all splits, and branch weight changes from seeded initialization. It does not retrain or choose a new checkpoint.
