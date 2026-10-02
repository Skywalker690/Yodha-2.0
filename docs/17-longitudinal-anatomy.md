# Longitudinal anatomy extension

## Current implementation boundary (2026-10-02)

Latest direction: only MTA/Koedam-conditioned training, with the new scan-count cohort
and 44/4/4/4 subject split. An explicit private research mode permits candidate fitting
before visual review, while preserving the release review gate. The earlier
matched-ablation and frozen-40 requirements below are superseded by D029 and
[18](18-anatomy-forecast-lifecycle.md).

The extension adds a separately versioned `anatomy` analysis to the existing patient
workspace and asynchronous worker. It accepts one visit for measurements or two to
five visits through the selected chronological cutoff. It does not change historical
classifier eligibility, baseline manifests, splits, labels or compact forecast features.

Each visit uses the existing pinned native-resolution FastSurfer runner. The separate
`dkt-longitudinal-v1` dictionary reads bilateral hippocampus, lateral ventricles,
entorhinal, inferior/middle/superior temporal, inferior/superior parietal and precuneus
statistics. A source-grid nearest-neighbour resampling produces categorical NIfTI
masks for the combined label image and each region. FastSurfer statistics (partial
volume estimation) and hard-label voxel counts (mask estimator) are presented as
different quantities. Masks retain the source affine and use millimetres. The eTIV
conversion applies only to source OASIS-2 values recorded in cm3/mL: multiply by 1000
to compare with mm3. Missing or unverified units remain unavailable.

The job records raw-source and segmentation digests, method and dictionary versions,
volume units, observed metadata and owned artifact digests. The existing report route
can emit a separate anatomy report. `GET /analysis/{id}` remains owner-scoped; the
artifact route allowlists named regions and verifies the per-analysis artifact manifest
and content digest. A researcher must inspect each segmentation against its MRI before
posting the explicit visual-review confirmation. The API binds that review to the
current raw scan, segmentation, and complete unchanged artifact set, and records the
reviewer and time. Only reviewed pairs yield longitudinal volume changes. These
measurements do not imply spatial registration or tissue movement.

The workspace can display the measured labels over the selected acquired MRI, measured
volume tables, asymmetry, source nWBV/MMSE/CDR history, processing/QC and an anatomy
report. The current-versus-predicted control and requested-time selector use queued
forecasts and owned NIfTI/GIFTI artifacts from an evaluated release. Until real
training, evaluation and promotion pass, future anatomy remains unavailable.
No image, mesh, score or uncertainty is generated as a substitute. The implemented
training/release and application lifecycle is documented in
[18 Anatomy forecasting lifecycle](18-anatomy-forecast-lifecycle.md).

## Not complete or scientifically verified

- AVRA v0.8 has a worker execution adapter requiring a digest-pinned Linux runtime
  and a hash allowlist of all upstream MTA/PA/GCA-F checkpoints. It uses upstream
  preprocessing, records private alignment/CSV provenance and hides unverified scores.
  All 15 upstream checkpoints are now hash-pinned locally and the isolated FSL runtime
  completed preprocessing and scoring on one real MRI. The API/UI alignment-review
  workflow is implemented; smoke-test scores remain pending review. Independent
  agreement ratings are absent, so rating accuracy is unverified.
- `ml/anatomy/` now includes cutoff-local rigid/target registration, train-only scalar
  preprocessing, saved mixed-effects models, matched score ablations, a time-conditioned
  3D displacement model, subject-held-out calibration/evaluation and native artifact
  generation. Synthetic save/reload checks pass. No real anatomy model is trained or
  promoted, so future measurements and evaluated intervals remain unavailable.
- Native MRI, labels, 18 masks, physical displacement and brain/region GIFTI generation,
  native overlap/surface evaluation, owned future serving, current/predicted controls
  and generated-time playback are implemented. No real evaluated predictor supplies
  future meshes yet. The required scientifically evaluated future rendering is NOT
  complete. SimpleITK and scikit-image are recorded in `requirements-anatomy.txt`.
