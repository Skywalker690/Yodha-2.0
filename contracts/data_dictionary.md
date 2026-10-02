# Baseline forecast contracts

Authoritative Python request/result validation is in `src/contracts.py`; JSON schemas
are exported mechanically with `python -m scripts.export_forecast_contracts`.

All subject-level tables and trained parameters live in ignored local directories.
`patient_id` and `scan_id` are join keys, never predictors. The endpoint is
`observed_cdr_conversion`, not a diagnosis. See [cohort definition](../docs/cohort_definition.md).

| Table | Grain and required content |
|---|---|
| baseline.csv | One CDR-zero baseline per subject; baseline_day, scan_id, age_years, sex, education, ses, mmse, cdr, etiv, nwbv, asf |
| manifest.csv | One baseline scan per subject; source_mri_path, tensor_path, scan_qc, preprocess_version |
| labels.csv | One subject; event_observed, event_month, last_event_free_month, y12/y24/y36, reversion_after_event |
| split.csv | One subject; train/validation/test, seed, split_version |
| fastsurfer_features.csv | One subject/scan; version, feature_set_version, qc, digest, exact mm³ features |

Calendar baseline_date is null because the supplied workbook provides relative days,
not calendar dates. Sex encoding is F=0/M=1; education is years; SES is recorded ordinal
class; MMSE is 0–30; CDR-zero is constant in this cohort. OASIS-2 eTIV is retained in
source cm³ (equivalent to mL), not mm³; FastSurfer anatomical features are mm³.
The [original OASIS-2 publication's data dictionary](https://pmc.ncbi.nlm.nih.gov/articles/PMC2895005/)
documents the source units. No factor-of-1000 conversion is silently applied.
nWBV and ASF are unitless. Missing recorded SES/MMSE remain missing until train-only
imputation. Never synthesize anatomy or treat unknown horizon labels as negatives.

The request baseline allows exactly these clinical predictors. Outcome fields, future
visits, IDs and Group are rejected as features. The adapter returns every horizon,
using null when unsupported; raw and monotonically adjusted estimates are distinguished.
