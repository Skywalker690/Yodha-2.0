# FastSurfer forecast completion blockers

Current D044 replaces the fixed table with a training-only reference and removes
the minimum ten rule. Six age groups have positive sample SD; the 90–94 group
has one measurement and remains unavailable. Reference scope is 44 declared
training subjects and 33 eligible baselines. Full processing/training/evaluation,
calibrated uncertainty, geometric release checks and supported patient horizons
remain separate prerequisites. The v3 metrics below are historical evidence.

Current fixed-reference anatomy status is in [19](19-fixed-reference-anatomy-run.md).
The supplied constants now give Z-scores for all 16 available examples. A real
20-epoch CUDA candidate was trained with four training subjects, one selection,
one test and no calibration. Scalar MAE is worse than no change, two of three
native exports fail mask/scalar consistency and no requested horizon meets
subject support. One +229-day retrospective evaluation artifact set exists;
it is not a promoted patient-viewer release. The remaining full-cohort processing
is running through one worker in a fresh run, with full-cohort fitting/evaluation
still pending. Reference overlap and unreviewed anatomy/rating agreement remain
explicit limitations, not accuracy claims. The entries below retain earlier
baseline-study status and historical execution blockers.

Current anatomy-extension blockers (2026-10-02): all five baseline outputs are
verified but require human visual QC. The application has zero completed/reviewed
longitudinal anatomy jobs. AVRA weights and the FSL container are pinned and completed
one real-MRI smoke test, but alignment QC and independent agreement remain unverified.
Registration, time-conditioned spatial/scalar training, native evaluation, promotion,
queued forecasts and owned future artifacts are implemented in software. Real reviewed
data, actual model training/evaluation and release are still outstanding. The real GPU
pilot was interrupted when Docker/worker stopped; files are preserved and the job is
failed. The old CDR classifier is not a substitute. See
[18 Anatomy forecasting lifecycle](18-anatomy-forecast-lifecycle.md).

Checked 2026-10-02. This document distinguishes implemented code from verified real-data
completion. The supplied PRD cannot currently be declared fully implemented and validated.

1. **Docker runtime repaired:** the initial pilot failed readiness. A subsequently
   diagnosed stale `dockerInference` socket prevented startup. With explicit user
   approval, only the socket runtime directory was renamed as a recoverable backup;
   Docker Linux readiness now passes. The five-scan pilot was resumed and the pinned
   image pull finished with verified registry digest. The first container launch
   rejected the default UID 999; explicit non-root UID/GID fixed that error. The fresh
   pilot loaded all three VINN checkpoints on CUDA. Processing progress is not
   successful/reviewed segmentation.
   See [repair/workflow](16-ml-only-serving.md) and local pipeline status.
2. **Anatomy:** all five baseline pilot scans produced verified segmentation and
   versioned statistics. Windows failed on Linux aliases for some outputs; explicit
   verification recovered their source/native/output hashes and ROI labels, preserving
   original failures. All five feature rows await visual review; none is approved.
   A real 5–10 scan pilot, visual QC and subsequent eligible full processing must finish
   before Tier B real training/evaluation. Synthetic tests verify software paths only.
3. **Outcome support:** zero events at 12 months; only three at 24 months. The frozen
   training split cannot support either head. At 36 months a clinical model trains,
   but the known test sample has no events. There is no independently validated
   12/24/36-month forecast. Do not resplit after viewing this evidence to improve metrics.
4. **Clinical meaning:** MR Delay is MRI observation timing; separate diagnosis dates
   and strict baseline MCI are not supplied. The implemented endpoint is observed CDR
   conversion. Segmentation cannot create missing diagnoses or future event records.
5. **Reduced anatomy subset:** selected hippocampal/lateral-ventricular/entorhinal
   volumes only. Thickness/surface measures and optional CNN remain unavailable until
   license/runtime, pilot results and feasibility permit independent verification.

Independent work completed: source audit, baseline cohort/label/split, actual clinical
36-month training and reload, FastSurfer runner/parser/provenance/review gates,
matched Tier A/B training/evaluation code, shared predictor, Streamlit and authenticated
Next.js panel, contracts/documentation and synthetic regression checks.

Resume: restore local Docker readiness and start one worker, inspect completed
baseline outputs, approve only reviewed scans, rebuild features, then train
matched models into a fresh artifact directory. Additional outcome follow-up or a
separately approved study design is required for stronger forecasting validation.

ML-only serving is now the default: no legacy or clinical-only prediction fallback.
Until a complete release passes anatomy/QC, support, matched evaluation and promotion
gates, prediction cards remain unavailable even though the web services are online.
