# Anatomy forecasting lifecycle

D062 replaces D061's full-field magnification with local scalar-guided hippocampus
illustrations. The experimental generation path prepares MRI/labels/local field
using the acquired cutoff and learned scalar ratios. The presentation CLI now
prepares the same regional mode for existing forecasts, preserving raw files and
prior results. It uses native-grid volume fitting, 8-mm smooth support within
brain labels, positive Jacobians, source coverage and exact head identity.
This representation is not an evaluated spatial forecast or a disease diagnosis.

D061 prepares 12/24/36-month outputs for the five pinned patients using the same
frozen v3 predictor. It also creates explicitly labeled presentation artifacts
with bounded field magnification, independent of raw outputs and measurements.
Thin-region surface refinement repairs mesh approximation while retaining the
5% native-volume guard; saved source/model files and review status are unchanged.
See the decision log for the scalar limit and queued preprocessing policy.
The queue CLI accepts `--subjects CODE ...` to restrict a batch to requested cases.
`python -m scripts.prepare_forecast_presentations --batch-report PATH --output PATH`
adds new presentation variants for the completed 15-entry annual batch using the
shared compute lock. Earlier results and all original prediction file hashes remain
unchanged; new variants share immutable raw files through local hard links. The
edited manifest and display files are written separately. It does not refit models.

D046 now permits explicit experimental patient-specific inference with the frozen
historical v3 candidate. This does not satisfy the promoted lifecycle below. Use
`experimental: true`, two-to-five prepared observations, and the configured pinned
candidate; preserve unreviewed statuses and disclose failed evaluation gates.
Scalar/mask disagreement is visible in this mode; native geometry still must pass.
The optional CPU `--experimental-only` worker leaves paused preprocessing untouched.
Earlier statements that no real candidate was trained describe the initial stage;
actual historical v3 training/evaluation are recorded in [19](19-fixed-reference-anatomy-run.md).

The first D046 +365-day batch completed six of nine prepared patients. Three failed
regional mesh/mask volume agreement; unavailable outputs were retained as failed
jobs. See [07](07-testing-validation.md) for actual checks and the private runtime
audit. Remaining unprepared patients require the paused Docker preprocessing path.

Current D044 uses a training-only baseline reference and removes the minimum ten
rule. The waiting v3 coordinator was stopped before fitting; all files remain.
Fresh v4 runs reuse verified registrations. The updated worker and offline
coordinator share a PostgreSQL advisory GPU slot. Reload the older worker only
after its active job finishes. See [20](20-training-reference-anatomy-run.md).

## Current fixed-reference feature contract

D043 supersedes training-only reference estimation: use the user's supplied
fixed age-bin means and sample SDs, saved unchanged with each new checkpoint.
The current real run, exact feature definitions, evidence and blockers are in
[19 Fixed-reference anatomy run](19-fixed-reference-anatomy-run.md). Older
checkpoint versions are explicitly rejected. The 44/4/4/4 subject split is
unchanged; partial research fitting never reassigns a training subject to
calibration. Missing calibration yields unavailable uncertainty intervals.
The execution evidence below describes earlier runs and is retained as history.

## Implementation and evidence (2026-10-02)

Latest user direction supersedes the earlier matched-ablation/frozen-40 design:
train only the MTA/Koedam-conditioned model, select the richest available histories
and use a new anatomy-specific split. See decision D029. Prior CDR studies are unchanged.

The supplied implementation plan extends the existing product. Native segmentation,
AVRA execution and alignment review, scalar forecasting, cutoff-local registration,
time-conditioned deformation training, native evaluation, release promotion,
asynchronous forecast jobs, owned NIfTI/GIFTI access, viewer controls and PDF content
are implemented. They reuse the existing worker, PostgreSQL JSON results, storage,
authentication, NiiVue and reports. Historical classifiers and the separate
baseline-only study retain their meanings and artifacts.

The plan's scientific completion condition is **not met**. No real structural/spatial
forecast model has been trained, evaluated or promoted. No real future anatomy is
currently served. Synthetic checks exercise the software but cannot grant release.
There are no independent MTA/Koedam reference ratings, so rating agreement is unverified.
Neither automatic scores nor future anatomy are clinically validated.

Actual work completed locally:

- Imported the frozen 56 subjects and their 185 visits through the existing OASIS
  importer, retaining the original 40-subject training membership and raw MRI data.
- Downloaded the pinned AVRA source and all 15 released ensemble checkpoints. Built
  an isolated CPU/FSL container under the user's explicitly authorized non-commercial
  FSL use. Source and weight digests are recorded in the local runtime manifest.
- Executed upstream preprocessing and all rating ensembles on a real source MRI.
  The first candidate exposed a missing FSL `dc` dependency; a fresh v2 container
  includes `bc`/`dc` and completed the smoke test. Outputs remain pending visual
  alignment review; a successful invocation does not approve alignment.
