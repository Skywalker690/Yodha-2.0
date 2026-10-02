# OASIS-2 nWBV age-reference module

This folder is a portable Python package for an **optional descriptive nWBV card** in the existing Yodha/NeuroPredict analysis workspace. It implements and corrects the age-bin calculation in the pasted proposal. It does not score MCI, Alzheimer disease, or future risk, and it does not generate a future MRI.

## Default role: support value

The module is intentionally configured for **support-value use by default**. The Z-score is displayed as age-adjusted context beside the other MRI and clinical outputs. It is not automatically passed into the CDR, regional-volume, or future-anatomy model. This keeps the integration independent and prevents a descriptive calculation from silently changing the model’s feature schema.

If the research team later wants to test the Z-score as a feature, that is a separate experiment. Build the age-bin reference inside each training fold using training patients only, transform both the training and validation patients with that reference, and compare against the same model without the Z-score. The bundled whole-cohort reference is not permitted for cross-validated feature training.

The current workspace has the OASIS-2 CSV and MRI data but does **not** contain the prototype repository named in `IMPLEMENTATION_PLAN.md`. The package therefore exposes a small Python interface and a versioned result object for your friend's existing worker, without changing that application.

## What the plan verification found

The pasted code's arithmetic reproduces the local CSV: `Group == Nondemented` and baseline visit yield 72 people, with age-bin counts `6, 13, 15, 16, 10, 10, 2`. For age 73 and nWBV 0.690, its rounded table yields a Z-score near **-1.596**. The calculation is correct; the clinical labels are not established by it.

The uploaded implementation plan calls for longitudinal masks, MTA/Koedam estimates, regional change, structural forecasting, and future anatomy. This package is only an **additional source-provided biomarker comparison** that can appear beside those results. It cannot replace any of those tasks or supply the geometry needed by the 3D predictor.

Key corrections to the proposal:

