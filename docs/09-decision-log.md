# Decision Log

## D001: Full-stack product architecture

Status: Accepted

The product uses Next.js, FastAPI, PostgreSQL, local filesystem or S3-compatible storage, and a Python ML pipeline. It runs entirely locally.

## D002: ML remains in Python

Status: Accepted

Use FastAPI, PyTorch, MONAI, NiBabel, NumPy, Pandas, and PyTest for backend and ML work. Use Next.js, TypeScript, Tailwind, shadcn/ui, Recharts, and Lucide for the frontend.

## D003: Prepared demo cohort

Status: Accepted

Use 3–5 prepared OASIS-2 subjects with three visits each for a fast, deterministic demonstration.

## D004: Asynchronous analysis

Status: Accepted

MRI analysis is represented as a job. The API returns `202 Accepted`, and the frontend observes status through polling or WebSocket updates. A simple FastAPI background task is sufficient initially.

## D005: Demo and inference modes

Status: Accepted

The app supports instant demo outputs and local inference when available. The UI must disclose which mode produced the current result.

## D006: No clinical claims

Status: Accepted

The system is a research prototype. It does not diagnose Alzheimer's disease and has no independent clinical validation.

## D007: Local-only deployment

Status: Accepted

There is no AWS deployment target. The supported deployment environment is local Docker Compose with local PostgreSQL and local filesystem or S3-compatible object storage. Kubernetes, Kafka, Redis, service mesh, and cloud infrastructure are out of scope.

## D008: Local filesystem storage and durable worker

Status: Accepted

Use generated object keys on the local filesystem and a single local Python worker polling PostgreSQL. Jobs snapshot their ordered inputs and are persisted before returning 202. Interrupted processing jobs become explicitly failed on worker restart and can be retried. This implements D004's local-worker option without an additional queue service. Patient ownership is tied to researcher accounts. Reports are stored as filesystem artifacts; the six specified database tables remain sufficient.

The worker holds a PostgreSQL advisory lock for its lifetime; accidental duplicate starts fail before recovery can touch live jobs. Host PostgreSQL connections use 127.0.0.1 and a five-second connection timeout to avoid long IPv6 localhost connection attempts on Windows. Container connections use the Compose service hostname.

## D009: OASIS import and metadata

Status: Accepted

Inspect both extracted parts with NiBabel. Import one deterministic acquisition (mpr-1 where present) per visit; repeated acquisitions are not additional visits. Convert the paired header/image volumes to .nii.gz in managed storage while preserving affine and voxel data. Public uploads accept .nii and .nii.gz. Read the supplied demographics XLSX or equivalent CSV, matching by MRI ID, using MR Delay for chronology. CDR, MMSE, eTIV and nWBV are observed research metadata, never invented inference outputs. Prepare 3-5 subjects with at least three actual visits. Full-dataset import is an explicit offline command.

## D010: Transparent feature-delta baseline

Status: Accepted

The first usable inference model is the transparent baseline permitted in docs/04: canonical orientation, percentile intensity scaling, MONAI resize, PyTorch pooled spatial features and ordered deltas from baseline. Scores are uncalibrated structural-change indices displayed with the required progression-risk estimate label and caveat; they are not probabilities of disease. No untrained neural weights are used to produce risk. A small CNN and LSTM interface is provided for future trained checkpoints, but training performance is not an MVP acceptance condition. Confidence remains null until a defensible estimator exists.

## D011: Explanation and metric semantics

Status: Accepted

Use per-visit absolute intensity differences versus the first scan as a research visualization, explicitly not Grad-CAM or a temporal explanation. Canonical orientation and resizing are not anatomical registration; overlays can reflect motion, acquisition and alignment differences. Foreground fraction and pooled-feature change are image proxies, not segmented brain volumes or atrophy. Observed nWBV/eTIV from the demographic workbook are presented with source labels. Demo scores use fixed synthetic values and visibly differ from computed outputs. Precomputed mode reuses a versioned cache of the same baseline calculation and never silently falls back to demo.

## D012: Reproducible frontend installation

Status: Accepted

Keep a committed npm lockfile and explicitly declare the Recharts `react-is` and React Testing Library DOM peers. The Windows npm resolver required `legacy-peer-deps`; the project `.npmrc` applies the same installation behavior to local and Docker builds. Vitest is updated to the patched 4.x line; clean-install checks include type checking, unit tests, a production build and npm audit. Prettier formats source without changing application behavior.

## D013: Longitudinal dashboard selection

Status: Accepted

Prefer a completed three-or-more-visit analysis for the dashboard's featured trajectory, falling back to the most recent completed analysis when none exists. Browser retesting after creating single-visit cases exposed that recency alone replaced the prepared longitudinal demonstration with one observation. Overview totals and recent-patient rows continue to include all owned records.

## D014: User-requested 3D MRI workspace

Status: Accepted (2026-10-01)

The user explicitly expanded the 2D MVP to interactive 3D visualization. After comparing official NiiVue, vtk.js/ITK-Wasm and Cornerstone3D documentation, select pinned NiiVue 0.69.0 (BSD-2-Clause): native NIfTI parsing, orientation-aware slices, WebGL2 volume rendering, clipping, overlays and linked viewers match this local structural-MRI application with less integration than a general renderer or DICOM-oriented tool stack. No new service is introduced. See docs/11-3d-visualization.md for research and acceptance criteria.