- The current viewer label interpolation setting is viewer-wide; nearest-neighbour
  rendering protects the categorical label overlay, but also affects the source MRI
  display in that viewer. This is a display choice, not a change to saved source data.
- All five baseline pilot outputs are verified, with original failure records
  preserved. The resumed pipeline stops at `awaiting_visual_qc`, not training.
  A read-only database check found zero completed longitudinal anatomy jobs and zero
  reviewed longitudinal visits. One real longitudinal anatomy pilot began on GPU but
  Docker and the worker stopped during interruption. Its job is failed and its files
  preserved; this is not successful processing or QC.
- OASIS horizon outputs concern observed CDR conversion and do not represent
  Alzheimer-specific diagnoses. Sparse events do not support an all-horizon model.

## Reproducible follow-up

First complete/recover the existing serialized FastSurfer pilot, then have a qualified
reviewer inspect its real scans. Do not run a second GPU segmentation batch concurrently.
Run anatomy jobs only through the application worker, one per patient, and inspect the
source MRI and labels in axial, coronal and sagittal views before recording QC. Preserve
all raw scans and existing baseline experiment artifacts. Check [16 ML-only serving](16-ml-only-serving.md)
for pilot state, disk/runtime recovery and model release gates.

Synthetic unit and API tests must cover geometry/units, malformed segmentation,
chronology, ownership, integrity failures, required manifest contents, explicit review,
unavailable ratings and future outputs, and historical result compatibility. Browser
checks must confirm the panel is available in both workspace variants and that the
existing viewer's MRI and baseline comparison remain usable. Synthetic checks establish
software behavior only; actual anatomical quality needs real reviewed/evaluated data.

## Configuration and compatible API

Install optional geometry dependencies using `python -m pip install -r requirements-anatomy.txt`.
Restart the single existing worker after code changes; do not run competing GPU workers.
`POST /analysis/{cutoff_visit_id}` accepts `outputMode: anatomy` and optional
`futureIntervalDays` (default 365, range 0–3650). The result stores native measurements
but does not promise a forecast for that interval. Reviews use
`POST /analysis/{id}/anatomy-qc/{visit_id}` with `visualReviewConfirmed: true`.
Owned artifacts use `GET /analysis/{id}/visits/{visit_id}/anatomy/{artifact}`;
`regions`, `segmentation`, and the 18 region keys are allowlisted. Raw data is unchanged.
`POST /reports/{patient_id}?analysis_id={id}` selects the anatomy report explicitly;
omitting that parameter preserves the legacy completed-analysis report behavior.

An operator-provided `AVRA_RUNTIME_MANIFEST` JSON must contain `image` (registry
digest), `weights_dir` (local path), and `weights_sha256` (relative file-to-hash map).
The image must provide the verified upstream entry point `/opt/avra/avra.py`, FSL
with MNI152 1-mm template, compatible checkpoint loading and its dependencies.
Patient mounts are read-only, network is disabled and output logs remain private.
The pinned container provisioner is `scripts/provision_avra.py`; it preserves source,
weights, build logs and a runtime manifest in a fresh artifact directory. AVRA code
is MIT; FSL has separate terms. The user authorized non-commercial FSL research use
for this installation. The v2 container completed real-MRI upstream preprocessing and
scoring; alignment quality and reference-rating agreement remain unverified.

Alternative investigated: [MRI Visual Scores](https://github.com/l-kuo/mri_visual_scores)
provides MTA/ERICA/GCA, not the required Koedam PA output. It cannot silently replace
the whole scorer. [AVRA upstream](https://github.com/gsmartensson/avra_public)
documents continuous ensemble outputs and native-T1 FSL preprocessing.

The uploaded plan's completion condition is not yet met. The remaining work is actual
longitudinal segmentation, segmentation/alignment/registration visual QC, real
frozen-subject model training, held-out scalar/interval/spatial evaluation and successful
release, followed by verifying matching real predicted artifacts in the viewer.
The software for these stages is implemented; the execution evidence is not.
Existing CDR models do not satisfy these future targets.
