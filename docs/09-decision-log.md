# Decision Log

## D047: Simplify assessment point options

Status: Accepted and implemented (2026-10-03, explicit user request)

Remove the "Not administered" radio option from the assessment UI. Show only numeric
point choices and label unset review results "Unanswered". Unset tasks still persist
as null and block completion; scoring, API contracts and existing records are unchanged.

## D046: Implement original English cognitive demo with separate scoring

Status: Accepted and implemented (2026-10-03, explicit user clarification)

The user requested implementation, then confirmed they have no authorized questionnaire
content and asked for an English demo. This supersedes D045's initial standard-content
scope for the current release. Use original demonstration prompts covering eleven
cognitive task groups with a 30-point arithmetic total, label them MMSE-style demo,
and persist `cognitiveDemoScore` separately. Never fill clinical `MMSE` or change model
inputs from a demo. A separately configured authorized original-MMSE definition can
use the standard storage branch; no actual licensed questionnaire is bundled.

Deliver clinician-recorded task points, deterministic server totals, draft/resume,
immutable completed attempts, selected-visit isolation, sanitized summaries and
dashboard values before anatomy. Preserve MRI metadata with refreshed row locks,
add PATCH browser support, and keep imported observations and historical reports
unchanged. See [20 Cognitive assessment](20-cognitive-assessment.md) for evidence.

## D045: Plan standard MMSE scoring from assessment results

Status: Accepted for planning (2026-10-03, explicit user clarification; not implemented)

The user selected a standard MMSE assessment with the score calculated directly from
recorded task performance, rather than ten custom questions per area. Plan a
clinician-guided assessment attached to a visit, using authorized instrument content
and deterministic backend scoring. The total is not an editable input. Only a valid
completed standardized assessment can publish `metadata.MMSE`; drafts and custom
questionnaires cannot supply that model-compatible field.

Reuse visit JSON for the MVP, fix MRI upload metadata replacement/concurrent-write
handling, display the score without requiring completed anatomy, and preserve imported
observations, historical input snapshots and forecast eligibility. No training, worker
or model changes are included. Implementation and verification remain future work;
see [MMSE assessment plan](../mmse-plan.md).

## D044: Alzhio text-only product and bot branding

Status: Accepted (2026-10-03, explicit user request)

Use a CSS-styled text wordmark, `Alzhio`, for public product branding and `Alzhio Bot`
for the contextual chat. Remove the brain icon marks from those brand areas rather than
adding a graphical logo. Public browser, API, report and export labels use Alzhio; routes,
database identifiers and package names remain unchanged for compatibility.

## D043: Floating assistant widget preserves workspace space

Status: Accepted (2026-10-03, explicit user request)

Render Alzhio Bot as a fixed launcher and overlay drawer rather than an
in-flow patient-workspace panel. It stays scoped to the selected patient, has keyboard
Escape, backdrop and Close controls, and does not alter backend behavior or send data
until the clinician submits a question.

## D042: Gemini assistant for the five-hour hackathon

Status: Accepted (2026-10-03, explicit user implementation request)

Implement one stateless authenticated patient assistant endpoint and one chat panel shared
by both workspace modes. Use the existing httpx dependency with Gemini generateContent
REST, optional Google Search grounding, backend-only SecretStr API key and configurable
model. No local training, database migrations, SDK installation or worker changes.

This extends D007 with an explicit cloud text-processing exception for synthetic/OASIS
de-identified demonstration cases. Send only allowlisted structured clinical/anatomy
values, preserving unreviewed research status and unavailable forecasts; omit source
identifiers, patient/visit codes, free text, paths, raw MRI and owner data. User questions
and recent exchanges are sent to Gemini and must omit identifying details. No chat is
persisted by Alzhio; provider retention terms still apply. Preserve existing forecast
gates and user worktree changes. Record configuration and verification in doc 19.

## D041: Compact regional measurements and remove the regional comparison chart

Status: Accepted (2026-10-02, explicit user request)

Remove the observed-versus-model-predicted regional anatomy section from the MRI
analysis panel. Show its first four regional measurement rows initially, preserving
the existing order. Reveal the remaining rows with a keyboard-accessible dropdown
button; collapse again on visit/analysis changes. Measurements, forecast outputs,
3D timeline and reports remain available through their existing data paths.

## D040: Hide cyan regional highlights and keep the hippocampus visible

Status: Accepted (2026-10-02, explicit user request)