Serve source volumes through owner-checked APIs with generated download names, never filesystem paths. Fetch with same-origin authenticated requests and bundle the viewer/assets locally, without external patient-data transfer or CDN dependencies. Keep the existing 2D fallback. 3D research differences are optional versioned visualization artifacts attached to completed analyses; old cached results remain readable, but cannot claim a 3D overlay until recomputed. Original voxels are immutable and prediction mathematics/model version remain unchanged. Cap simultaneous viewers at two and release GPU/event resources on navigation. Do not invent segmentation, cortical surfaces, tractography or anatomical registration.

Display defaults use a normalized difference threshold of 0.04, upper display value 0.3 and overlay opacity 0.45; threshold/opacity are user-adjustable visualization settings, not calibrated clinical cutoffs. Below-threshold values are transparent. Comparison display controls affect both panels; optional interactive linking uses header coordinates and does not imply registration. Apply explicit windows after NiiVue colormap recalibration. Support retry after graphics-context loss and dispose late asynchronous attachment/loading after navigation.

## D015: Local login convenience

Status: Accepted (2026-10-01)

The login form may prefill the local seed email and password from the ignored `frontend/.env.local` via `NEXT_PUBLIC_LOCAL_LOGIN_EMAIL` and `NEXT_PUBLIC_LOCAL_LOGIN_PASSWORD`. This is a local-development convenience only; credentials remain absent from tracked frontend source and documentation, and the defaults must not be enabled for a deployed environment.

## D016: Existing host PostgreSQL for local development

Status: Accepted (2026-10-01)

For this local Windows development environment, use the existing PostgreSQL 17 service on `127.0.0.1:5432` instead of the Compose PostgreSQL container. The project-owned `neuropredict` role and database are created there, while Docker remains available as the packaged deployment option. The ignored local `.env` is the source of the active connection string.

## D017: Demonstration training split and target

Status: Accepted (2026-10-01)

The first trained demonstration model uses the 56 subjects with at least three visits. A seeded, stratified subject-level split assigns 40 subjects to training, 8 to validation, and 8 to testing. The binary target is an observed increase in source CDR from the first to the last available visit. It is a research target, not a diagnosis or a validated clinical endpoint. The model is a small 3D SpatialEncoder plus LSTM and is saved outside Git under `data/training/`.

## D018: Multimodal demonstration model

Status: Accepted (2026-10-01)

The multimodal experiment uses the same subject split and combines MRI features with non-leaking visit metadata: age, education, SES, MMSE, eTIV, nWBV, ASF, MR Delay, sex and handedness. CDR and Group are excluded because CDR defines the target and Group is derived from disease status. Numeric missing values are imputed from training visits only with missingness indicators. The trained artifact is saved under ignored `data/training_multimodal/` and remains experimental until held-out evaluation supports integration.

## D019: Audited multimodal retraining

Status: Accepted (2026-10-01)

Retraining reads and validates the saved 40/8/8 subject manifest rather than generating new assignments. All 132 visits belonging to the 40 training subjects contribute each epoch; 29 validation visits and 24 test visits stay outside gradient updates. Include every usable workbook covariate, including the recorded visit number. Subject/MRI IDs are join keys only; CDR defines the target and Group is excluded as an outcome-derived label. Fit numeric medians/scales on training visits only, preserve missingness, and encode missing/unknown categories explicitly.

Train the MRI encoder, demographic MLP, LSTM and head together from fresh seeded weights using bounded batches. Encode actual visits only and use packed sequences. Select the best checkpoint using class-weighted validation BCE, with a minimum training duration and early stopping; set any decision threshold from validation predictions only. Save immutable run directories with per-epoch subject coverage, source fingerprints, preprocessing, weights, prediction CSVs, full metrics and optimizer state. Test results are withheld from training decisions but this same test cohort has already been evaluated in earlier experiments, so it is a reused holdout, not an independent final validation.

Using MRI/MMSE/nWBV from every visit makes the target retrospective recognition of observed first-to-last CDR increase. It does not establish forecasting ability. Checkpoints remain offline experiment artifacts until a separately requested integration.

## D020: Strict MCI-to-Alzheimer forecasting objective

Status: Accepted (2026-10-01, explicit user selection)

Adopt the supplied complete PRD's strict forecasting direction: documented baseline MCI, followed by a documented study-defined Alzheimer dementia outcome, evaluated at 12/24/36 months. Neither CDR 0.5 nor OASIS Group is sufficient to relabel a subject as MCI. Do not reuse the 40-subject retrospective experiment as evidence for this endpoint or force the new cohort to contain those same subjects. Preserve its files and the active application while a new authorized cohort is acquired and audited. The existing local full-stack architecture remains in place.

## D021: Conditional ADNI acquisition and governance gate

Status: Acquisition plan accepted; access and data not yet verified (2026-10-01)

ADNI is the selected acquisition candidate because its official documentation provides phase-specific baseline diagnosis fields and longitudinal diagnostic records. This is not a claim that a downloaded cohort contains sufficient events. Approved LONI IDA access, the researcher's data-use agreement and institutional requirements must be confirmed before acquisition. The agent must not accept the agreement, invent affiliations, bypass access controls or use unofficial redistributed participant files.

The current ADNI agreement restricts participant-level sharing and use of third-party AI tools without data-containment guarantees. Do not upload participant records, MRI, derived individual predictions or data-bearing tool outputs into this chat. Develop with synthetic examples; real-data processing needs an approved contained workflow. Record download/dictionary versions and storage protections. Retrieve clinical/dictionary/QC metadata before selecting MRI downloads; only about 8.4 GiB was free on C: at the acquisition check, so bulk MRI storage is not approved by this observation. No actual ADNI acquisition or strict-model training has occurred. Details and primary sources are in [13 Strict forecasting data](13-strict-forecasting-data.md).
