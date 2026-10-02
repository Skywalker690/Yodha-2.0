# Testing and Validation

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
