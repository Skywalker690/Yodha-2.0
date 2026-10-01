# Testing and Validation

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

## Strict forecasting checks (planned, not yet executed)

Before any new strict forecasting training, verify the permission/containment and dataset gates in [13 Strict forecasting data](13-strict-forecasting-data.md). Public documentation and synthetic fixtures are permitted during acquisition planning; real participant-level tool output is not permitted without an approved contained workflow.

The new pipeline must test phase-specific diagnosis mappings, documented baseline MCI eligibility, Alzheimer-specific outcome semantics, duplicate/rollover participant and scan detection, clinical/MRI date alignment and feature availability at the prediction cutoff. Label tests must cover events before/on/after 12/24/36 months, inadequate follow-up, diagnosis gaps spanning a horizon, reversions and unresolved diagnoses. Unknown labels must remain masked. Verify both classes and report event/nonevent/unknown counts separately by split and horizon; class presence alone does not establish adequate sample size. MRI QC, morphometry units, training-only preprocessing, monotonic supported risks and a synthetic end-to-end request also need checks. Existing OASIS tests do not validate this future pipeline.

## Completion rule

A change is complete only after relevant automated tests, manual checks, and documentation updates pass.

## Executable checks

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
