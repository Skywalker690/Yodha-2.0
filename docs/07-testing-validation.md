# Testing and Validation

## Guided assessment entry restored above MRI (D084)

The production frontend build, including TypeScript, and diff whitespace checks
pass. Live browser inspection of the uploaded `RESEARCH_001` case confirms the
existing assessment card and Resume action now appear between patient navigation
and MRI. Reopening its saved draft displays the original eleven-task guided demo,
the first unanswered task, scoring choices, clinician guide and save/continue
controls. The existing completion dialog code is unchanged. SHA-256 comparisons
confirm the MRI viewer, MRI styles, score/API types, resource/API helpers and
backend assessment service remain unchanged. The ignored screenshot
`artifacts/alzhio-guided-assessment-restored.png` captures the open dialog. No
points were entered, assessment saved/completed, patient data modified, automated
test suite run or model job launched.

## Saved cognitive score header display (D083)

The production build, including TypeScript, and diff whitespace checks pass.
Live browser review confirms OAS2_0048's selected baseline has `Recorded MMSE:
19/30` in the patient header and its link scrolls to the existing matching
assessment card. The local screenshot is
`artifacts/alzhio-mmse-score-visible.png` (ignored by Git). Read-only comparisons
confirm the eight protected files remain unchanged: MRI viewer components,
both stylesheets, assessment component, types, resource and API helpers. Header
display reads selected-visit metadata/summary, preserves zero and keeps demo
scores separate. No assessment was started/completed, stored score changed,
automated test suite run or model job launched during this display correction.

## First prototype palette restoration (D082)

The production frontend build, including TypeScript, and diff whitespace checks
pass. Read-only SHA-256 comparison of 70 frontend files confirms that only
`app/patient-dashboard.css` changed in this correction. CSS declaration comparison
confirms that non-palette declarations, including spacing, sizes, typography,
radii, border widths and shadow geometry, remain unchanged. Live browser review
shows original dark navy cards/sidebar and teal accents, with the existing 3D
selection, MRI rendering and yellow hippocampus highlight still present. The
local screenshot is `artifacts/alzhio-prototype-colors-restored.png` (ignored by
Git). No automated tests, patient-data changes or model jobs were performed.

## Patient dashboard design implementation (D081)

Strict TypeScript, the production frontend build and diff whitespace checks pass.
Read-only SHA-256 comparisons confirm eight protected files remain unchanged:
the two MRI viewer components, original global stylesheet, resource/API helpers,
types and both package manifests. The new stylesheet scopes supplementary panel
colors outside the viewer and does not override MRI selectors or root tokens.
Live local browser review confirms the implemented header, grouped visit actions
and section links around the actual acquired MRI viewer. Switching from 3D volume
to the Assessment section and back retains the selected 3D volume mode and the
same viewer controls. This review does not establish persistence across reloads
or patient changes. No automated test suite, patient-data mutation or model job
was performed for this implementation.
The local implementation screenshot is
`artifacts/alzhio-patient-dashboard-implemented.png` (ignored by Git).

## Patient dashboard design template (D080)

Read-only file comparison confirms the two working frontend viewer components,
the isolated preview's matching viewer components, and both existing preview
stylesheets are unchanged (six protected files). The 36 original frontend source
fingerprints also remain unchanged. Browser review shows the compact header,
grouped MRI visit/Add visit controls and four section links, with all link targets
present and the viewer above assessment. The unchanged synthetic MRI canvas and
yellow labels were visually captured. Superdesign draft version 5 was refetched
and exactly matches the imported HTML. The canvas draft uses a static screenshot;
the local preview retains the interactive viewer. No automated tests or real
patient/model operations were run for this design-only change.


## Assessment completion flow (D074)

The user requested checking completion. Five focused frontend tests and four
isolated SQLite API tests pass, covering zero/full scoring, required task
selection, draft/resume, completion retry/revision, persisted separate demo scores
and MRI upload metadata preservation. TypeScript, the production build, Ruff and
diff whitespace checks pass. Live inspection reproduced skipped scoring followed
by a disabled completion action; the updated page requires each task's score and
shows clear guidance. Temporary browser-only inspection scores were discarded;
no real patient score was saved or completed. These synthetic checks establish
workflow/scoring behavior, not clinical instrument validity.

## Diff-based cognitive assessment import (D073)

Fetched `origin/chatbot` at `bd61b54` and reviewed changes after `7165081`;
the two new commits are imported through targeted patches/manual adaptation,
with no merge or cherry-pick. Strict TypeScript, the production frontend build,
focused backend Ruff/Python compilation and diff whitespace checks passed.
The restarted API is online with connected PostgreSQL and all three assessment
routes (POST start/resume, PATCH draft, POST completion). Paired MRI fields and
required age/nWBV remain in its multipart schema. Live browser inspection confirms
the assessment card/action on the existing uploaded patient case and its dashboard
visit selector/source values without completed anatomy or unavailable value cards. No patient
assessment was started/completed, real scores invented, provider calls made or
automated tests added/imported/run. Source branch test results are historical;
the full administered assessment and concurrency flows have not been rerun here.
The ignored preview is `artifacts/imported-cognitive-assessment-20261003.png`.

## Default axial view and hippocampus mask status (D072)

Strict TypeScript, the production frontend build and diff whitespace checks passed.
Live browser inspection of the uploaded `RESEARCH_001` MRI confirmed axial selected
on a fresh workspace mount, a disabled/unchecked hippocampus control and the
segmentation prerequisite with the earlier pending baseline explanation. The
existing measured mask rendering remains enabled by default when available.
The inspected patient has no anatomy job or completed mask; the Docker Linux
engine is unavailable and the running worker only accepts experimental forecasts.
No segmentation was launched, patient data changed or automated tests added/run.
The ignored screenshot is `artifacts/axial-mri-workspace-20261003.png`.

## Paired MRI upload support (D071)

Strict TypeScript, production frontend build, focused Ruff/Python compilation and
diff whitespace checks passed. The restarted API is online; its multipart schema
exposes `file`, `header` and `image` alongside required age/nWBV, with selection
validation enforcing one volume or a complete pair. Browser inspection of an
existing pending baseline confirms `.nii,.nii.gz,.hdr,.img` acceptance, multiple
file selection, pair instructions and preserved age/nWBV defaults. No records
were created, real pairs submitted or automated tests added/run for this change.
This establishes build/startup/UI availability, not a completed real upload or
model-processing run. The ignored screenshot is under `artifacts/`.

## Automatic patient codes and required MRI metadata (D070)

Strict TypeScript, the production frontend build, focused backend Ruff/Python
compilation and diff whitespace checks passed. The restarted API is online and
its OpenAPI contract requires `age`/`nwbvFraction` for new patients and
`file`/`age`/`nwbvFraction` for uploads. Browser inspection confirms the automatic
code explanation and age/nWBV fields. No patient records were created, MRI files
uploaded or automated tests added/run for this change. Historical creation/upload
test fixtures below use the previous contract and require revision before rerun.

## Dashboard available-value cleanup (D068)

Strict TypeScript, the production frontend build and diff whitespace checks passed.
Browser inspection of OAS2_0127's dashboard snapshot confirmed that BMI, total
hippocampus and hippocampal volume change cards are absent, available MTA/Koedam,
asymmetry/reference and source values remain, and sex/handedness display their
recorded text. The empty trajectory card is hidden. No automated tests were added
or run for this change. The local screenshot is ignored under `artifacts/`.

## Main branch integration (D067)

The merge of `feat/ml` at `5eb3818` into `main` completed without conflicts.
The production frontend build, strict TypeScript, Ruff across backend/ML/scripts,
Python compilation and staged whitespace checks passed. The combined application
code matches the merged ML branch; only integration records were added. No
automated test suites were run for this branch integration.

## Combined chatbot/ML build (D066)

The merge of chatbot `7165081` into the ML branch passed the frontend production
build, strict TypeScript, focused backend Ruff, Python compilation and diff
whitespace checks. The restarted local API returned health 200, exposes
`POST /patients/{patient_id}/assistant` and retains the experimental anatomy
forecast request field. The local Gemini key is absent; no provider request was
made and no automated test suites were run for the merge. Existing branch test
evidence below and in document 21 is historical, not a combined test run.

## Local hippocampus illustrations (D062)

Real preparation completed 15/15 illustrations: 365/731/1096 days for each of
OAS2_0048, OAS2_0070, OAS2_0073, OAS2_0127 and OAS2_0017. Every patient's left
and right displayed hippocampal mask volumes decrease across those intervals.
The minimum local Jacobian was 0.503258; maximum scalar/display disagreement
was 0.545061 percentage points. MRI changes outside the local region were zero,
and the exact non-brain head identity guard passed for all fifteen outputs.
Original spatial model artifacts remain unchanged. The private execution report
is `artifacts/hippocampus-forecast-presentations-20261003.json`.

Strict TypeScript, production build and focused Ruff checks passed. Browser
inspection confirmed the regional display, bilateral volume table and annual
scalar estimates on OAS2_0017's 36-month view. No automated tests were run for
this change. These checks establish execution and presentation consistency,
not forecast accuracy, clinical validation or an Alzheimer diagnosis.

## Annual patient forecasts and presentation variants (D061)

Real execution completed 15/15 raw forecasts: 365/731/1096 days for each of
OAS2_0048, OAS2_0070, OAS2_0073, OAS2_0127 and OAS2_0017. Native minimum
Jacobian was 0.2693 and maximum raw mesh/voxel volume error was 4.6891%.
Thin-mask surface refinement resolved the prior 48/127 failures. All bilateral
hippocampal scalar loss estimates increase over these three intervals.

Fifteen additional immutable presentation variants completed. Five permit
enlargement: 48/70 at 12 months use 1.5x; 17 at all three intervals uses 3x.
Ten remain at original scale because greater gains did not pass the display
envelope/geometry checks. Earlier results and raw artifacts remain unchanged.
The explicit 12-percentage-point display allowance is not confidence evidence.
Private execution reports are `artifacts/annual-forecast-batch-20261003.json`
and `artifacts/annual-forecast-presentations-20261003.json`.

TypeScript, production build, focused Ruff and diff whitespace checks passed.
No automated tests or browser interaction checks were run for D061. This verifies
execution and software checks, not predictive accuracy or clinical validation.

## Pending visit deletion (D056)

D057 moves the action beside the MRI visit selector in the marked pending upload
section. TypeScript, production build and focused whitespace checks passed; no
live visit was deleted and no automated tests were run for the placement change.

TypeScript, production build, focused route Ruff and diff whitespace checks passed.
The local API was restarted and its OpenAPI schema exposes `DELETE /visits/{visit_id}`.
No live patient visits were deleted for verification and no automated tests were
run for this change. Follow-up functional checks should cover owned empty deletion,
missing/unowned 404, populated/referenced 409, upload/delete concurrency, automatic
new-visit selection, delete without a selected file and error/reload behavior.

## Acquired hippocampus visibility (D051)

Check preview metadata for matching cutoff/source/segmentation and owner-scoped,
hash-verified acquired mask access. Unit checks must cover acquired preview/baseline
label URLs and a shared toggle. Real Edge checks must find yellow pixels on the
acquired and predicted canvases, including the saved gallery, and confirm hiding
the labels hides both. Run frontend checks, TypeScript/build and preview API tests.

Actual verification: six preview API checks, 66 frontend unit checks, Ruff,
TypeScript and production build passed. Four real Edge checks passed, with yellow
pixels verified in both acquired/predicted patient and saved-preview canvases,
shared toggle removal/restoration, camera/zoom/clipping and default serving gates.
The acquired/predicted gallery screenshot was inspected in `frontend/test-results/`.

## Hippocampus overlay adjustment (D050)

Run frontend unit checks, TypeScript and build, plus the real Edge
`hippocampus-overlay.spec.ts` and `anatomy-experimental.spec.ts` checks. The new
pixel check uses OAS2_0017's saved +365-day MRI/labels: camera changes must change
the yellow projection, zoom must scale its width, and opposite coronal cutaways
must retain/remove the yellow tissue before disabling clipping restores it.
Before the fix, the cutaway regression failed: all 742 yellow pixels remained
visible even at the cutaway that removed their MRI tissue. Preserve ownership,
native geometry, saved model artifacts and scalar/mask measurements.

After the fix, 65 frontend unit checks, TypeScript and the production build passed.
The real Edge experimental/default-policy and overlay checks passed (three checks),
including yellow projection changes with camera/zoom and clipping removal/restoration.

## Actual forecast comparison (D049)

Eight focused Python checks verify native-grid/units, nonfinite rejection, actual
millimetre displacement, independent mask/scalar changes and unavailable/unowned
comparison rejection. 65 frontend checks, TypeScript, build and Ruff passed. The
real Edge comparison/default-policy checks passed: both cutoff/generated canvases
loaded, yellow labels/meshes were off, and measured changes were visible. The
canvas gets a new DOM element when loaded layers change; a regression preserves
cleanup of the old graphics context without destroying the replacement.

The actual OAS2_0017 +365-day field has median 0.243 mm, p95 0.546 mm and maximum
0.749 mm displacement in the cutoff brain mask. Both native hippocampal volumes
are unchanged; separate scalar estimates are -1.29% and -5.21%. Generated MRI
voxels differ from the source, with mean absolute intensity difference 4.27% of
mean absolute input intensity in the brain mask. This includes interpolation
effects and is not an atrophy or accuracy metric. Read-only source/file audit is
ignored `artifacts/forecast-change-inspection.json`. No weights or saved forecast
files were changed to make the display look different.

## Experimental view visibility fix (D048)

64 frontend unit checks, TypeScript and production build passed. Added regressions
cover the visible future-panel opt-in, direct experimental interval links at the
prepared cutoff, changed-source rejection and no job submission from a view link.
Two real Edge checks passed: visible action and direct link both loaded OAS2_0017's
actual +365-day generated MRI; default ML-only serving still stayed gated. The
direct-view screenshot was inspected in ignored `frontend/test-results/`.

## Explicit experimental forecasts (D046)

Run anatomy experimental/API/lifecycle/features/spatial checks, frontend forecast/
preview tests, TypeScript and build. Verify explicit opt-in, default rejection,
ownership, frozen sources/candidate, exact cutoff, retained review state and cached
mode separation. Replay the saved +229-day scalar prediction and inspect newly
generated MRI/labels in the browser. Record actual successes/failures; checks establish
execution and visibility, not accuracy. No illustrative substitutions are allowed.

Actual D046 execution: 58 focused Python checks passed, followed by five preview
integrity checks including wrong-interval rejection; 61 frontend checks, strict
TypeScript, build and Ruff passed. Three real Edge checks passed for the patient
forecast, saved preview and default ML-only policy. The original +229-day scalar
prediction replay had exactly zero error against its saved values.

All nine prepared histories received +365-day attempts. Six completed: OAS2_0017,
OAS2_0027, OAS2_0036, OAS2_0037, OAS2_0070 and OAS2_0073. OAS2_0034, OAS2_0048 and
OAS2_0127 failed regional mesh/mask volume agreement (>5%). No failed output is
served. Each completed result has 40 hash-verified artifacts, positive native
Jacobians and unchanged source/review states. Weights/evaluation fingerprints are
unchanged. Runtime audit: ignored `artifacts/experimental-forecast-runtime-audit.json`.
The CPU worker remains available for explicit forecasts; Docker preprocessing is
paused. This is execution evidence only; no new accuracy evaluation was performed.

## Saved preview (D045)

Run `python -m pytest tests/test_anatomy_preview.py -q` and frontend
`npm run test -- tests/anatomy-preview.test.tsx tests/anatomy-forecast.test.tsx`,
`npm run typecheck` and `npm run build`. Preview checks cover exact interval/subject,
read-only access, ownership, source/file tampering, path escapes and no substituted
volume when unavailable. Inspect the real two-canvas preview after installation.
These verify artifact visibility, not forecasting accuracy.

Actual local verification: four API/integrity tests and nine focused frontend
tests passed, as did Ruff, strict TypeScript and the production build. The real
Edge preview check passed: both acquired/generated canvases loaded, +229-day
provenance was visible, slices and 3D rendered, mobile had no horizontal overflow,
and no browser exceptions or external requests were observed. Desktop screenshots
were inspected in ignored `frontend/test-results/`. The pinned real profile's
four original source MRI hashes match the application's owned visits. Only the
API was restarted to expose the new read-only endpoints.

## Current training-reference contract (D044)

The root Python suite passed 227 tests. Focused anatomy/reference/lifecycle/spatial
and API checks passed 23 tests. TypeScript, 57 frontend unit tests, production
build, Ruff, Alembic and the live ML-only Playwright check passed. New regressions
verify Z arithmetic below ten subjects, baseline-only fitting, held-out membership
rejection, singleton/zero-spread unavailable states, training-only missingness,
shared input/reference reload and older-checkpoint rejection. A real PostgreSQL
two-connection check acquired the first GPU slot, rejected a competitor, and
reacquired the slot after release. This is concurrency evidence, not accuracy.

The actual source availability audit with the training-only reference yields
352/373 visits and 146/150 baseline subjects with numeric Z. The saved audit
distinguishes 17 singleton-bin visits and four unsupported-age visits. Real CUDA
training/native evaluation are recorded in [20](20-training-reference-anatomy-run.md).
Earlier v3 metrics below are retained history and do not describe the v4 model.

## Fixed-reference anatomy contract (D043)

Full root Python suite passed 226 tests after restoring the matching model source;
the later focused anatomy/reference/lifecycle suite passed 38 checks and four
subtests, including two added source-reuse/frozen-cutoff regressions. Frontend
TypeScript, 57 unit tests, production build, Ruff and Alembic schema check passed.
The live ML-only Playwright check passed, including unavailable future anatomy,
disabled generation and rejection of legacy fallback modes. Authenticated model
readiness also reports unavailable for the failed/unsupported candidate. A final
source/checkpoint reload confirmed the fixed reference and all 129 conditioning
columns match. The source availability audit separately reports 336 of 373 visits
with computable Z-scores; this is arithmetic availability, not forecast validation.
An existing AVRA test was updated to the already documented D038 automatic research
policy; parser behavior was unchanged.

New regressions check unchanged supplied bin constants without refitting,
exact Z arithmetic, sparse/unsupported/invalid states without raw-nWBV fallback,
irrelevance of excluded demographics, missingness indicators, saved scalar/reference
roundtrip, explicit older-checkpoint rejection, geometry-bound registration reuse
and exclusion of added visits from the frozen source cutoff. The real checkpoint
reload confirmed all 129 columns and exactly identical saved/reference constants.
Both saved models reject incompatible earlier feature versions.

Actual 20-epoch CUDA training and held-out/native evidence is recorded separately
in [19](19-fixed-reference-anatomy-run.md); tests do not establish forecast accuracy.

## Clinical assistant checks (2026-10-03)

Run `pytest tests/test_assistant_api.py -q`, frontend unit tests, TypeScript and production
build. Synthetic/mock tests verify ownership before provider access, filtered context,
ML-only availability, request limits, server-only configuration, bounded history,
grounded references, timeout/errors, retry and patient-switch isolation. See
[21 Clinical assistant](21-clinical-assistant.md). Live Gemini checks require an API key;
no real patient information is used by automated tests.

## AVRA raw-regression research inputs (2026-10-02)

`python -m pytest tests/test_anatomy.py tests/test_anatomy_lifecycle.py -q` passed
26 checks; the full root suite passed 221 tests and Ruff passed. Added regressions preserve negative and above-scale finite estimates
only in explicit provisional research mode, require the raw-method marker/warning,
retain strict default parsing, block reviewed feature use and reject nonfinite or
malformed outputs. The live hash-verified OAS2_0070 MR4 CSV reproduced the negative
ensemble mean. Research export now includes all three completed five-scan histories,
including that exact raw value; the three existing prepared source records are
unchanged. App review records and source artifacts were not modified. The coordinator
was resumed with the same frozen cohort, GPU image, 96³ grid and 20-epoch settings.
See D034 and ignored `artifacts/avra-negative-output-investigation.json`.

## Optional nWBV reference checks (2026-10-02)

Run `python -m pytest tests/test_nwbv_reference.py nwbv_reference_module/tests/test_reference.py -q`
and the full Python suite. The focused run passed 19 tests and four subtests;
the full root suite passed 215 tests. Ruff and Alembic schema checks passed.
All eight vendored source files match the supplied ZIP byte-for-byte; installation
with `--no-deps` and the installed package's bundled reference were verified.

Checks cover method-matched fractions and integral recorded ages, sparse/unsupported
bins, malformed/nonfinite/missing input, optional package failure, descriptive-only
contracts, frozen enqueue metadata, exclusion of later observations, clearing a
parent's later-cutoff reference, unchanged model outputs, structured biomarker
persistence, API serialization and researcher ownership. The existing trained-mode
regression verifies the added object cannot change the original model covariates or
sequence prediction. These are integration/arithmetic checks, not diagnostic validation.
An additional read-only check evaluated the latest completed real anatomy job's
frozen source metadata: age 77, nWBV 0.769165, reference bin count 19, status `ok`.
Removing the optional comparison reproduced the existing result exactly. The audit
is saved at ignored `artifacts/nwbv-real-input-check.json`; no stored result was rewritten.

The local backend was reloaded with the new contract. A one-off deployment helper
at ignored `artifacts/reload-nwbv-worker.py` holds queued jobs while the current MRI
job finishes, then replaces only the verified worker processes at an idle boundary.
It records `artifacts/nwbv-worker-reload-status.json`; `reloaded` and the capability
`nwbv-age-reference-v1` confirm activation. A waiting state means code is installed
but the current worker still uses its previous loaded code. It leaves native files,
job outcomes, review gates and training artifacts unchanged.

## Longitudinal anatomy checks (2026-10-02)

Run `python -m pytest tests/test_anatomy.py tests/test_anatomy_api.py tests/test_anatomy_spatial.py tests/test_anatomy_forecast_api.py tests/test_anatomy_lifecycle.py -q` and the full
Python suite. Synthetic checks cover verified eTIV conversion, irregular visit timing,
source geometry/coverage and categorical labels, continuous score ranges, unavailable
alignment, review provenance, owned artifacts/tampering, explicit report selection,
train-only structural preprocessing and subject-held-out guards, zero-time physical
warping, folding/coverage failures and closed physical GIFTI mesh volume agreement.
Additional checks exercise a small explicitly synthetic score-conditioned training/save/reload
run and native export of all 40 artifacts with zero-time identity, independent
selection/calibration roles, physical RAS/LPS/vector resampling,
registration units, earlier-cutoff exclusion, hash-bound rating approval, HTTP 202
forecasts, changed-release/input failures, owned future artifacts and available PDF
content. Synthetic candidates are rejected by promotion.
These are engineering checks, NOT real-data anatomical accuracy.

Run frontend TypeScript, `npm test`, production build and
`playwright test tests/e2e/ml-only.spec.ts`. The strict browser check scopes outcome
cards separately from anatomy cards, verifies the added workspace panel, selected
future interval and explicit unavailable/non-acquired label; it does not load a real
predicted artifact. Anatomy UI tests cover review confirmation, ratios, unavailable
ratings, explicit report selection and bounded authenticated mesh loading.
Forecast UI tests cover the exact 731-day interval, selected cutoff, measured/predicted
URLs, two reviewed observations and stale measurement/provenance rejection.
The synthetic measured and available-forecast PDFs were rendered with Poppler and
every page inspected.

Current verification: 199 Python tests and 54 frontend tests passed; Ruff, TypeScript,
production build, the strict Edge browser check and Alembic schema check passed.
AVRA's v2 container completed a real-MRI preprocessing/scoring smoke test, with its
scores still pending visual alignment review. See [18](18-anatomy-forecast-lifecycle.md).

New tests freeze the scan-count cohort at 44/4/4/4, show that changed CDR/Group does
not alter assignment, reject unreviewed inputs by default, exercise explicit provisional
candidate training without granting review, and verify no no-score model files are
trained. A partial one-visit analysis does not satisfy full-history readiness.
The offline CUDA container also completed an explicitly synthetic one-epoch
training run, checkpoint save and reload in the host environment. Its runtime is
recorded as PyTorch 2.7.1+cu128 / RTX 3050; promotion remains rejected. This verifies
the training execution path, not real forecasting accuracy.
The three actual prepared examples from OAS2_0048 also completed CUDA
forward/backward/optimizer preflight steps at 96³ with finite losses and gradients.
This single-subject preflight creates no release and is not the full-cohort fit.
All 19 native source-mask meshes from its second scan passed the corrected binary
isosurface closure/volume checks. Neither check grants human review.
Additional regressions check subject-balanced spatial metrics for repeated histories,
stable full-cohort case indices during incremental preparation, immutable GPU image
pins/read-only study mounts, and binary saddle contacts yielding closed meshes without
changing the categorical mask.

Required scientific checks remain UNEXECUTED: real longitudinal segmentation/alignment
QC, independent rating agreement (no reference labels), interval coverage,
trained spatial forecast overlap/surface metrics and
matching real predicted NIfTI/GIFTI artifacts. No synthetic check is evidence for
these scientific gates. See [17](17-longitudinal-anatomy.md).

## ML-only serving checks (2026-10-02)

The default local app now rejects all legacy prediction starts and clinical-only
serving requests. Existing legacy unit regressions explicitly set `ML_ONLY=false`
in their isolated test environment; dedicated strict tests override that policy.
Run `pytest tests/test_ml_only_serving.py tests/test_forecast_v2.py tests/test_forecast_runner.py -q`.
The release tests fit synthetic models only and check missing promotion, file/source
tampering, full-horizon support, matched anatomy and no fallback. Pipeline tests
confirm missing Docker prevents training and persists a blocker. Synthetic integration
does not measure real anatomy accuracy.

Run the real browser policy check from `frontend` using
`.\node_modules\.bin\playwright.cmd test tests/e2e/ml-only.spec.ts`.
It verifies 409 rejection of old modes, hidden historical current results, three
unavailable cards and Settings readiness. Retained legacy e2e workflows require an
explicit separate research-mode service; do not expect them to pass against strict
serving. The production Next build, TypeScript, unit tests and full Python suite still apply.

## Automated tests

### ML and data

- Manifest parsing and visit ordering
- Missing-file and invalid-NIfTI errors
- Normalization and tensor shape
- Risk-score bounds
- Biomarker calculations
- Output provenance
- Deterministic demo outputs
- Deterministic subject-level training split with no subject leakage
- Held-out trained-model metrics compared with a majority-class baseline
- Training-only demographic statistics, missing/unknown categories and serialized preprocessing round-trip
- Exclusion of identifiers and outcome-derived labels from model inputs
- MRI and demographic gradients, padding invariance, exact subject/visit coverage in bounded batches
- Saved-split validation and fresh-checkpoint prediction round-trip
- Experimental trained inference uses the saved weights/scaler/threshold, pins the full bundle, rejects changed/missing models and incomplete covariates, and never falls back silently
- Trained result/UI/PDF expose one retrospective sequence score, empty neural trajectory, poor reused-holdout performance and in-sample cohort disclosure

### Backend

- JWT login and unauthorized requests
- Patient and visit CRUD
- Upload validation and object-key generation
- Analysis job state transitions
- API response schemas
- Report generation

### Frontend

- Login loading and error states
- Protected routes
- Patient empty/loading/error/completed states
- Analysis progress polling
- Charts and MRI viewer rendering
- Report download behavior

## Manual demo checklist

- Researcher can log in locally.
- Patients and visits persist after a backend restart.
- MRI upload creates a queued job.
- The request returns without waiting for full inference.
- UI shows processing and completion states.
- Three visits appear chronologically.
- Risk chart labels units and visits.
- Biomarker changes identify their baseline.
- Heatmaps show correct provenance.
- A report can be generated and downloaded.
- No credentials, raw paths, or tracebacks appear in normal use.

## Scientific honesty checklist

- Metrics come from a documented subject-level split.
- Demo outputs are not presented as validation results.
- Confidence is shown only when defined and calculated.
- Claims are limited to structural pattern analysis and progression-risk estimation.

## OASIS-2 forecast checks

Forecast labels must derive only from the supplied OASIS-2 CDR history and the
documented horizon policy. Test earliest CDR-zero baseline selection, visit-date
alignment, held-out follow-up masking, insufficient follow-up, subject-level split
integrity, training-only demographic preprocessing, missing covariates, MRI QC and
physical units. Report event, nonevent and unknown counts by frozen split and horizon;
do not infer Alzheimer-specific diagnoses from CDR or Group. Suppress horizons that
the supplied cohort cannot support.

## Completion rule

A change is complete only after relevant automated tests, manual checks, and documentation updates pass.

## Executable checks

For the baseline forecast extension also run:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-base.txt
.\.venv\Scripts\python -m pytest tests/test_forecast_v2.py -q
.\.venv\Scripts\python -m ruff check src backend ml scripts tests
.\.venv\Scripts\python -m scripts.export_forecast_contracts
```