- Started one native GPU anatomy pilot through the serialized application worker.
  Docker and the worker initially stopped during interruption. The stale socket
  failure was recovered again by preserving the two-socket directory and creating a
  fresh runtime directory. The engine and one worker are running; all 56 subjects
  are queued/processing. The earlier failed pilot remains preserved.
- Created `artifacts/anatomy-score-study-20261002/` from source scan counts and started
  `scripts.run_anatomy_training` at `artifacts/anatomy-score-run-20261002/`. Its durable
  status tracks preprocessing, registration, 20-epoch CUDA training and native
  evaluation. At startup: one subject processing, 55 queued; parameter training had
  not started. Check the local status for current progress.
- Verified an isolated CUDA training image using a synthetic training/save/reload
  cycle on the RTX 3050. The host PyTorch is CPU-only; the waiting coordinator now
  pins the container image and will run real fitting there. See D031. This is not
  evidence that the real forecast candidate has been trained.

Local AVRA artifacts are in `artifacts/avra-runtime-20261002-v2/runtime.json` and
`artifacts/avra-real-smoke-20261002-v2/`. The ignored `.env` points to that runtime.
The earlier candidate and its failure logs are retained. These private artifacts
and MRI data must remain outside Git.

## Result and API contract

`anatomy` is an optional versioned result, independent of CDR risk scores. A measured
analysis contains up to five chronological visits, regional statistics, hard-mask
volumes, asymmetry, reviewed pair changes and continuous automatic rating estimates.
FastSurfer partial-volume statistics and categorical voxel volumes remain separate.
Verified source eTIV in cm3 is converted explicitly to mm3 for ratios. Positive
regional change means growth; annualized change uses the actual interval in days.

The existing segmentation review route binds the source, segmentation, statistics
and complete artifact set. The added rating review binds source MRI, aligned MRI,
alignment transform, CSV, runtime and weights. Pending alignment hides score values;
approval records reviewer, timestamp and the changed provenance digest. The UI review
is about image alignment, not a manual score or an independent agreement assessment.

| Route | Behavior |
|---|---|
| `GET /anatomy-model/readiness` | Promoted release and supported intervals; unavailable reason when blocked |
| `GET /patients/{id}/anatomy-forecasts` | Owner-scoped completed forecast analyses |
| `POST /analysis/{id}/forecast` | HTTP 202; body `{intervalDays, cutoffVisitId?}` queues the existing worker |
| `GET /analysis/{id}/future/{artifact}` | Owner-scoped, allowlisted, digest-checked MRI, labels, regional masks, field or mesh |
| `GET /analysis/{id}/visits/{visit_id}/rating-alignment` | Owned aligned MRI for explicit review |
| `POST /analysis/{id}/rating-qc/{visit_id}` | Body `{visualReviewConfirmed: true}`; provenance-bound alignment approval |
| `POST /reports/{patient_id}?analysis_id={id}` | Explicit measured or predicted anatomy PDF/JSON selection |

Forecasting requires at least two reviewed observations through the selected cutoff.
Choosing an earlier cutoff excludes every later visit, including pending observations.
The worker rechecks immutable parent-result and release snapshots before inference.
Model, score/provenance and source hashes, cutoff, interval and artifact digests are
stored with every forecast. Changed files fail explicitly. No HTTP request performs
MRI inference and no missing prediction falls back to observed or illustrative data.
New fields remain optional for historical results; existing persistence needs no
database migration.

The viewer selects current/predicted anatomy and the generated interval. The UI offers
0, 183, 365, 731 and 1096 days, gated by release support, with zero-time identity.
Playback advances among completed model-generated times; it neither interpolates nor
crossfades anatomy. Acquired and predicted labels remain visible in comparisons and
exports. Scalar observations and forecasts are plotted separately, with evaluated
intervals only where supported.

## Model, geometry and release gates

Each training example uses two-to-four earlier observations to predict the next hidden
visit. Earlier MRI scans are rigidly registered to their own latest-input cutoff.
The hidden future is aligned only to construct supervision. No hidden image, feature,
rating or longitudinal Group enters predictor inputs or registration templates.
The bounded learning grid is independent of original-resolution segmentation.

A small time-conditioned 3D network predicts a smooth **physical RAS-mm pull field**:
an output location samples the current MRI at output position plus displacement.
Conditioning includes reviewed anatomy/rating levels and histories, actual timing,
regional volumes and rates, and available demographics with train-only imputation.
Losses use target deformation, MRI similarity, smoothness, positive Jacobians and
regional volume-change consistency. Exact zero time is enforced by the architecture.
Saved structural models compare no change, individual linear trend and regularized
mixed effects. Only score-conditioned structural and spatial models are fitted; the
user removed the no-score ablation. We cannot claim scores improve accuracy relative
to a no-score model because that comparison is not run.
No future ordinal MTA/Koedam transition model is supplied.

