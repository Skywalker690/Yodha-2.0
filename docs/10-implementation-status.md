# Implementation Status

## Longitudinal anatomy extension 2026-10-02

The uploaded atrophy/future-brain plan is partially implemented, NOT completed.
The existing worker/API/workspace now support native anatomy jobs, 18-regional masks
and stats, immutable provenance, explicit visual QC, reviewed scalar changes,
automatic-score availability/history, source observations, ratios and separate reports.
Generic GIFTI loading and physical warp/mesh checks are implemented, but no trained
spatial model, evaluated forecast artifacts or functioning real future-brain rendering
exists. AVRA runtime/weights/alignment release remain unverified. Details and exact
remaining acceptance criteria are in [17](17-longitudinal-anatomy.md).

All five baseline pilot outputs are verified and `awaiting_visual_qc`. Original
failure records are preserved; none is automatically approved. The local database
has zero completed/reviewed longitudinal anatomy jobs. This is not new training or
prediction accuracy evidence. Current tests: 180 Python and 50 frontend passed;
TypeScript, production build and the updated strict Edge browser check also passed.
Both synthetic anatomy report pages were rendered and visually reviewed. See
[07](07-testing-validation.md) for checks and scientific limitations. These checks
do not validate AVRA ratings or real future-brain forecasting.

## ML-only serving extension 2026-10-02

Default API/UI/Streamlit now require a promoted Clinical + FastSurfer release. Legacy
analysis starts and clinical-only serving selections are rejected; uploads store MRI
without rule-based jobs, and old current-score panels are hidden while archives remain.
Release checks bind models/evaluation/source hashes, reviewed scan features, all horizon
heads and predeclared support/development gates. The durable offline runner pauses for
runtime, processing, visual QC or outcome support rather than generating a fallback.

Docker startup was repaired with user approval by preserving/replacing only the two-socket
runtime directory. Linux engine readiness passed; pinned image download and the actual
five-scan pilot were resumed. Segmentation/training completion must be read from local
run status; no combined model or full-horizon accuracy is claimed yet.

All five scans' real outputs are verified and pending visual QC after recovering
Windows statistics-symlink read failures. The adapter uses the real versioned stats
file, not the Linux alias. Original failed provenance is preserved. No scan is
auto-approved and no outcome model training/serving promotion is claimed from this.

Current verification: 160 Python tests, 46 frontend tests, TypeScript and production
build and the new strict-serving Edge browser check passed. Commands are in [16](16-ml-only-serving.md);
previous legacy e2e results below are historical, not tests of the changed serving policy.

## Baseline FastSurfer study extension 2026-10-02

The new PRD is implemented as a baseline-only study layer in `src/`, with source audit,
85 CDR-zero baseline records, censoring-aware labels, a frozen 61/12/12 subject split,
actual clinical-only 36-month training/reload, pinned isolated FastSurfer runner,
label/unit/provenance parser and visual-review gate, matched Tier A/B experiment code,
shared prediction adapter, local Streamlit dashboard, owned API and separate Next.js panel.
Existing MRI, database/account records, original manifests and historical checkpoints
are preserved. The source Word PRD and vendor repository are not modified.

**Initial implementation snapshot (superseded by the extension above):** the real five-scan FastSurfer pilot timed out waiting for Docker's
Linux engine; anatomy is unavailable for all 85 rows. Real Tier B training/comparison,
surface measurements and optional CNN training are not completed. Zero 12-month events,
one training event at 24 months and zero known test events at 36 months prevent a
validated all-horizon forecast. The fitted 36-month clinical model is experimental
and uncalibrated, not a validated Alzheimer predictor. See [blockers](blockers.md).

Verification: 141 Python tests pass, including 39 new synthetic forecast/runner
tests and Streamlit AppTest; strict TypeScript, 44 frontend tests,
production Next.js build, no dependency conflicts, Alembic no pending schema changes,
and all seven Edge browser workflows pass (six retained workflows plus the new
forecast null-horizon/no-fallback check). Documentation link checks found zero broken
links. Streamlit readiness endpoint returns
ok at loopback 8501; backend/frontend respond locally. No real segmentation accuracy,
fresh-environment container execution or MRI-added-value validation is claimed.

