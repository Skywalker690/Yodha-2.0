# Longitudinal anatomy extension

## Current implementation boundary (2026-10-02)

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
report. The current-versus-predicted control and requested-time selector show that
future anatomy is unavailable until a predictor is trained, evaluated and released.
No image, mesh, score or uncertainty is generated as a substitute.

## Not complete or scientifically verified

- AVRA v0.8 has a worker execution adapter requiring a digest-pinned Linux runtime
  and a hash allowlist of all upstream MTA/PA/GCA-F checkpoints. It uses upstream
  preprocessing, records private alignment/CSV provenance and hides unverified scores.
  There are no installed/pinned weights or verified FSL/AC-PC runtime, nor a completed
  alignment-review release workflow.
  MTA-left/right and one PA score therefore remain unavailable; independent agreement
  ratings are also absent.
- `ml/anatomy/structural.py` contains offline feature, baseline, penalized mixed-effects
  candidate and subject-held-out evaluation helpers. These are not a saved trained,
  evaluated or serving release; no future volumes or intervals are returned.
- `ml/anatomy/spatial.py` contains geometric warp/Jacobian and optional mesh utilities,
  not registration, a trained time-conditioned deformation predictor, generated
  future NIfTI/GIFTI artifacts, or held-out Dice/surface-distance evaluation.
  SimpleITK and scikit-image are installed and recorded in `requirements-anatomy.txt`.
  `VolumeCanvas` supports bounded authenticated GIFTI loading and explicit predicted
  labels/snapshots, but no evaluated predictor/artifact endpoint supplies real future
  meshes. The required end-to-end future rendering is NOT complete.
- The current viewer label interpolation setting is viewer-wide; nearest-neighbour
  rendering protects the categorical label overlay, but also affects the source MRI
  display in that viewer. This is a display choice, not a change to saved source data.
- All five baseline pilot outputs are verified, with original failure records
  preserved. The resumed pipeline stops at `awaiting_visual_qc`, not training.
  A read-only database check found zero completed longitudinal anatomy jobs and zero
  reviewed longitudinal visits. The anatomy worker has not run on real patient scans.
- The OASIS horizon model remains a different task: observed CDR conversion, not strict
  MCI-to-Alzheimer dementia. Sparse events do not support an all-horizon model.

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
This is a runtime interface, NOT a provided/tested container distribution. AVRA code
is MIT; FSL has separate terms requiring operator verification before packaging.
Current checkpoint/runtime compatibility and reference-rating agreement are unverified.

Alternative investigated: [MRI Visual Scores](https://github.com/l-kuo/mri_visual_scores)
provides MTA/ERICA/GCA, not the required Koedam PA output. It cannot silently replace
the whole scorer. [AVRA upstream](https://github.com/gsmartensson/avra_public)
documents continuous ensemble outputs and native-T1 FSL preprocessing.

The uploaded plan's completion condition is not yet met. Remaining work is actual
longitudinal segmentation and visual QC, verified automatic scoring/alignment release,
frozen-subject structural training with matched score ablation, evaluated intervals,
historical rigid/nonlinear registration, trained time-conditioned deformation model,
held-out overlap/surface/volume validation, and serving matching future NIfTI/GIFTI
artifacts in the viewer. Existing CDR models do not satisfy these future targets.