1. `Group == Nondemented` identifies people who remained nondemented through follow-up, so it uses a future-informed grouping to define a baseline reference. The bundled profile instead uses **Visit 1 and baseline CDR 0**, a status known at that visit. This yields 85 subjects.
2. The 60–64 bin has 6 people and the 90–94 bin only 2. The runtime returns `insufficient_reference` for bins with fewer than 10 people. Ten is a conservative software rule, **not** a clinically validated cutoff.
3. OASIS nWBV was produced by a specific atlas-based tissue-segmentation procedure. The local CSV stores values as fractions, for example `0.744` for 74.4%. A FastSurfer volume divided by eTIV or a SynMRI measurement cannot be assumed equivalent. The runtime requires the exact measurement-method ID. [Original OASIS-2 methods and data dictionary](https://pmc.ncbi.nlm.nih.gov/articles/PMC2895005/).
4. A normal-CDF percentile assumes a normal reference distribution within each small bin. That assumption was not validated here, so the module does not return a percentile.
5. The pasted “Low/Moderate/High” risk categories and claims of MCI or pathological atrophy are unsupported by this Z-score. The output uses **descriptive standard-deviation bands** and always leaves `clinical_risk` null. An MRI volume may contribute to clinical evaluation, but brain shrinkage alone does not determine a specific diagnosis. [National Institute on Aging](https://www.nia.nih.gov/health/biomarkers-dementia-detection-and-research).

## Bundled reference

The included `data/oasis2_baseline_cdr0_v1.json` is generated from the local source CSV using the package builder. It contains only aggregate bin statistics and a source SHA-256 fingerprint. It contains no subject records, scan data, or trained weights.

| Age | Subjects | Mean nWBV fraction | Sample SD | Runtime status |
|---|---:|---:|---:|---|
| 60–64 | 6 | 0.801667 | 0.016705 | Insufficient reference |
| 65–69 | 16 | 0.776375 | 0.033945 | Available |
| 70–74 | 16 | 0.744000 | 0.032408 | Available |
| 75–79 | 19 | 0.736105 | 0.027638 | Available |
| 80–84 | 13 | 0.724692 | 0.029386 | Available |
| 85–89 | 13 | 0.719538 | 0.025484 | Available |
| 90–94 | 2 | 0.699500 | 0.002121 | Insufficient reference |

These are local **research-cohort summaries**, not population norms. The bins and score have not been externally validated. The sample spread uses `N-1` in the denominator.

## Install in your friend's backend environment

From the destination repository root, after copying this whole folder into a location such as `vendor/nwbv_reference_module`:

```powershell
python -m pip install --no-deps .\vendor\nwbv_reference_module
```

The runtime has no third-party dependencies. The installation includes the aggregate JSON reference.

## Call the module from the existing analysis worker

Call it **after** the existing import/measurement step has supplied age and the source CSV's nWBV for the same visit. Keep the result separate from the established disease models and from regional FastSurfer outputs.

```python
from az_nwbv_reference import NwbvReference, OASIS2_NWBV_METHOD

reference = NwbvReference.bundled()  # load once at worker startup

def add_nwbv_reference(visit, result):
    # Example mapping; adapt names to the existing visit and biomarker contracts.
    if visit.get("nWBV") is None or visit.get("Age") is None:
        result["nwbv_age_reference_v1"] = {
            "status": "missing_input",
            "task": "descriptive_age_reference",
        }
        return result
    # Use typed values from the existing importer; avoid silently coercing bad data.
    result["nwbv_age_reference_v1"] = reference.evaluate(
        age=visit["Age"],
        nwbv=visit["nWBV"],
        measurement_method=OASIS2_NWBV_METHOD,
    )
    return result
```

Only use `OASIS2_NWBV_METHOD` when the value is the imported OASIS-2 CSV nWBV. For any new MRI-derived measurement, pass its actual method ID. The scorer will return `method_mismatch` until you establish measurement comparability and create a new validated reference profile.

### If your system computes a new nWBV value

If the new system uses SynMRI, FastSurfer, or another pipeline to compute a whole-brain fraction, **do not label that number as the OASIS source method**. The practical path is:

1. Run the same production measurement pipeline on the OASIS baseline scans for the reference subjects, preserving subject ID, baseline CDR, age, and source/QC records.
2. Confirm that its output has a clearly defined whole-brain fraction on the interval `(0, 1)` and that failed/low-quality measurements are reviewed. A volume in `cm³` or `mm³` is not an nWBV fraction.
3. Prepare a new CSV with `Subject ID`, `Visit`, `MR Delay`, `CDR`, `Age`, and a distinct metric column such as `SynMRI_nWBV_fraction`.
4. Generate a new reference with an explicit method and profile ID, then review its counts and measurement comparability:

```powershell
python -m az_nwbv_reference.builder `
  --csv '.\derived_synmri_metrics.csv' `
  --metric-column SynMRI_nWBV_fraction `
  --measurement-method synmri_nwbv_fraction_v1 `
  --profile-id oasis2_synmri_baseline_cdr0_v1 `
  --output '.\oasis2_synmri_reference_v1.json'
```

Load that profile with `NwbvReference.from_file(path)` and pass `measurement_method="synmri_nwbv_fraction_v1"` when evaluating a patient measured by the same SynMRI pipeline. This only makes the comparison **method-matched**; it does not establish clinical norms, risk thresholds or diagnostic accuracy. Do not use a profile built from held-out test subjects as a feature inside a forecasting evaluation.

In the existing application, place the call in the analysis worker after visit metadata is loaded, persist it as an optional versioned biomarker result, and show a descriptive card in `analysis-workspace.tsx`. The UI should display the age bin, reference count, nWBV value, Z-score if available, measurement method, and the text **“Research-cohort comparison; not a diagnosis or future risk estimate.”** If status is not `ok`, display the status and reason with no colored risk badge. No database migration is needed if the current result JSON can store this optional field.

Use the result field `intended_use="support_value"` to keep this behavior explicit in the backend contract. The result also includes `feature_use_allowed=false`; the application should not use this runtime result as a training feature. A future fold-aware trainer may create a separately named feature artifact and model version after evaluation.

## Result contract

Successful example for source-compatible age 73, nWBV 0.690:

```json
{
  "schema_version": 1,
  "metric": "nWBV",
  "task": "descriptive_age_reference",
  "intended_use": "support_value",
  "feature_use_allowed": false,
  "status": "ok",
  "age_years": 73,
  "nwbv_fraction": 0.69,
  "z_score": -1.666,
  "relative_volume_band": "between_1_and_2_sd_below_reference_mean",
  "clinical_risk": null
}
```

The real result also includes reference method, source hash, reference age bin and exact floating-point Z-score. The example rounds the Z-score only for display. Supported statuses are `ok`, `insufficient_reference`, `unsupported_age`, `method_mismatch`, and `invalid_input`.

## Rebuild the aggregate reference

Use the source CSV only in your data preparation environment. The package does not need it at runtime. From this module directory after installation:

```powershell
python -m az_nwbv_reference.builder `
  --csv '..\oasis_longitudinal_demographics-8d83e569fa2e2d30(Sheet1).csv' `
  --output '.\src\az_nwbv_reference\data\oasis2_baseline_cdr0_v1.json'
```

Review the source hash, counts and age-bin statistics before replacing a deployed reference. Changing the CSV, cohort rule, measurement process, bin width, or minimum count requires a new profile version. Do not silently overwrite the deployed model or its provenance.

## Boundary with the implementation plan

- **Data/worker:** consume the current import and worker; no second patient database or MRI importer.
- **Reports/UI:** present this as an optional source-provided biomarker comparison, alongside MTA/Koedam and regional-change results when those are independently available.
- **Forecasting:** do not use this all-subject aggregate as a feature when evaluating a model on held-out OASIS subjects. A training fold would need a reference built without those held-out subjects. The existing future-anatomy model must continue to use measured regional histories and evaluated spatial prediction methods.
- **Feature experiment:** if the team later promotes the Z-score to a feature, create a new fold-aware feature pipeline and a new model version. Do not alter the support-value contract or reuse its whole-cohort reference.
- **QC:** preserve the existing review gates. `status: ok` means the arithmetic is supported by this reference profile; it does not mean that the MRI, segmentation, or clinical result received visual approval.

## Sources

- [OASIS-2 original study and definitions](https://pmc.ncbi.nlm.nih.gov/articles/PMC2895005/)
- [National Institute on Aging: what imaging biomarkers can and cannot establish](https://www.nia.nih.gov/health/biomarkers-dementia-detection-and-research)
- The project's `IMPLEMENTATION_PLAN.md`, supplied with this handoff