Verified locally on 2026-10-01. The documented research-prototype MVP is implemented. This is software workflow verification, not clinical or predictive-model validation.

The subsequently requested strict MCI-to-Alzheimer forecasting PRD is **not implemented or trained**. The endpoint and authorized-data acquisition plan are now documented in [13 Strict forecasting data](13-strict-forecasting-data.md). ADNI access, a compliant processing environment, the actual cohort and horizon support remain unverified; no dataset download has been completed. The MVP verification below does not establish compliance with this new forecasting specification.

## Delivered product

| Requirement | Implementation |
|---|---|
| Researcher login | JWT in an HTTP-only same-site cookie; Argon2 password hashes; protected, researcher-owned data |
| Patient records | Persisted list, creation, search, optional demographics and chronological visits |
| MRI upload/storage | Validated .nii/.nii.gz, bounded size/shape, generated local object keys, immutable visit MRI, previews |
| Asynchronous analysis | Persisted PostgreSQL queue, one Python worker, progress polling, safe failure and restart states |
| Longitudinal cases | Five prepared OASIS-2 subjects with three real visits each, joined to observed demographic metadata |
| Trajectory/metrics | Documented feature-delta baseline; foreground and feature-change proxies; separately labeled source nWBV/eTIV |
| MRI comparisons | Visit navigation, central axial preview and explicitly labeled intensity-difference visualization |
| 3D MRI workspace | Actual NIfTI volume rendering, four-up/orthogonal views, camera/zoom/window/opacity/colormap, cutaways, crosshairs, silhouette shading, linked baseline comparison, difference thresholds, fullscreen and annotated PNG export |
| Interpretation | Constrained, cautious template text with methods and limitations |
| Reports | Persisted owner-scoped PDF reports with visits, metrics, source metadata, visualization and caveats |
| Provenance | Distinct Demo, Precomputed and Inference modes; unavailable confidence is not displayed as a calculated value |
| Local packaging | Next.js, FastAPI, worker and PostgreSQL in Docker Compose; loopback-only ports and persistent local storage |
| Research disclaimer | Research Prototype / Not a medical diagnosis labels throughout the workspace and reports |

## Dataset evidence

Both extracted parts and the supplied demographics workbook were inspected: 150 subjects, 373 visits and 1,368 paired acquisitions. All workbook MRI IDs match the extracted directories; header/image size checks passed. The supplied format is paired NIfTI-1, not plain Analyze. Whole-volume validation is performed on imported/uploaded volumes.

The prepared cohort is OAS2_0002, OAS2_0041, OAS2_0078, OAS2_0129 and OAS2_0186. Each has three actual visits in MR Delay order. Source volumes are preserved; one acquisition per visit is converted to managed .nii.gz. Missing optional demographic observations remain missing. The actual supplied demographics file is XLSX; CSV is also supported by the importer.

Full-cohort processing is an explicit offline option, not a live-demo requirement. Subject-level split assignment is provided for that workflow, with leakage checks. The five prepared cases are not a validation cohort.

## Verification results