Synthetic checks cover horizon boundaries/gaps/reversions, unknown masks, fixed subject
split, train-only preprocessing/reload, exact FastSurfer label/unit parsing, no silent
fallback, matched model training/evaluation, changed-source rejection, owned API access
and unavailable UI cards. These do not constitute real segmentation validation.
The five-scan real pilot, visual anatomy QC, fresh-environment image execution and
matched real-data evaluation remain required and currently blocked; record actual
completion separately. Never turn a class-unavailable ROC-AUC into zero or report
development AUC from five subjects as validated prediction performance.

From the repository root:

```powershell
.\.venv\Scripts\python -m ruff check backend ml scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m alembic check
.\.venv\Scripts\python -m scripts.create_test_fixture
.\.venv\Scripts\python -m scripts.smoke_3d --prepare
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend audit
npm --prefix frontend run test:e2e
```

Playwright requires the running stack, prepared OASIS cohort, root .env credentials and Microsoft Edge. It covers login protection/errors, a three-visit review, overlay/navigation, 202 asynchronous analysis, downloaded PDF, desktop/mobile rendering, Reports/Settings navigation, patient creation and a real fixture upload. It creates clearly prefixed `E2E_` research records; it does not delete existing data.

For live service and persistence checks:

```powershell
.\.venv\Scripts\python -m scripts.smoke --analyze --mode inference --report
.\.venv\Scripts\python -m scripts.smoke --analyze --mode demo
.\.venv\Scripts\python -m scripts.smoke --analyze --mode precomputed --snapshot data/qa-before-restart.json
docker compose restart backend worker
docker compose up -d --wait
.\.venv\Scripts\python -m scripts.smoke --compare data/qa-before-restart.json --report
```

