# FastSurfer forecast completion blockers

Current anatomy-extension blockers (2026-10-02): all five baseline outputs are
verified but require human visual QC. The application has zero completed/reviewed
longitudinal anatomy jobs. AVRA weights/FSL runtime and alignment-release checks
are unverified. The required time-conditioned spatial predictor, its training/
held-out evaluation and owned future-artifact serving are NOT implemented end to end.
The old CDR classifier is not a substitute. See [17](17-longitudinal-anatomy.md).

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
2. **Anatomy:** two real scans produced segmentation and versioned statistics;
   Windows failed on their Linux aliases. Explicit output verification recovered those
   records with source/native/output hashes and real ROI labels, preserving the failed
   records and not inventing unknown exit codes. Two feature rows are now pending
   visual review; none is approved for training. A third scan is processing.
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

Resume: finish the pinned image pull and real five-baseline pilot,
inspect segmentation outputs, approve only reviewed scans, rebuild features, then train
matched models into a fresh artifact directory. Additional outcome follow-up or a
separately approved study design is required for stronger forecasting validation.

ML-only serving is now the default: no legacy or clinical-only prediction fallback.
Until a complete release passes anatomy/QC, support, matched evaluation and promotion
gates, prediction cards remain unavailable even though the web services are online.
