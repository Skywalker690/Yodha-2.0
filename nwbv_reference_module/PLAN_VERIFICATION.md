# Verification of the pasted nWBV proposal against IMPLEMENTATION_PLAN.md

## Verified calculation

The pasted Python filter selects 72 baseline rows in the local CSV. Its seven 5-year bins contain `6, 13, 15, 16, 10, 10, 2` records, and its listed means and sample standard deviations match the source. For age 73 with nWBV 0.690, `(0.690 - 0.742200) / 0.032707 = -1.596` after rounding, as shown in the paste.

The CSV fingerprint used to build the bundled profile is:

```text
d2f0a15ff35fa4a65c35c064b848fc1b396e9d2f4aec935c88d6e1588d31d40e
```

## Changes needed before application integration

| Pasted element | Assessment | Implementation in this package |
|---|---|---|
| `Group == Nondemented` reference | `Group` distinguishes people who stayed nondemented over follow-up from those later marked `Converted`; it is not just a baseline measurement. | Use Visit 1, MR Delay 0, CDR 0. This yields 85 patients and names the cohort accurately. |
| All seven bins scored | The 60–64 bin has 6 patients; 90–94 has 2. The latter SD is especially unstable. | Return `insufficient_reference` where `n < 10`; expose count and no Z-score. |
| Z-score arithmetic | Mathematically correct for the selected mean and sample SD. | Preserve arithmetic, full precision and source provenance. |
| Normal-CDF percentile | Requires a normal-distribution assumption that is unverified in these small bins. | Omit percentile. |
| `0.50–0.95` as a physiological acceptance range | The proposal supplies no validation for those exact endpoints. | Validate a finite numeric fraction strictly between 0 and 1; source and MRI QC remain separate. |
| SynMRI nWBV used against OASIS nWBV | No equivalence study is provided. OASIS used a particular atlas/mask/FSL tissue workflow, so even similarly named quantities may differ. | Require `oasis2_csv_nwbv_fraction_v1`; reject other methods until a matched reference is established. |
| Low/Moderate/High risk and MCI/pathological atrophy claims | A whole-brain volume Z-score cannot establish these clinical outcomes. | Emit descriptive volume bands only; `clinical_risk` is null. |
| Direct replacement of the application model | The updated plan requires MTA/Koedam, regional metrics and an evaluated future-anatomy model. | Integrate only as an optional source-provided biomarker card. |
| Z-score role in the MVP | The score is derived from age and nWBV and is not independently validated as a predictor. | Default to `intended_use=support_value`; do not pass it into production or research training automatically. |

For the new CDR-0 reference, age 73 and nWBV 0.690 yield a Z-score near **-1.666**. The difference from the pasted -1.596 reflects the reference-cohort change, not a change in formula.

## Place in the updated plan

- **Task 1:** attach the package to the existing visit metadata and analysis worker; avoid new ingestion paths.
- **Task 4:** display the result beside nWBV/MMSE/CDR history while preserving its `source_provided` origin and exact measurement method. The age-reference card does not replace longitudinal change in nWBV or measured regional volumes.
- **Task 5:** keep the bundled Z-score as a support value. A later feature experiment must recompute the reference without held-out patients in each training fold and receive a new feature/model version. The bundled whole-cohort table is for descriptive display, not an input to cross-validated forecasting.
- **Tasks 2, 3 and 6:** FastSurfer segmentations, AVRA MTA/Koedam scoring and spatial future-brain forecasting remain separate work with their own artifacts and validation.
- **Tasks 7–8:** store an optional versioned result, show unavailable states, and keep diagnostic and forecast claims out of this card.

## Evidence and limitations

The original OASIS-2 publication describes the nWBV measurement process and distinguishes the participants stable at CDR 0 from those whose later status changed. It defines nWBV as tissue proportion within an atlas-derived mask; the local CSV represents that proportion with decimal fractions. [OASIS-2 methods and variable dictionary](https://pmc.ncbi.nlm.nih.gov/articles/PMC2895005/).

The National Institute on Aging explains that observed brain shrinkage can support evaluation but does not establish a specific dementia diagnosis. [NIA biomarker guidance](https://www.nia.nih.gov/health/biomarkers-dementia-detection-and-research).

This package's `n >= 10` rule is an engineering rule to avoid publishing extreme Z-scores from very small bins. It is not an externally validated normative threshold. Even the available bins contain only 13–19 subjects, from one research cohort and imaging pipeline. The reference needs independent validation before broader use.
