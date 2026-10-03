# Implementation Status

## Guided assessment controls restored to view (2026-10-03, D084)

The full cognitive assessment card now appears directly under the patient section
links and before the MRI workspace. Uploaded cases retain Start/Resume and the
existing task/scoring, draft and completion dialog. The empty state clearly names
the MMSE-style assessment; imported study observations explain their read-only
status. The saved score header, prototype palette, scoring APIs and MRI viewer
remain intact. See [07](07-testing-validation.md) for checks.

## Saved MMSE visible on patient entry (2026-10-03, D083)

The default patient header now displays the selected visit's saved MMSE and
separately labeled demo cognitive score, when available. Score links scroll to
the original assessment card, which remains below the MRI workspace. Existing
scoring, storage, styles and MRI viewer components are unchanged. Production
build/type and whitespace checks pass; local review confirmed the baseline
OAS2_0048 MMSE of 19/30 in both locations. No stored data was modified.

## First prototype palette restored (2026-10-03, D082)

The patient styling now inherits the original dark navy and teal palette from
the existing global stylesheet. Card radii/sizes, typography, spacing, button
arrangement, section navigation and persistent MRI viewer are retained. This
correction modifies only palette declarations in the added patient stylesheet;
all other frontend sources, including MRI components and global styles, remain
unchanged. See [07](07-testing-validation.md) for validation evidence.

## Patient dashboard design implemented (2026-10-03, D081)

The approved patient header, grouped MRI visit/Add visit actions, four section
links, slate-blue sidebar and surrounding panel palette are integrated into the
working frontend. All actions retain their existing handlers, endpoints and
data. Section links scroll without conditionally mounting workspace content;
loaded patient content is retained alongside transient polling errors. The live
MRI viewer components and original global stylesheet remain byte-for-byte
unchanged, including axial defaults, segmentation highlights and forecasts.
TypeScript, production build and whitespace checks pass; local browser review
confirmed the actual MRI and retained 3D selection after section navigation.
No automated tests, new data/model jobs or preview fixtures were introduced.

## Assessment completion correction (2026-10-03, D074)

The assessment now requires a task score before advancing, accepts legitimate
zero-point responses and explains missing-score requirements. Task navigation
resets scrolling; incomplete review offers a direct return to unanswered tasks.
Five UI and four isolated API checks pass, including server completion, draft
resume, retry and upload metadata preservation. Build/type/lint checks pass; no
real patient assessment was completed during verification.

## Cognitive assessment imported through diffs (2026-10-03, D073)

Imported the new assessment feature from remote chatbot `bd61b54` without merging
branches. It includes eleven original English task groups, numeric point choices,
draft/resume, server-calculated totals, immutable completion, owned visit APIs,
optional authorized-protocol configuration and separate dashboard/chatbot demo
scores. Current automatic patient codes, required age/nWBV, paired MRI uploads,
hidden unavailable cards and axial defaults are preserved. Pending visits with
assessment records are protected from empty-visit deletion. Build/type/static
checks and API startup passed; the patient assessment action was inspected live.
No real assessment, provider request or automated test suite was run for this
import. See [22](22-cognitive-assessment.md) and [07](07-testing-validation.md).

## Default axial MRI view and segmentation visibility (2026-10-03, D072)

The spatial MRI workspace opens in axial mode, including direct forecast links,
and reset returns to axial. Manual alternative layouts remain available. A
matching hippocampus mask is highlighted by default; uploads without a mask show
the FastSurfer prerequisite and keep the highlight control visible but disabled.
Build/type/whitespace checks and live uploaded-MRI inspection passed. Rendering
does not generate segmentation. The current uploaded patient still has a pending
earlier baseline and no anatomy result; Docker and a normal anatomy worker are
unavailable. No segmentation run or automated tests were performed.

## Paired MRI file uploads (2026-10-03, D071)

