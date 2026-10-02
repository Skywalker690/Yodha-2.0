# ML-only serving and actual processing workflow

Latest execution (2026-10-02): all five pilot scans have verified outputs after
`python -m src.fastsurfer.recover`; the resumed run stops at `awaiting_visual_qc`.
Training did not start. Zero reviewed longitudinal anatomy jobs are present in the
application database. See [17](17-longitudinal-anatomy.md) for the separate extension.

The same Docker socket startup failure recurred. With Docker stopped, only `run`
was preserved as `run.before-repair-20261002-anatomy` and recreated. Linux engine
readiness passed, and the pilot resumed. Containers/images/database volumes were
not removed. Both repair backups remain recoverable while Docker is stopped.

The user requested removal of illustrative/rule-based prediction modes. The default
is now **strict ML-only research serving**, not a clinical-production deployment claim.
FastSurfer performs pretrained segmentation; the outcome model is a separately
trained regularized logistic model using clinical inputs and measured anatomy.
Logistic regression learns coefficients from labels; it is not a pattern-matching rule.

## Serving behavior

- `ML_ONLY=true` is the backend default. The patient payload explicitly carries the policy.
- The main patient workspace contains one Clinical + FastSurfer forecast and original
  MRI viewing/upload. Demo, precomputed feature-delta, local feature-delta and the old
  poorly generalizing retrospective neural checkpoint are not new prediction options.
- The API rejects every legacy analysis start and clinical-only forecast selection.
  Uploaded MRI is validated/stored, but no rule-based analysis is automatically queued.
- Historical analyses/checkpoints/reports are preserved. Historical report download
  remains available; no new retrospective PDF is generated as a combined-model report.
- The new worker guard rejects legacy queued jobs when restarted with current code.
  Restart the single existing worker after code changes; do not run two workers.
- `/health` reports `servingPolicy` and aggregate `forecastReadiness`. HTTP 200 for
  service liveness does not mean the prediction release is ready.
- Streamlit also defaults to the combined path. `ML_ONLY=false` explicitly opts into
  local research comparison/legacy regression testing; it is never a fallback.

## Release contract

`FORECAST_ARTIFACT_DIR` defaults to `artifacts/forecast_v2` and
`FORECAST_PROCESSED_DIR` to `data/forecast_v2`. A release directory must contain
Clinical + FastSurfer and matched clinical-reference JSON models and evaluations,
plus `serving_manifest.json` created by explicit promotion. Prediction verifies
every release file hash and the current study source hashes. No training happens
inside an HTTP request.

Promotion checks exact feature/task versions, matched subjects/scans and sources,
positive finite reviewed anatomy, matching model/evaluation fingerprints,
clinical source-unit metadata (eTIV cm³/mL, anatomy mm³), all three
trained horizon heads, at least 5 known training examples per class and 2 per class
in development/test. Metrics must be finite. Predeclared development gates require
ROC-AUC >= 0.7, balanced accuracy >= 0.6, and Brier no worse than matched clinical.
Test scores do not choose thresholds or models. These are execution/quality guards,
not a statistical power calculation or evidence of clinical validation. Probabilities
remain explicitly uncalibrated; adequate calibration/external validation remains work.

The current data cannot pass: zero 12-month events, one 24-month training event and
zero known 36-month test events. All serving predictions therefore remain unavailable.
Do not modify splits, infer missing diagnoses or relabel unknown follow-up to pass.

## Explicit processing/training run

From the repository root with the existing virtual environment:

```powershell
.\.venv\Scripts\python -m scripts.run_ml_pipeline --run-dir artifacts/ml_only_next_run --batch-size 5 --pull-image
```

Choose a fresh run name for a new study run; do not start this example alongside the
active pilot. Two pilot scans have verified outputs pending visual QC; a third is
processing at this status snapshot. The active pilot is `artifacts/ml_only_20261002_uid`; initial runtime/container-user
failures remain recorded in the earlier `ml_only_20261002` run. Do not invoke resume
while the active pilot is running. After it pauses, resume rather than overwriting:

```powershell
.\.venv\Scripts\python -m scripts.run_ml_pipeline --run-dir artifacts/ml_only_20261002_uid --batch-size 5 --resume
```

Stages are saved in `<run-dir>/pipeline_status.json`: preflight, processing,
blocked_runtime, blocked_processing, awaiting_visual_qc, training, blocked_training, blocked_outcomes
or release_ready. Actual image pull/container execution happens only after Docker
readiness. Existing completed scans are reused only after their provenance, source
and output hashes match; they are never overwritten.
New invocations take an OS-held per-study lock to reject duplicate processing/training.
Timed-out container jobs stop only their own generated container name, not other
containers or any volumes. The pilot already running before these hardening changes
must finish before invoking resume; do not start a second command alongside it.

Actual pinned image digest: `sha256:11d594ae6fea7b1dde5b66ba5124b6295c4eedf1f401e21c7319c22eefd55c50`.
FastSurfer rejects its default placeholder UID 999. The runner now passes explicit
non-root `container_user: "1000:1000"` for this Windows Docker environment; on Linux,
configure the real non-root host UID/GID with read/write permissions on the mounts.
The real retry confirmed CUDA and CPU view aggregation plus all three VINN checkpoints
loaded. Segmentation accuracy still requires visual review. Source/output hashes use
portable POSIX-relative artifact names.

The first actual scan took approximately 925 seconds (15.4 minutes), including
postprocessing and the host alias-verification failure. A spot resource check showed
about 3.5 GiB container RAM, not a measured peak. This is one observation, not a
universal throughput guarantee; full-cohort processing is lengthy. Disk free space
after image/runtime allocation was about 17.8 GiB. Check storage headroom before a
full 85-scan batch rather than assuming the initial 39.7 GiB remained available.

Windows cannot follow the container-created `aseg+DKT.stats` Linux alias. The adapter
reads the real `stats/aseg+DKT.VINN.stats`, consistent with the no-CC segmentation.
An explicit `python -m src.fastsurfer.recover` verifies already-produced files,
source/native hashes, exact ROI statistics and actual segmentation labels after an
alias-related OSError, preserves the failed record, and marks output verification
without inventing an unknown container exit code or approving visual QC.
The already-running pilot imported the old alias-check code before this correction;
after it stops, run recovery for finished outputs, then resume with the corrected
runner. Verified completed outputs are reused, not recomputed. Never run a second
segmentation pipeline beside the active one.

After a successful pilot, a qualified reviewer must inspect real segmentation over
T1. Approve each reviewed scan using the documented `src.fastsurfer.qc` command.
Resume with `--batch-size 85` for all baseline subjects, inspect/approve the remaining
segmentations, then resume again to train. The pipeline does not auto-approve QC.
Once every baseline has reviewed features, it fits/evaluates the clinical matched
reference and combined model using frozen splits and known labels. It pauses instead
of promoting when outcome/release gates fail. Candidate models stay under this run's
`models/`, separate from old artifacts.

If a future run genuinely reaches `release_ready`, set `FORECAST_ARTIFACT_DIR` to
that run's models directory in the ignored local environment, restart the API and
check `/health`. Do not promote the current clinical-only model as a combined release.

## Docker repair performed with user approval

Docker startup failed because its inference manager could not access/remove a stale
zero-byte `dockerInference` reparse-point socket (Windows error 1920). Individual
rename/reparse-point removal failed without changes. With Docker stopped, the runtime
directory containing only two zero-byte socket entries was moved to
`C:\Users\Sanjo\AppData\Local\Docker\run.before-repair-20261002`; a fresh `run`
directory was created. Docker Linux engine readiness then passed. No factory reset,
image/volume deletion or host PostgreSQL change occurred. Preserve the backup; it
allows directory-level recovery while Docker is stopped.

Current execution evidence is local run status and per-scan processing logs. A
running/download stage is not completed segmentation, training or validated accuracy.