Keep the yellow hippocampal labels and boundaries visible in observed/predicted views.
Make temporal/parietal labels transparent and omit their cyan regional meshes. Keep
the hippocampus highlight control and a neutral gray complete brain boundary. Purple
ventricle highlighting remains hidden. Stored segmentation, regional meshes,
measurements and training inputs are unchanged; this is a visual change.

## D039: Hide ventricle highlighting in the MRI viewer

Status: Accepted (2026-10-02, explicit user request)

Make lateral-ventricle labels transparent in the shared anatomy overlay and omit
ventricle meshes from the predicted view. Remove the purple ventricle legend.
This is a display-only change: source MRI, segmentation labels, measurements,
stored meshes and model inputs remain unchanged.

## D038: Automatically expose unreviewed anatomy values for research use

Status: Accepted (2026-10-02, explicit user direction)

After automated checks complete, use the produced hippocampal volumes and AVRA
MTA-left/MTA-right/Koedam outputs directly in the dashboard and anatomy report;
remove manual visual confirmation controls from the value workflow. Label AVRA
scores and unreviewed measurements as unreviewed research estimates and preserve
raw regression outputs, including finite values outside nominal score bounds.
This does not claim visual QC, independent rating agreement, or clinical meaning.
Only display values after source, segmentation, rating CSV, transform and provenance
integrity checks pass. Missing, failed, or tampered artifacts remain unavailable.
Explicit forecast release/promotion and scientific evaluation gates remain unchanged.

This supersedes the dashboard display restriction in D036 and the app review
workflow for direct descriptive values. API review endpoints remain for historical
compatibility but the dashboard no longer asks the researcher to invoke them.

## D037: Provisional 6-subject research candidate training on CUDA

Status: Accepted (2026-10-02, explicit user direction)

Train the MTA/Koedam-conditioned 3D longitudinal anatomy model on the first 6 completed
subjects (16 registered longitudinal examples: OAS2_0048, OAS2_0070, OAS2_0073, OAS2_0127,
OAS2_0017, OAS2_0027) using the pinned CUDA container (`yodha-anatomy-training:20261002`)
for 20 epochs. For this provisional research run, OAS2_0027 serves as calibration while
OAS2_0048, OAS2_0070, and OAS2_0127 train, OAS2_0017 provides hyperparameter selection,
and OAS2_0073 evaluates holdout generalization. All predictions produced by this checkpoint
remain explicitly tagged with honest research provenance and labeled experimental.

## D036: Source-bound patient value snapshot on the dashboard

Status: Accepted (2026-10-02, user request)

Add a dashboard panel with patient and observed-visit selectors. Show source OASIS
demographics/clinical values, FastSurfer regional statistics, hard-label mask volumes,
eTIV ratios, bilateral hippocampal volume/asymmetry, MTA/Koedam estimates, and the
optional descriptive nWBV age reference when present. Show BMI only from an explicit
source BMI field; do not infer it without height and weight. Keep MTA/Koedam hidden
unless AVRA alignment is reviewed, and show longitudinal hippocampal volume change
only when both adjacent scans pass visual QC. State unavailability and provenance
beside each value. Distinguish pending scan QC from pending AVRA alignment QC and link
to the full patient workspace for the required review action. These values are
descriptive research measurements, not a diagnosis or atrophy norm.

## D035: Interactive 12/24/36-month future prediction timeline with explicit experimental provenance

Status: Accepted (2026-10-02, explicit user request)

The longitudinal anatomy model generates 3D displacement fields, warped T1 MRI volumes,
categorical segmentation masks, and 19 boundary meshes (`brain_mesh.gii` and 18 regional meshes)
at discrete horizons. The scan-count-selected frozen cohort split contains insufficient holdout
scans matching exact 12-, 24-, and 36-month intervals (±90 days) to meet formal holdout
validation thresholds.

Connect 12-, 24-, and 36-month prediction positions to the interactive 3D timeline strip
in `VolumeExplorer` and `MLWorkspace`, tied to the cutoff scan. Allow sequential navigation
(Earlier / Later MRI) past the cutoff scan into +12m, +24m, and +36m future brain positions.
When viewing future brain predictions, load the real model-generated NIfTI MRI, categorical labels,
and all 19 boundary meshes. Clearly label every 12-, 24-, and 36-month position and view
with an explicit "Experimental (unsupported horizon)" badge and honest provenance disclaimers.
Never fabricate synthetic holdout support, crossfade transitions, or uniformly scaled meshes.

## D034: Preserve unbounded AVRA outputs in provisional research training