The MRI uploader accepts matching `.hdr`/`.img` pairs, including the supplied
`.nifti.hdr`/`.nifti.img` names, and retains `.nii`/`.nii.gz` support. Selecting
several complete pairs offers one acquisition for the selected visit, preferring
`mpr-1`. The backend validates and converts pairs into managed `.nii.gz` for the
existing viewer/processing path, preserving geometry and scaled float32 values.
Size limits, age/nWBV requirements and serving/release policies remain enforced.
Build/type/lint/compilation, API startup and upload-form inspection passed. No
real pair upload, new analysis execution or automated tests were performed.

## Patient entry and MRI metadata (2026-10-03, D070)

New patients receive automatic owner-scoped `RESEARCH_001`-style codes. Age and
nWBV are required, stored in the new pending baseline visit and prefilled on its
MRI upload screen. All uploads require scan-time age/nWBV and preserve existing
metadata when merging image details. Researcher-entered values retain their
unverified measurement provenance. Existing imported patient IDs are preserved.
Build/type/lint/compilation checks passed; the API is restarted and the form was
inspected. No real data was submitted and no automated test suite was run.

## Dashboard card cleanup (2026-10-03, D068)

The dashboard omits BMI, total hippocampus and hippocampal volume change cards.
Missing remaining measurements/source values and empty result panels are hidden;
available numeric zero and recorded sex/handedness remain visible. TypeScript,
production build and whitespace checks passed, and the current dashboard was
visually inspected. No automated test suite was run for this change.

## Main branch integration (2026-10-03, D067)

The combined `feat/ml` branch at `5eb3818` is merged into `main`, including
the anatomy/forecast workflow, hippocampus display corrections, patient workspace
updates and Alzhio Bot. The merge required no conflicts or application code edits.
Production build, TypeScript, Ruff, Python compilation and staged whitespace
checks passed; automated test suites were not run for this integration.

## Combined chatbot and ML application (2026-10-03, D066)

Remote `chatbot` at `7165081` is integrated into the current ML branch, including
Alzhio branding, the patient chat widget, follow-up history, suggested questions,
research references and the authenticated Gemini adapter. The current anatomy
and forecast workflow remains integrated. Frontend build/type checks, backend
lint/compilation and API startup checks passed. The local API serves the merged
code; live bot replies require a backend Gemini API key. No provider call or
automated test suite was run for this merge.

## Regional hippocampus display correction (2026-10-03, D062)

The default forecast viewer now shows scalar-guided local hippocampus changes
with the acquired skull/head fixed. All fifteen five-patient annual illustrations
completed. Bilateral displayed mask volumes decrease at 12/24/36 months; actual
scalar estimates and voxel quantization are shown separately. The full-head
magnifier is retired. Source MRI, previous outputs and weights are preserved.
This is a presentation mapping from learned scalar volumes, not an evaluated
spatial MRI predictor or evidence of Alzheimer's progression.

## Five-patient annual forecasts (2026-10-03, D061)

The five pinned patients have completed patient-specific 12/24/36-month outputs
from the frozen historical v3 model, plus separately identified presentation
variants. The workspace defaults these patients to experimental mode, offers
annual scalar progression and plays completed horizons. Five of fifteen views
permit 1.5x/3x magnification; others show original scale. Original outputs,
model weights, training membership and unvalidated status remain unchanged.
See [07](07-testing-validation.md) for runtime counts and check limitations.

## Gemini clinical assistant (2026-10-03)

The patient workspace includes temporary contextual chat, three suggested questions and
optional Google Search references with supported passages. One authenticated backend
endpoint builds an allowlisted context and uses the existing httpx dependency. No model
training, schema migration or additional service is required. Raw MRI/identifiers/notes
are excluded; unreviewed anatomy and unavailable forecasts retain their status.

On the original chatbot branch, frontend unit tests, TypeScript, production build,
focused backend tests, Ruff and the synthetic Edge desktop/mobile workflow passed.
That branch's running backend was updated and healthy;
the existing MRI worker remained running. Live responses need GEMINI_API_KEY in the local
backend environment. Full Python verification remains limited by existing missing reference
data and anatomy/forecast dependencies. See [21 Clinical assistant](21-clinical-assistant.md).