| Check | Result |
|---|---|
| Ruff | Passed |
| PyTest | 23 passed: prior workflow plus canonical field-of-view geometry, volume ownership/source integrity, difference NIfTI artifacts, legacy-result compatibility and missing claimed-cache artifacts |
| Frontend strict TypeScript | Passed |
| Vitest UI/resource tests | 19 passed, including patient-switch/polling races, 3D controls, bounded local downloads, intensity-window ordering, GPU cleanup, late attachment disposal and download cancellation |
| Next.js production build | Passed locally and in the Linux Docker image |
| Playwright in Microsoft Edge | 5 passed against the packaged Docker stack: real OASIS WebGL rendering and graphics-context recovery, no-WebGL fallback, original login/analysis/report flow and persistent upload workflow |
| npm audit | Zero reported vulnerabilities, including development dependencies |
| Alembic check | No model/schema differences on the real PostgreSQL database |
| Idempotent Docker import | Existing patient, visit, account and analysis records preserved |
| Docker smoke: Inference | 202 response in 0.03 seconds; three-scan analysis completed in 18.58 seconds |
| Docker smoke: Demo | 202 response in 0.02 seconds; completed in 14.98 seconds with explicitly illustrative scores |
| Docker smoke: Precomputed | Final restart check: 202 response in 0.05 seconds; completed in 1.64 seconds |
| Restart persistence | Patient/visit identifiers unchanged after backend and worker restart; MRI previews and PDF generation/download still work |
| Duplicate worker guard | A second worker exited before touching jobs, with an explicit already-running message |
| Visual QA | Desktop dashboard/patient and 390px mobile views reviewed; no page overflow or browser exceptions; rendered PDF pages reviewed |
| 3D cohort smoke | Five real OASIS cases / all 15 visits: source-volume downloads, finite bounded 64-cube differences and canonical field-of-view affines passed after container replacement |
| 3D browser privacy and visual QA | Actual varied volume pixels and rotation verified; desktop/mobile workspace and exported PNG reviewed; no external HTTP requests or browser exceptions in the 3D workflow |

Timings are observations on this machine, not universal performance guarantees. The cached cohort review, async analysis and report-download browser workflow completed within the one-minute demo acceptance window.

Browser tests deliberately create `E2E_`-prefixed synthetic research cases. They remain distinguishable from the five OASIS cases and are included in real overview totals. Test reports and screenshots stay in ignored local output directories. No credentials are printed by the smoke or browser tests. PyTest currently emits one non-failing upstream Starlette/httpx deprecation warning.

The PDF render-review workflow led to grouping visualization headings/images/captions across page breaks and rounding observed eTIV with mL units. Charts, tables, source labels and disclaimers were inspected on both report pages.

The 3D render-review workflow caught NiiVue colormap recalibration overwriting explicit intensity windows. The integration applies windows/thresholds afterward, with a regression test; low-difference voxels are transparent and overlay opacity is adjustable. Browser tests exercise slice coordinates, camera/zoom, cutaways, window/opacity/colormap, shading, overlays, two-view comparison, fullscreen, PNG export, visit navigation, pause/reopen and forced WebGL-context loss followed by Retry. Original 2D workflow/report behavior remains available. NiiVue 0.69.0 and local bundled assets were selected after comparing primary library documentation in [11 3D visualization](11-3d-visualization.md).

## Run and recovery

Follow [06 Local development](06-local-development.md). The packaged application is at http://localhost:3000; API/OpenAPI documentation is at http://localhost:8000/docs. Local login values are `SEED_EMAIL` and `SEED_PASSWORD` in the ignored root .env; never copy them into frontend source or documentation.

`docker compose up -d --build` starts the stack after running `python scripts/setup_env.py`. `docker compose exec backend python -m scripts.import_oasis --precompute` prepares or preserves the demo cohort. Stop without deleting data using `docker compose stop`; restart using `docker compose up -d`.

On an existing installation, `docker compose exec backend python -m scripts.smoke_3d --prepare` queues inference for OASIS cases missing the new volumetric artifacts; old analyses/raw MRI remain intact. The prepared five-case cohort already has these artifacts locally. `python -m scripts.smoke_3d` without `--prepare` performs read-only API/geometry checks.

## Offline multimodal retraining (2026-10-01)

The audited run `data/training_multimodal/runs/20261001T134908Z` completed 15 epochs with 150 optimizer updates. All 40 training subjects and all 132 training visits contributed each epoch. The original validation split has eight subjects/29 visits and the test split has eight subjects/24 visits. Eleven usable demographic/visit covariates are encoded as 27 inputs; CDR is the target and Group/identifiers are excluded. MRI, demographic, LSTM and head weights all changed from their seeded initial values. Best validation-selected weights were from epoch 1; final epoch weights/optimizer state are also retained.