The generated native MRI uses continuous interpolation; labels/masks use nearest
neighbour. Vector resampling does not apply voxel scaling twice. Forecast artifacts
include MRI, full labels, 18 regional masks, the field, a brain-mask boundary mesh and
18 regional meshes. Marching-cubes vertices use the NIfTI affine once. Surfaces are
checked for orientation, degenerate faces, components, closed two-manifold topology
and mask-volume agreement within 5%. No smoothing is applied. Brain-mask boundaries
are not reconstructed cortical surfaces. Positive Jacobians, complete coverage and
non-disappearing regions are required; scalar/mask relative-change discrepancy must
stay within 12 percentage points. These are engineering gates, not clinical thresholds.
Binary meshes use fixed isovalue 0.5001 to resolve exact-midpoint saddle contacts;
the value is recorded with each mesh check. Segmentation voxels remain unchanged.
See D032 for the real-data failure and synthetic regression.

The new study uses all 56 subjects with at least three scans: 43 have three, nine
have four and four have five. Its new split is 44 train / 4 selection / 4 calibration /
4 test. Training includes three five-scan and six four-scan subjects; holdouts retain
longer histories for evaluation. Scan-count selection and fixed-seed assignment exclude
CDR/Group/outcomes. Processing prioritizes descending scan count. This supplies 73
history-to-next-visit examples, including 56 training examples. The old classifier
split remains intact. Only selection chooses checkpoint/penalty; only calibration
fits subject-block 80% intervals. Four calibration/test subjects provide limited
precision; this reused OASIS cohort is not independent validation.

Predeclared release guards include the full frozen cohort, at least 15 epochs,
subject-balanced mean Dice >= 0.70, mean ASSD <= 3 mm, baseline comparisons, horizon
support and interval coverage. Candidate horizons are 183/365/731/1096 days within
90 days of observed follow-up, requiring at least 10 training, three selection and
three test subjects for each supported interval. Native evaluation reuses the actual
generation path, including zero-time MRI/label identity, meshes,
positive Jacobians and physical surface distances. Poor performance or insufficient
support remains a blocker; do not resplit to make gates pass. A release binds the
actual two trained files and evaluation by digest. Synthetic studies cannot promote.

Explicit `--allow-unreviewed-research` exports/training enable provisional candidate
fitting after automated source/geometry/score checks. They retain separate
`automated_checks_only` anatomy and `unreviewed_research` rating states in private
study files; app review records remain pending. Registration remains pending review.
Such a candidate has `review_complete=false`, an explicit release failure and cannot
promote or serve. This permits computation without fabricating reviewer approval.

AVRA's pinned regression output head is unbounded. Under this explicit research
mode, finite estimates outside the nominal MTA 0–4 / PA 0–3 ranges are retained
without clipping, with method `AVRA-v0.8-ensemble-raw-regression-research` and a warning
listing the extrapolated values. They remain `unreviewed_research`; default/reviewed
parsing still enforces nominal bounds. Missing/nonfinite values and changed source
or rating artifacts remain blockers. This corrects the coordinator failure caused
by OAS2_0070 MR4's PA mean -0.00059036014. See D034.

## Run and resume locally

Use the existing Python environment, PostgreSQL and Docker Linux engine. Run one
worker only. Its advisory lock prevents duplicate workers, and its heartbeat continues
during long segmentation/inference. On the next start, interrupted processing jobs
become failed with an explicit retry message; queued jobs resume. Preserve failed job
artifacts and retry through normal analysis actions after runtime recovery.

```powershell
.venv/Scripts/python -m pip install -r requirements-anatomy.txt
# Only for an operator authorized under FSL's separate licence:
.venv/Scripts/python -m scripts.provision_avra --output artifacts/avra-runtime-new --licensed-fsl
# An interrupted prepared build can resume with --resume.
# A fresh build can use --reuse-downloads artifacts/avra-runtime-20261002-v2.
# Set AVRA_RUNTIME_MANIFEST to the resulting runtime.json, then start one worker.
.venv/Scripts/python -m scripts.train_anatomy create-cohort --metadata dataset/oasis_longitudinal_demographics-8d83e569fa2e2d30.xlsx --output artifacts/anatomy-score-study-new
.venv/Scripts/python -m scripts.import_oasis --manifest artifacts/anatomy-score-study-new/app-manifest.csv --refresh-covariates
.venv/Scripts/python -m backend.app.workers.runner
```

In a second terminal, queue a bounded pilot before the full frozen cohort:

Offline cohort/export commands use only `source=oasis-2` patients belonging to the
configured `SEED_EMAIL` account, matching the importer. An identical patient code
under another researcher is not study membership.

```powershell
.venv/Scripts/python -m scripts.train_anatomy queue-cohort --split artifacts/anatomy-score-study-new/subject_split.csv --limit 1
.venv/Scripts/python -m scripts.train_anatomy queue-cohort --split artifacts/anatomy-score-study-new/subject_split.csv
docker build --file infra/anatomy/Dockerfile --tag yodha-anatomy-training:local .
$trainingImage = docker image inspect yodha-anatomy-training:local --format '{{.Id}}'
.venv/Scripts/python -m scripts.run_anatomy_training --cohort artifacts/anatomy-score-study-new --output artifacts/anatomy-score-run-new --epochs 20 --device cuda --training-image $trainingImage
```

The coordinator waits for all real anatomy/score outputs, prepares cutoff-local
registrations, trains the single score-conditioned candidate and evaluates it. It
does not promote. Progress is in `pipeline-status.json`, with failures in execution
logs. `--resume` preserves frozen settings and reuses verified prepared cases; an
interrupted partial training run needs a new immutable candidate directory.
It also prepares completed histories during the wait, preserving full-cohort case
indices and rechecking sources/hashes on reuse. `prepare --completed-only --resume`
records partial progress without publishing `study.json`. The final study is written
only after the complete frozen cohort is usable. Interrupted case directories are
preserved under `.interrupted-*` names before retrying.
On Windows, the coordinator requests system wakefulness for its process lifetime
so idle sleep does not interrupt a long run. It does not change the power plan or
keep the display on; the request clears when the process exits. Shut-down/restart
still interrupts processing and requires the documented recovery/resume steps.
CUDA fitting uses the specified immutable image with read-only workspace/study
mounts and a writable candidate directory. Prepared case paths use portable `/`
separators. Registration and native evaluation use the host environment and its
original source paths. The active image is
`sha256:3e0d9558197c37ae861721e34d9e4c97b1ff6f7cd073692c4e26e70de3bc0049`.
The C: drive now has approximately 77 GB free, sufficient for the complete run and
headroom. The first five-scan training history completed segmentation and scoring;
its actual cutoff-local registration is being checked before full-cohort preparation.
All three real training examples for that subject have now been prepared at 96³;
target fields have positive minimum Jacobians (0.400, 0.347 and 0.340). All 19 native
source-mask meshes for its second scan passed the corrected closure/volume checks.
These remain provisional automated checks, without human review or forecast accuracy.
The three prepared examples also passed real-input CUDA forward/backward/optimizer
preflight steps. They do not constitute the complete frozen-cohort training run.
Evidence: `artifacts/anatomy-real-training-preflight-20261002/execution.json` and
`artifacts/anatomy-native-mesh-probe-20261002-v2/checks.json` (private, ignored).

For a reviewed serving release, inspect each native segmentation and AVRA alignment against its source MRI before
recording the corresponding confirmations in the workspace. Do not restart a worker
while it is processing. When every frozen subject has reviewed anatomy and ratings,
export and prepare a fresh study:

```powershell
.venv/Scripts/python -m scripts.train_anatomy export --split artifacts/anatomy-score-study-new/subject_split.csv --output artifacts/anatomy-export-new.json
.venv/Scripts/python -m scripts.train_anatomy prepare --export artifacts/anatomy-export-new.json --output artifacts/anatomy-study-new
# Inspect every case's rigid/target alignment, then review each case explicitly:
.venv/Scripts/python -m scripts.train_anatomy review-registration --case artifacts/anatomy-study-new/case-0-2/case.json --reviewer REVIEWER --visual-review-confirmed
.venv/Scripts/python -m scripts.train_anatomy train --study artifacts/anatomy-study-new/study.json --run artifacts/anatomy-run-new --epochs 20 --device cuda
.venv/Scripts/python -m scripts.train_anatomy evaluate-native --study artifacts/anatomy-study-new/study.json --run artifacts/anatomy-run-new
.venv/Scripts/python -m scripts.train_anatomy promote --run artifacts/anatomy-run-new
```

Use fresh paths for immutable exports/studies/runs. Training requires every registration
review, not just the example command. Set `ANATOMY_RELEASE_DIR` to a run only after
successful promotion, then restart idle services. API/UI readiness reflects the release
and supported intervals. Failed promotion does not install a forecast.

Upstream implementation and checkpoint conventions:
[AVRA source](https://github.com/gsmartensson/avra_public),
[AVRA v0.8 release](https://github.com/gsmartensson/avra_public/releases/tag/v0.8).
Pinned source commit: `17e947606596e6594ec01d54ef38c992becf9395`.