Status: Accepted (2026-10-02, investigation of the user-reported training blocker)

The pinned upstream AVRA model ends in an unconstrained `nn.Linear` layer, and its
runner writes the ensemble mean without clipping. OAS2_0070 MR4 has PA members
0.01023519, -0.048216164, 0.044799566, 0.0032413006 and -0.013011694;
the reported mean is -0.00059036014, with ensemble SD 0.030379687. Source/alignment
artifact hashes pass. This is a finite near-zero regression estimate outside the
nominal ordinal scale, not evidence of negative biological atrophy or a failed MRI.
Alignment remains pending visual review. Source:+[pinned output head](https://github.com/gsmartensson/avra_public/blob/17e947606596e6594ec01d54ef38c992becf9395/model/model.py).

Correct only the explicitly authorized provisional `--allow-unreviewed-research`
path: preserve finite out-of-scale raw estimates under status `unreviewed_research`,
method `AVRA-v0.8-ensemble-raw-regression-research`, and an explicit warning listing
the extrapolated values. Do not clip, round, replace with zero or discard the subject.
Default/reviewed parsing still enforces MTA 0–4 and PA 0–3; missing/nonfinite values,
source tampering and malformed artifacts still fail. This permits candidate training
and leaves app review/serving/promotion gates intact. Existing in-range examples retain
their exact values and metadata so immutable prepared cases can resume.

## D033: Optional source-matched nWBV age reference (user-provided module)

Status: Accepted (2026-10-02, explicit user request)

Extract and vendor the supplied `nwbv_reference_module` package at the repository
root, preserving its aggregate reference and README. Install with `python -m pip
install --no-deps ./nwbv_reference_module` in the backend environment and Docker image.
The existing worker calls `NwbvReference.bundled().evaluate` after inference, storing
the structured optional `biomarkers.nwbv_age_reference_v1` for the selected observed
visit in result JSON and the existing biomarker table. No migration is needed.

Freeze age, nWBV and measurement method at enqueue, separately from model covariates.
Use the OASIS method only for imported OASIS values; unknown/different methods,
missing/invalid values, unsupported ages and sparse bins remain explicit unavailable
states. Normalize integral numeric ages from the existing float-valued importer;
never coerce strings, impute missing values, derive nWBV from FastSurfer, or use
future/currently edited metadata. Older queued anatomy snapshots can use their
already-frozen OASIS metadata/provenance flags. Older results remain compatible.

Keep `task=descriptive_age_reference`, `intended_use=support_value`,
`feature_use_allowed=false`, and `clinical_risk=null`. This whole-cohort reference
does not alter model inputs, training, CDR risk, volumes, future MRI or review gates.
An earlier cutoff clears the parent's later-visit reference and the worker evaluates
the selected cutoff's observed inputs. Optional package/profile failures are logged
and stored explicitly, without substituting a disease or forecasting model.
The README's example UI card is context; the requested change is backend integration.
## D032: Resolve binary isosurface ties without changing categorical anatomy

Status: Accepted (2026-10-02, discovered on the first real five-scan history)

The source middle-temporal mask produced three edges with four incident faces at
marching-cubes level exactly 0.5, failing the existing closed two-manifold check.
Use a fixed 0.5001 binary isovalue and remove degenerate triangles. The 0.0001-voxel
interpolation offset resolves saddle ties without editing labels, smoothing, or
simplifying surfaces. Keep closure, non-degenerate faces, orientation and <=5%
physical volume checks mandatory; record the actual isovalue in mesh provenance.
A synthetic saddle fixture reproduces the four-face failure and verifies a closed
export and unchanged mask. Real source-mask checks are engineering evidence, not
forecast accuracy or segmentation approval.

## D031: Reuse the verified CUDA container for score-conditioned training

Status: Accepted (2026-10-02; supersedes D030's wheel-install approach)

Build `infra/anatomy/Dockerfile` from the locally verified pinned FastSurfer CUDA
base. Retain its CUDA PyTorch and add the required Pydantic and matching geometry
dependencies. Bind code/study read-only and the candidate output read-write, disable
network access during fitting, and record the immutable image ID in run status.
The host worker remains in its original Python environment. A synthetic CUDA
training/save/host-reload check passed with PyTorch 2.7.1+cu128 on the RTX 3050;
it is engineering evidence only. The coordinator will use this runtime after all
56 real histories finish processing. It never silently falls back to CPU.

Stopped the superseded isolated-wheel download and removed only its approximately
2 GB package scratch file. Kept its scripts, environment and logs. Raw MRI, earlier
model files and native analyses remain preserved. The full run needs additional
disk space; the user was asked to free 10 GB or provide another location while
processing continued. The drive subsequently has 77 GB free, which is sufficient.
A lossless LZX compression probe preserved the aligned MRI
digest and reduced one 28.9 MB file to 22.1 MB; it does not solve the full capacity need.

## D030: Isolated CUDA runtime for the active anatomy training run

Status: Superseded by D031 (2026-10-02)

The host has an RTX 3050 and a working NVIDIA driver, but the application's Python
environment contains PyTorch 2.14.0+cpu. The queued CUDA training run cannot fit
with that build. Install the matching 2.14.0+cu130 wheel from PyTorch's official
CUDA index in `artifacts/anatomy-cuda-runtime-20261002`, reusing the application's
non-Torch dependencies through a `.pth` path. Keep the running API and segmentation
worker in their original environment. Verify actual CUDA model forward/backward
execution before resuming only the waiting training coordinator with the isolated
interpreter. Preserve cohort, epochs, device, grid size and existing run artifacts.

## D029: Score-conditioned training on the richest MRI histories

Status: Accepted (2026-10-02, explicit user direction)

Train only the anatomy predictor with MTA-left/right and Koedam inputs. Remove
the no-score training/evaluation/release dependency. Keep inexpensive no-change and
individual-trend comparisons; they do not train another neural model. Retain prior
artifacts without treating their accuracy as evidence for the new study.

Create a separately frozen anatomy cohort using source scan count, not CDR, Group,
prediction outcomes or the old classifier's 40-subject assignment. All 56 supplied
subjects with at least three scans qualify: four have five scans, nine have four,
and 43 have three. Prioritize the longest histories for processing. Use 44 training,
four selection, four interval-calibration and four test subjects. Reserve one four-scan
subject for each held-out role and one five-scan subject for test, using a fixed seed;
all remaining longest histories enter training. Freeze membership before model fitting.
Old classifier/baseline splits remain unchanged. The new holdout is reused OASIS data,
not independent clinical validation. Explicit image review and source integrity remain
required; processing does not automatically become human approval.

Permit an explicitly marked unreviewed research candidate to complete actual fitting
after automated source/geometry/score checks. Private exports distinguish
`automated_checks_only` anatomy and `unreviewed_research` score inputs. They do not
modify application review records. Such training/evaluation remains provisional and
cannot promote or serve until real reviews and a reviewed retraining pass. This
separates the requested computation from the release approval gate.

Spatial selection/test metrics average within each subject before averaging across
subjects, matching structural and native evaluation. Extra examples from a five-scan
history therefore improve training coverage without giving that subject extra weight
in reported accuracy or checkpoint selection.

Prepare completed, integrity-checked histories incrementally while the single worker
processes later subjects. Stable case indices come from the full frozen split, not
completion order. Partial preparation writes only progress, never a final study
manifest; final export/preparation still requires all 56 subjects. Verified cases
are reused and interrupted partial directories are preserved before retrying.
The Windows coordinator holds a process-lifetime system-awake request during the
run, released on exit. Display sleep and persistent power settings are unchanged.

The local drive has limited headroom. Lossless NTFS compression was enabled for
`storage/derived`, including inherited compression for new analysis folders. This
preserves file bytes/hashes and formats, is reversible with `compact /U`, and leaves
raw MRI storage unchanged. Processing still enforces its disk-headroom guard.

## D028: Reviewed cutoff forecasts and reproducible licensed runtime

Status: Accepted (2026-10-02)

The user authorized non-commercial research use of FSL and asked this chat to
continue implementation while stopping the other overlapping chat. Preserve the
existing work and services. Provision AVRA from a pinned upstream commit and all
15 released checkpoints in an isolated container. Retain failed candidates and
logs; a successful real invocation still requires explicit alignment review.

Queue anatomy forecasts through the existing worker and persist optional JSON
fields. A selected earlier cutoff uses only its chronological prefix, with reviewed
segmentation and rating provenance. Bind parent result, actual inference files,
release, sources and generated artifacts by digest. Do not expose another owner's
artifacts or return observed anatomy for failed prediction. Generate and retrieve
18 separate regional masks in addition to labels, MRI, physical pull field and meshes.

Divide the frozen eight development subjects deterministically into four selection
and four calibration subjects; use subject-block 80% intervals with explicit limited
sample size. Keep original 40/8/8 membership and acknowledge reused holdout. Require
real native evaluation, matched score ablation and immutable promotion before serving.
Code/synthetic verification is complete enough to run the lifecycle; real segmentation,
review, model training and held-out release evidence remain outstanding. See
[18](18-anatomy-forecast-lifecycle.md) for commands and current execution status.

## D027: Cutoff-local spatial learning and evaluated anatomy release

Status: Accepted for implementation (2026-10-02, explicit completion request)

Train a bounded time-conditioned 3D displacement predictor from reviewed longitudinal
anatomy, not from the retrospective CDR checkpoint. Register each earlier observation
to its own latest-input cutoff; register the hidden future only to construct targets.
Never construct a template using hidden/future visits. Fields are physical RAS-mm pull
maps (future coordinates to current coordinates). MRI interpolation is continuous;
labels use nearest neighbour. Exact zero time, coverage and positive Jacobian checks
are mandatory. The learning grid is separate from native FastSurfer processing.

Freeze the existing 40/8/8 subject assignment. Fit preprocessing on training examples
only, select penalties/checkpoints on development subjects and evaluate once on held-out
subjects. Compare matched score/no-score structural and spatial candidates, no change,
and individual trend. Prediction intervals require held-out coverage evidence. Model
and artifact integrity, supported intervals, visual segmentation/alignment review and
explicit research release gates must pass before serving. Synthetic runs may exercise
the complete software path but can never create a serving release or accuracy claim.

## D026: Integrity-bound review and explicit anatomy report selection

Status: Accepted (2026-10-02)

Segmentation review binds source MRI, native segmentation, versioned statistics,
container digest, subject/scan identity and the complete owned artifact set. Geometry
checks/recovered files do not grant visual approval. Keep conformed mask voxel counts
separate from partial-volume statistics and source-grid display masks. Reports require
explicit anatomy analysis selection; the legacy report default is preserved. Display
only measurement/score changes through the doctor's selected cutoff.

AVRA execution remains an isolated, hash-pinned optional runtime rather than an
unverified installation of old checkpoint dependencies into the app's Python
environment. Pending alignment hides numerical estimates. Mesh helpers verify closed
two-manifold surfaces, physical scaling and a 5% engineering volume tolerance; none
of these tests establishes future-anatomy accuracy or clinical validation.

## D025: Separate longitudinal anatomy analysis and structural forecast

Status: Accepted (2026-10-02, explicit pasted user request)

Reuse existing imported/uploaded MRIs, chronological MR Delay, PostgreSQL jobs,
JSON result persistence, owned artifacts and NiiVue. Add an explicit anatomy job
without reopening legacy predictions in ML-only serving. Baseline manifests, splits,
labels and old models remain immutable. Full-resolution FastSurfer processing is
separate per longitudinal analysis; automated geometry checks never imply visual QC.
The extended DKT dictionary is separate from the compact baseline feature set.
Measured stats and discrete-mask voxel volumes are different estimators; preserve
both, and eTIV cm3 converts to mm3 by multiplication by 1000 before head-size ratios.

AVRA v0.8 is the first rating candidate: verify upstream preprocessing/weights and
license; no qualitative score is synthesized from volume thresholds. Its released
PA model uses ReturnStackedPA (axial/coronal/sagittal slices) and one global
posterior output. Missing FSL/runtime, failed alignment or invalid scores remain
explicit unavailable states. Future-score transitions and 3D geometry stay blocked
until their own held-out evaluation/release evidence exists. Structural baselines
are research comparisons, never a fallback pretending to be a trained spatial model.

## D024: ML-only serving, not a clinical-production claim

Status: Accepted (2026-10-02, explicit user request)

Default serving policy is `ML_ONLY=true`: a single Clinical + FastSurfer forecast,
requiring reviewed real anatomy, trained saved parameters, matched clinical-reference
evaluation and an explicitly promoted, hash-verified artifact release. Do not expose
Demo, feature-delta, precomputed baseline or the poorly generalizing retrospective
checkpoint as new predictions. Preserve historical records and archived reports.
Uploads still validate/store MRI but do not silently enqueue a rule-based analysis.

Processing/training remains explicit offline work, with durable stage status and a
human visual-QC pause. Do not train on unknown labels, relax class-support gates,
resplit after evaluation or substitute clinical-only inference when anatomy fails.
Serving requires all three horizon heads and both classes in development/test
evaluation; the present OASIS data cannot pass. `ML_ONLY=false` is an explicit local
research/test opt-out, not a deployed fallback. This improves serving discipline;
it does not remove research disclaimers or establish clinical production readiness.

Predeclared development gates: ROC-AUC >= 0.7, balanced accuracy >= 0.6 and Brier
no worse than the matched clinical reference. Never choose these thresholds by
inspecting final test results. Require finite metrics and at least 5 training and
2 development/test examples per class; these are execution guards, not power analysis.

User explicitly approved a targeted recoverable Docker repair. Individual socket
operations failed without changes; with Docker stopped, preserve the two-socket `run`
directory as `run.before-repair-20261002` and create an empty replacement. Linux
engine readiness then passed. No factory reset or container/database-volume changes.

The real container required explicit non-root UID/GID (its placeholder UID 999 is
rejected). Configure `1000:1000` for this Windows host, pin the downloaded registry
digest, and keep any surface license requirement unchanged. A source-unit audit also
corrected an earlier documentation/UI label: OASIS-2 eTIV is source cm³/mL, while
FastSurfer anatomical features are mm³. Keep numeric source values unchanged; do not
silently rescale saved inputs or invalidate old checkpoints under the same identity.

## D023 Baseline OASIS forecast with pinned FastSurfer

Accepted 2026-10-02 following the user-supplied FastSurfer Rewired v2 PRD.
The new `src/` study uses baseline CDR-zero subjects and first observed later CDR>0,
named `observed_cdr_conversion`, not MCI-to-Alzheimer diagnosis. MR Delay establishes
observation timing, not biological onset or exact clinical diagnosis dates. Unknown
horizons remain null. Historical 40/8/8 experiments and the functioning full-stack
application are preserved; the PRD's local Streamlit study workspace is added separately.
FastSurfer is an isolated, release-pinned anatomical processor, not another patient dataset.
Tier A/B models are compact logistic regressions with training-only preprocessing and
matched-subject comparisons. Tier C remains optional and unavailable until viable.
Missing runtime, insufficient event support, absent anatomy or unreviewed segmentation
must block the affected output, never silently generate a measurement or probability.

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

## D020: Strict diagnostic forecasting objective

Status: Superseded by D028 (2026-10-02)

An earlier request proposed a distinct documented-MCI-to-Alzheimer-dementia
endpoint. OASIS-2 CDR and `Group` fields do not provide this diagnosis target.
This endpoint is outside the current OASIS-2-only scope and must not be represented
as trained or supported by the supplied data.

## D022: Explicit experimental trained-model integration

Status: Accepted (2026-10-01, user-requested integration)

Expose the audited 40-subject multimodal checkpoint through an explicit `trained` analysis mode, selected by default in the workspace. Preserve the old baseline/demo/cache modes and historical analyses. Freeze the original 40/8/8 subjects; never replace difficult candidates, tune on test results, or promise improved accuracy. This supersedes D018's offline-only restriction solely for experimental research use, not clinical deployment or Alzheimer-specific forecasting.

Return one uncalibrated sequence-classification score for observed CDR increase, with its validation-selected decision threshold, checkpoint fingerprint, cohort membership and recorded reused-holdout performance. Do not manufacture per-visit neural scores or future Alzheimer probabilities. Keep intensity-difference images and structural proxies explicitly separate from model attribution. Trained inference must load validated saved weights and train-only preprocessing, require at least three chronological MRI visits and the documented covariate schema, and fail explicitly instead of silently falling back to the baseline. Missing recorded SES/MMSE use the checkpoint's training-only imputation; absent covariate ingestion must not masquerade as complete demographics.

Import the exact saved training cohort and all of its visits through an explicit offline command, adding source covariates without replacing existing MRI, accounts, splits, checkpoints or reports. Predictions on these 40 subjects are in-sample demonstrations, not accuracy evidence. The selected checkpoint's poor generalization remains prominently disclosed; this integration does not improve its measured performance or satisfy a diagnostic Alzheimer forecasting target.

## D028: OASIS-2 is the sole project dataset

Status: Accepted (2026-10-02, explicit user direction)

Use only the OASIS-2 MRI data and its supplied demographics workbook/CSV. Do not
acquire or combine another cohort. Clinical and demographic predictors must come
from recorded OASIS-2 fields available at the prediction cutoff; later observations
are outcome labels only. The supported baseline forecast endpoint is observed CDR
conversion at horizons with adequate frozen-cohort support. CDR and `Group` do not
establish Alzheimer-specific diagnosis, so the UI and reports must not claim one.
Preserve OASIS-2 raw data, source values, subject splits and existing checkpoints.