The reused eight-subject test holdout gave accuracy 25%, balanced accuracy 50%, recall 100%, specificity 0%, and ROC-AUC 0.0833 at threshold 0.5: all eight subjects were classified as increasing CDR. The majority-class baseline gave accuracy 75% and ROC-AUC 0.5. At the validation-selected threshold 0.514227, test accuracy remained 25% and balanced accuracy was 33.3%. This checkpoint failed to generalize. It was initially offline-only; the subsequently requested experimental application integration is recorded below. Its measured performance has not improved.

Ruff and all 33 backend/ML tests passed. A separate read-only audit rehashed all 185 raw MRI pairs, reconstructed train-only demographic statistics, verified every epoch's subject/visit coverage, reproduced predictions for all 56 subjects and confirmed weight updates in every model branch. Source MRI data were unchanged. See [12 Multimodal training](12-multimodal-training.md) and the ignored run's metrics/prediction artifacts.

## Trained application integration (2026-10-01)

The audited checkpoint is integrated into the existing asynchronous worker through explicitly experimental `trained` mode, initially selected in the workspace. The model uses all MRI and demographic branches with its saved train-only scaler and validation-selected threshold. Results contain one retrospective observed-CDR-increase sequence score, checkpoint/bundle identity and cohort role; no neural trajectory, future Alzheimer probability or confidence is fabricated. The legacy baseline/demo/precomputed modes, MRI sources and historical analyses remain intact.

The exact original forty training subjects and all 132 visits were imported into the host PostgreSQL application with all eleven source covariates. Existing OASIS visits were enriched without replacing MRI, researcher notes, accounts or analyses. The separate eight/eight validation/test assignments were not changed or used for candidate replacement. The raw-source audit again passed for all 185 MRI pairs and reproduced all 56 historical predictions.

All forty real worker predictions completed and matched the saved training scores with a maximum absolute difference of `5.960464477539063e-08` (tolerance `1e-6`). The ignored `data/qa-trained-integration.json` records aggregate verification only. This is an in-sample integration regression, not an improvement in predictive accuracy. After browser tests of legacy modes, current trained results were restored and reverified for all forty subjects.

Verification passed: 102 Python tests, 43 frontend unit tests, strict TypeScript, production Next.js build, Ruff, Alembic schema check, npm audit (zero reported vulnerabilities), and six Microsoft Edge end-to-end tests. The new browser check submits trained mode, observes 202/queued followed by the exact job's completion, checks the saved model/role/empty trajectory and downloads the trained PDF. Existing 3D, no-WebGL, baseline-cache, login, report and synthetic upload workflows pass. Desktop/mobile trained screens and both rendered PDF pages were visually reviewed; warnings and metric/source separation are visible and no page overflow was observed. These checks verify implementation, not clinical validity or reliable forecasting. See [14 Trained inference](14-trained-inference.md).

## Explicit research limitations

- Trained mode is an experimental retrospective CDR-change classifier with poor measured generalization, not a trained future Alzheimer's predictor. Explicit legacy inference remains `feature-delta-v1`.
- Small CNN/LSTM and multimodal checkpoints were trained/evaluated offline; only the audited multimodal run is integrated experimentally. No calibration, independent cohort evaluation or clinical validation is claimed.
- Risk percentages are uncalibrated structural-change indices, not disease probabilities. Demo percentages are illustrative.
- Foreground fraction is not tissue segmentation or measured brain volume. Observed nWBV/eTIV come from OASIS metadata, not the model.
- Overlays show intensity differences, not registered anatomical change, Grad-CAM or a proven temporal explanation.
- 3D shows the supplied MRI voxels, including non-brain head tissue. Clipping and shading are not skull stripping, cortical reconstruction or validated segmentation; no tractography/atlas regions are invented.
- Confidence is null until a defensible estimator exists. No accuracy, F1, ROC-AUC or other evaluation numbers are fabricated.

Improved predictive performance, strict forecasting and model-specific Grad-CAM remain subsequent research work under [04 ML plan](04-ml-plan.md), rather than unfinished MVP product screens or services.
