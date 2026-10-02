# OASIS-2 data and forecast scope

## Sole project dataset

This project uses only the OASIS-2 MRI archive and its supplied demographics
workbook/CSV. Do not acquire, merge, or depend on another research dataset for
model inputs, labels, or validation. Preserve the supplied raw archives outside
source control. Imported scans and generated artifacts stay in managed local
storage, and source MRI files remain immutable.

The audited source contains 150 subjects, 373 visits and 1,368 paired acquisitions.
All MRI identifiers match the supplied workbook. Fifty-six subjects have at least
three visits. The importer selects one acquisition per visit, preferring `mpr-1`,
and orders visits using the recorded `MR Delay`. Missing SES and MMSE measurements
remain missing. See [the data contract](03-data-contract.md).

## Supported target and predictors

The baseline forecasting study uses each eligible subject's earliest recorded
CDR-zero visit. Later CDR observations establish whether and when an observed CDR
increase occurred. They are labels only and never enter baseline predictors.
Supported source demographics include age, sex, education, SES, MMSE, eTIV, nWBV,
ASF, visit and recorded timing. Reviewed FastSurfer regional measurements can be
added as a matched MRI feature set. IDs, `CDR` and outcome-derived `Group` are not
predictors.

This endpoint predicts observed CDR conversion in this cohort. CDR or `Group` does
not establish MCI or an Alzheimer-specific dementia diagnosis. Do not describe its
output as diagnosing Alzheimer disease. Strict event counts, censoring and eligible
horizons are specified in the frozen cohort and label files; unknown follow-up
remains unknown. Unsupported horizons return no prediction.

The separate retrospective 40/8/8 model uses its frozen OASIS-2 sequence and
observed first-to-last CDR-increase target. Its poor reused-holdout performance and
in-sample scores are documented in [trained inference](14-trained-inference.md).
It does not predict future Alzheimer diagnosis or future 3D anatomy.

## Training and evaluation rules

- Use the supplied OASIS-2 files only; preserve source dictionaries and identifiers.
- Link MRI, metadata and outcome records by the supplied subject/MRI identifiers.
- Split by subject before feature fitting; keep a frozen test split.
- Fit imputation, scaling, feature selection and model settings on training/development
  subjects only.
- Compare clinical-only and matched clinical-plus-reviewed-MRI models on the same
  subjects. Report per-horizon events, nonevents and unknowns.
- Use later visits only to construct outcomes. Do not use follow-up `Group`, future
  MRI, or measurements derived from a later scan as baseline predictors.
- Suppress unsupported outcomes; report no metric when its class support is absent.
- Keep observed values, model estimates, illustrative data and unavailable outputs
  explicitly distinguished in the app and reports.

Current real-data blockers are reviewed segmentations, score/alignment review,
outcome support, and matched held-out MRI added-value evidence. These are evidence
gates, not a request to source more datasets. See [current blockers](blockers.md).
