# FastSurfer forecast completion blockers

Checked 2026-10-02. This document distinguishes implemented code from verified real-data
completion. The supplied PRD cannot currently be declared fully implemented and validated.

1. **Docker runtime:** Docker Desktop was started, but the Linux engine did not respond
   within the bounded runner readiness check. The five-scan pilot exited with
   `TimeoutExpired`; no segmentation succeeded. A downloaded source folder is not a
   working runtime. No image/weights download or registry digest was verified.
2. **Anatomy:** all 85 feature-table rows are unavailable, not synthetic replacements.
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

Resume: restore Docker Linux engine, pull the release-pinned image, run five baselines,
inspect segmentation outputs, approve only reviewed scans, rebuild features, then train
matched models into a fresh artifact directory. Additional outcome follow-up or a
separately approved study design is required for stronger forecasting validation.
