# Fixed-reference future anatomy

D046 explicitly reuses this saved candidate for unvalidated patient-specific
forecasts, without refitting or promotion. Four training subjects, one selection
subject and one test subject participated. This compatibility mode keeps v3's
original fixed reference and is separate from the current v4 training direction.

Historical v3 experiment, superseded by D044 for new forecasts. See
[20](20-training-reference-anatomy-run.md). Its full coordinator was stopped
before fitting; the handoff and prepared data are preserved. The metrics below
remain actual v3 results and must never be relabeled as v4 performance.

The user's correction in D043 requires the supplied fixed age-group reference,
not means/SDs estimated from the current training subset. Use
`Z = (patient nWBV - fixed age-bin mean) / fixed age-bin sample SD`.
The original bundled profile describes 85 OASIS-2 baseline-CDR-zero subjects.
It is a supplied research reference, not an independently validated population
norm; possible overlap with held-out OASIS subjects is disclosed in evaluation.
The previous training-only-reference candidate is preserved separately.

## Exact inputs

`anatomy-input-v3-fixed-age-reference` has 129 numeric conditioning columns:

- Requested future interval in years, history duration in years and visit count.
- Four actual elapsed scan intervals in days, most recent first; absent slots
  remain missing, with training-only imputation and missingness indicators.
- For each of 18 FastSurfer regions: latest statistics volume (mm3), cumulative
  history change (mm3 and percent), OLS volume rate (mm3/year), most recent
  annualized change (mm3/year and percent/year), using actual MR Delay.
- Latest observed age-reference nWBV Z-score and MMSE.
- For left MTA, right MTA and Koedam posterior atrophy: latest AVRA estimate,
  cumulative history change, OLS rate/year and last annualized change/year.

The 18 regions are bilateral hippocampus, lateral ventricle, entorhinal,
inferior parietal, inferior temporal, middle temporal, precuneus, superior
parietal and superior temporal. Definitions/labels remain `dkt-longitudinal-v1`.
FastSurfer supplies volumes; AVRA supplies continuous atrophy estimates.
Statistics-derived mm3 and categorical mask voxel-volume mm3 are separate.

The spatial network additionally receives six image channels: normalized latest
acquired T1, voxel-wise OLS intensity rate across all cutoff-registered acquired
MRIs, hippocampal mask, ventricular mask, cortical-label mask and brain-label
mask. It uses full categorical labels for the 18-region consistency loss.
Earlier images register only to the latest observed cutoff; hidden later scans
construct supervision/evaluation only. The network outputs physical RAS-mm pull
displacement and uses actual forecast time. Labels use nearest-neighbour warping.

Each scalar/spatial preprocessing path uses its training-only medians/scales
and one missingness indicator per conditioning column. An all-missing training
column uses a documented constant zero plus the indicator, never raw nWBV.
Age/raw nWBV are retained only to calculate Z and display provenance; EDUC, SES,
sex, handedness, eTIV and ASF never condition these models. Existing eTIV ratios
are descriptive preprocessing outputs only. No CDR/Group predictor is added.

Fixed constants retain the supplied minimum reference-bin size of 10. Ages
65–89 have supported bins; 60–64 and 90–94 are sparse, other ages unsupported.
Invalid/missing measurements remain explicit unavailable states. No reference
mean/SD is recomputed during selection, calibration, testing or inference.

The full source-data availability audit finds 336 of 373 visits with numeric Z,
33 visits in sparse bins and four visits outside supported ages. At baseline,
137 of 150 subjects have numeric Z; 12 have sparse bins and one an unsupported
age. Across any recorded visit, 141 subjects have at least one numeric Z and nine
have none. The audit is saved as `all-patient-z-availability.json` in the partial
run. The current dashboard card reads the completed analysis for its matching
visit; an unprocessed visit or a historical result without the reference object
can still display unavailable even when source metadata supports calculation.

## Real execution

Local header/file-size audit: 150 subjects, 373 visits, 1,368 paired acquisitions,
all matched to metadata, zero detected header/size issues. This is not complete
voxel/segmentation quality validation. Fifty-six subjects have at least 3 visits.

The frozen study remains 44 train / 4 selection / 4 calibration / 4 test.
Six completed, integrity-verified source histories supplied 16 prepared 96-cube
examples. Reuse copies checked registration arrays into a fresh study and updates
only source-bound measurements/review annotations when physical sources match.
Earlier runs and raw data are preserved. User-added visits outside the frozen
source cohort do not change its cutoffs.

Fresh fixed-reference run: `artifacts/anatomy-fixed-reference-partial-20261002/`.
Training uses OAS2_0048, OAS2_0070, OAS2_0127 and OAS2_0027 (11 examples);
OAS2_0017 supplies selection (2 examples); OAS2_0073 supplies test (3 examples).
No calibration subject is ready. The former provisional reassignment of OAS2_0027
is removed. All 16 examples have available fixed-reference Z-scores.

