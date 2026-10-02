# Testing and Validation

## Cognitive assessment checks (2026-10-03)

The focused MMSE/patient/upload/chatbot and ML-only runs passed 54 tests. Two real PostgreSQL
checks passed in an isolated disposable database, verifying stale metadata refresh
in both scan/assessment write orders. All 67 frontend tests, TypeScript, production
build and the desktop/mobile Edge assessment workflow passed. Checks cover strict
points, incomplete/zero distinction, stale revisions, owned visits, imported-record
protection, idempotent completion, draft persistence, separate demo/standard storage,
filtered chatbot context and MRI metadata preservation. All data is synthetic;
these checks do not establish clinical validity. See [20](20-cognitive-assessment.md).

## Clinical assistant checks (2026-10-03)

Run `pytest tests/test_assistant_api.py -q`, frontend unit tests, TypeScript and production
build. Synthetic/mock tests verify ownership before provider access, filtered context,
ML-only availability, request limits, server-only configuration, bounded history,
grounded references, timeout/errors, retry and patient-switch isolation. See
[19 Clinical assistant](19-clinical-assistant.md). Live Gemini checks require an API key;
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