## Optional nWBV module integration (2026-10-02)

The supplied package is extracted at `nwbv_reference_module/`, installed with
`--no-deps`, and packaged in the backend Docker build. The existing worker attaches
the selected observed visit's `biomarkers.nwbv_age_reference_v1` and persists its
structured provenance in the existing biomarker table. It is descriptive research
context with no clinical risk and no new training feature. Existing results remain
readable; they are not rewritten. Frozen metadata and earlier-cutoff handling prevent
later/edited visit data from entering the comparison. See D033 and the module README.

Verification: 215 root Python tests, three bundled package tests and four subtests
passed; Ruff, package integrity/installed evaluation and Alembic checks passed.
The local backend was reloaded. The worker's safe idle-boundary reload is tracked in
ignored `artifacts/nwbv-worker-reload-status.json`; it waits for the active MRI job
and confirms the new `nwbv-age-reference-v1` capability before marking `reloaded`.

## Longitudinal anatomy extension 2026-10-02

Live update after investigating AVRA: three complete five-scan cohort histories
are available, a fourth is processing and 52 subjects remain queued. The coordinator
had stopped because a finite PA estimate of -0.00059036014 violated nominal ordinal
bounds. D034 corrects the provisional research path to preserve raw regression
outputs with an explicit warning; source hashes and clinical review bounds remain
enforced. Research export now accepts all three histories and retains the earlier
three prepared examples unchanged. The same coordinator/run was resumed for
registration and eventual full-cohort training; parameter fitting has not started.

Latest training run: score-conditioned only, with a scan-count-selected 56-subject /
185-visit cohort and new 44 train / 4 selection / 4 calibration / 4 test assignment.
Docker was recovered again; one worker and a durable coordinator are processing the
cohort, then automatically preparing/training/evaluating an explicitly provisional
research candidate. Pending visual QC blocks promotion, not this candidate computation.
Live stage: `artifacts/anatomy-score-run-20261002/pipeline-status.json`.

The uploaded atrophy/future-brain plan's software paths are implemented, but its
scientific completion condition is NOT met. The worker/API/workspace support native
18-region anatomy, review-bound measurements and automatic scores, cutoff-local
registration, score-conditioned scalar/spatial training, held-out calibration/native evaluation,
immutable release promotion, asynchronous forecasts, owned MRI/mask/field/GIFTI
serving, predicted viewer controls/playback and separate reports. No real anatomy
model has been trained/promoted; no real future-brain output is available.
Details, API and reproducible commands are in
[18 Anatomy forecasting lifecycle](18-anatomy-forecast-lifecycle.md).

All five baseline pilot outputs are verified and `awaiting_visual_qc`. Original
failure records are preserved; none is automatically approved. The local database
has zero completed/reviewed longitudinal anatomy jobs. All frozen 56 subjects/185
visits are imported. A real GPU anatomy pilot began but was interrupted when Docker
and the worker stopped; the job is failed and files preserved. The hash-pinned AVRA
v2 runtime completed scoring on one real MRI, still pending alignment QC. This is
not prediction accuracy evidence. Current tests: 195 Python and 54 frontend passed;
Ruff, TypeScript, production build, strict Edge browser and Alembic checks passed.
Synthetic measured/forecast report pages were rendered and visually reviewed. See
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

This project uses only the supplied OASIS-2 MRI dataset and demographics workbook.
The baseline endpoint is later observed CDR conversion, not an Alzheimer-specific
diagnosis. Horizon support remains limited by observed follow-up and event counts.
See [13 OASIS-2 data and forecast scope](13-oasis2-data-and-forecast-scope.md).

## Delivered product

| Requirement | Implementation |
|---|---|
| Researcher login | JWT in an HTTP-only same-site cookie; Argon2 password hashes; protected, researcher-owned data |
| Patient records | Persisted list, creation, search, optional demographics and chronological visits |
| MRI upload/storage | Validated .nii/.nii.gz or matched .hdr/.img pairs converted to managed NIfTI, bounded size/shape, generated local object keys, immutable visit MRI, previews |
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