Actual training: 20 epochs on the RTX 3050, pinned CUDA image
`sha256:3e0d9558197c37ae861721e34d9e4c97b1ff6f7cd073692c4e26e70de3bc0049`.
Selection chose epoch 1 from the completed 20-epoch run. The candidate contains
`with_scores.pt`, `with_scores.json`, `nwbv-reference.json`,
`preprocessing.json`, per-epoch logs and `evaluation.json`. Both checkpoints bind
the same reference and input names. Older v1/v2 checkpoints fail explicitly.

Held-out regional mean MAE across 18 regions and three hidden scans:
441.731 mm3 learned model; 275.282 mm3 no change; 465.092 mm3 individual linear trend.
Learning-grid spatial Dice 0.801763, ASSD 0.474077 mm and HD95 2.590400 mm,
equal to no-change categorical predictions at that grid. This does not mean the
network has become a no-change serving fallback. It indicates no measured spatial
improvement in this tiny evaluation. Full per-region errors are saved in the report.

Only one test subject is evaluated. Actual test intervals are 229, 583 and 1,125
days, not assumed yearly scans. No 183/365/731/1096-day horizon meets the predefined
subject support guards. Calibrated uncertainty is unavailable. This reused OASIS
holdout and supplied reference cannot establish independent or clinical validation.

Native evaluation uses the actual forecast generation path, including mask/scalar
consistency, Jacobians, coverage and 19 physical mesh checks. Its saved report is
authoritative for the current status. Native baseline comparisons are recorded
even when the learned artifact export fails. Spatial individual linear trend uses
the last acquired MRI pair's physical displacement per actual elapsed day;
invalid coverage/folding remains unavailable rather than clipped.

Actual native result: one of three hidden futures passed complete artifact generation,
OAS2_0073 at +229 days. It produced 40 artifacts including 19 meshes at
`candidate/native-test/8/`, plus an exact zero-time check in `8-zero/`.
Minimum Jacobian is 0.972236; zero-time minimum is 1.0. Maximum mask/scalar change
discrepancy is 4.4225 percentage points. On this successful case only, mean Dice
is 0.844102, ASSD 0.387553 mm and HD95 1.083333 mm. The +583 and +1125-day cases
failed the 12-percentage-point mask/scalar consistency gate; they are not discarded
from the release decision. Overall native status is **failed**. Individual spatial
linear extrapolations fail full MRI coverage and remain explicitly unavailable.
These generated files are retrospective native evaluation artifacts, not promoted
forecasts published in the patient viewer. The app reports forecasting unavailable.

D045 now makes this exact +229-day example visible on the separate `/preview`
page with its original subject, cutoff, failed candidate status and unvalidated
retrospective provenance. It is a saved-artifact preview, not a promoted forecast
or a replacement for a requested 365-day patient prediction.

## Remaining workflow

Resume the existing single worker only when no other worker is active. A fresh
full-cohort coordinator can reuse prepared cases without changing old runs:

```powershell
.venv/Scripts/python -m backend.app.workers.runner
.venv/Scripts/python -m scripts.run_anatomy_training --cohort artifacts/anatomy-score-study-20261002 --output artifacts/anatomy-fixed-reference-full-20261002 --epochs 20 --device cuda --grid-size 96 --training-image sha256:3e0d9558197c37ae861721e34d9e4c97b1ff6f7cd073692c4e26e70de3bc0049 --reuse-prepared artifacts/anatomy-input-v2-partial-20261002/study
```

The coordinator waits for all frozen anatomy/AVRA outputs before full fitting and
native evaluation; its status/logs persist under the fresh directory. Resume only
with the same feature contract/reference/runtime/settings. The Docker command
adds the vendored package source to PYTHONPATH; the host anatomy requirements now
install that package. Do not start competing GPU jobs.

At the partial-run boundary, 50 complete subject histories remain unprocessed,
calibration is absent, horizon support fails and the scalar model underperforms
no change. Visual segmentation/alignment/registration review and independent AVRA
rating agreement also remain unverified. No partial candidate is promoted.
Future worker/viewer generation requires supported intervals and passing native
geometry; unavailable outputs have no illustrative or historical-classifier substitute.

Software checks establish implementation behavior only, never forecast accuracy.

The fresh full-cohort coordinator and single worker were actually started on
2026-10-02. At startup: six completed subjects, one processing, 49 queued, no failed
or missing study jobs. Its `pipeline-status.json` is the current execution record;
the full 44-subject fit and its held-out results remain pending. Preserved runs are
not resumed under a changed feature/reference contract.