Run mode checks sequentially; only one active explicit analysis per patient is accepted. The smoke script verifies authentication, ownership-safe responses, real cohort previews, status transitions, provenance, aligned bounded scores, missing confidence and PDF download. The snapshot contains identifiers only, is ignored by Git, and should be compared before adding further test records.

Render downloaded PDFs with `pdftoppm` and inspect every page; check tables, captions, source attribution and footer/page breaks. Do not substitute PDF text extraction for visual QA. Review desktop/mobile screenshots and ensure no page-level overflow or browser exceptions.

Current passing results are recorded in [10 Implementation status](10-implementation-status.md). Offline training and small subject-holdout evaluations now produce local metric artifacts. The original test cohort has already been evaluated in multiple experiments; describe subsequent results as reused-holdout evaluation, not independent final validation. Subject-level split checks are not evidence of predictive performance. See [12 Multimodal training](12-multimodal-training.md).

## 3D extension checks

Geometry tests verify resized canonical affine centers/boundaries (including axis permutations/flips), unchanged source data and finite difference-volume shape. Backend checks cover authentication, cross-owner isolation, intact source bytes, safe filenames, unavailable legacy results and matching visit artifacts. UI tests cover clipping bounds, authenticated bounded fetches, cleanup, layout/overlay/comparison controls, navigation and pausing.

The WebGL browser suite loads actual OASIS voxels, verifies non-empty varied canvas output and changed rendering after rotation, then exercises camera/zoom, clipping, four-up views, coordinate sliders, window/opacity/colormap, silhouette shading, difference layers, two-view comparison, linked navigation, fullscreen, annotated PNG download, visit switching and pause/reopen. It checks mobile overflow, browser exceptions and absence of external network requests. A separate test disables WebGL2 and verifies the explicit error plus intact 2D fallback. See [11 3D visualization](11-3d-visualization.md) for limits and acceptance criteria.
