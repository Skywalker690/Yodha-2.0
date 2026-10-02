# Product Requirements

## Guided cognitive assessment import (2026-10-03, D073)

Import the new remote chatbot assessment features through reviewed diffs without
merging branches. Uploaded patient visits support clinician-administered original
English demo tasks, eleven task groups, a server-calculated total out of 30,
draft/resume and immutable completed attempts. Demo results are labeled and stored
as `cognitiveDemoScore`, separate from clinical `MMSE` and all model inputs.
Preserve imported observations, forecast eligibility and current MRI/dashboard
behavior. Optional locally configured authorized original-MMSE content retains
the source branch's separate standard-score path; no questionnaire is bundled.
See [22 Cognitive assessment](22-cognitive-assessment.md).

## Hackathon clinical assistant (2026-10-03)

Add an authenticated floating patient-workspace chat widget using Gemini for concise case summaries,
missing-information review, explanations of current outputs and optional web references.
Patient context is rebuilt server-side, with numeric source fields and explicitly labeled
anatomy/QC and forecast availability. Raw MRI, patient codes/UUIDs, notes, paths and owner
information are excluded. Recent chat lives only in browser memory. Gemini receives the
structured context and user messages; use synthetic/OASIS de-identified demo cases.
This is an explicit exception to fully local computation (D063), preserving the clinical
research intended use and existing ML-only release gates. See [21 Clinical assistant](21-clinical-assistant.md).

## Product

D072 opens the spatial MRI workspace in axial view and explains when hippocampus
highlighting awaits a matching FastSurfer segmentation.

D071 accepts paired `.hdr`/`.img` MRI acquisitions directly in the upload screen,
alongside existing `.nii`/`.nii.gz` volumes.

D070 generates patient codes automatically and requires age and nWBV for new
patients and MRI uploads. New patients start with a pending baseline MRI visit.

D069 removes Settings from sidebar navigation.

D068 removes dashboard BMI, total hippocampus and hippocampal volume change cards,
and hides unavailable dashboard measurement cards and result panels.

D062 restores head geometry in the forecast viewer and shows hippocampal volume
progression in a separately identified scalar-guided illustration.

D061 opens patient-specific 12/24/36-month experimental forecasts for the five
pinned patients, showing actual model progression without enforcing its direction.

D060 removes the repeated experimental preview badges from MRI workspace
forecast positions and the unavailable anatomy card.

D059 removes MRI Analysis from sidebar navigation.

D058 defaults the MRI Analysis patient selector to OAS2_0048 when available.

D056 lets researchers delete their pending empty visits from the MRI upload
screen. Visits containing MRI or analysis/derived references cannot be deleted.

D055 puts the user-selected patient codes first in the patient directory, in
their supplied order, while preserving search and other patients' existing order.

D054 removes the standalone MRI timeline section from the default patient page.
MRI visit selection and navigation inside the 3D workspace remain available.

D053 removes the complete baseline Clinical + FastSurfer forecast section from
the default patient page, including readiness and blocked horizon content. Anatomy
measurements and future MRI exploration remain separate capabilities.

D051 applies yellow hippocampus highlighting to acquired/input comparison panels
using each scan's measured mask, including the saved preview and baseline panels.

D050 restores yellow hippocampus highlights in experimental comparisons and makes
volume cutaways apply to the MRI and labels together. Camera/zoom and spatial
positioning must stay shared; correcting rendering must not fabricate model changes.

D049 makes generated anatomy reviewable against its actual input cutoff in matched
slices. Quantify the saved deformation and mask changes separately from scalar
estimates; preserve model outputs and disclose disagreement without exaggeration.

D048 makes the D046 opt-in visible beside unavailable future anatomy and supports
explicit experimental-view links. Preserve ordinary default serving and all artifact
matching gates; label generated images as unvalidated experimental previews.

D046 adds user-requested patient-specific experimental forecasts using the frozen
historical v3 model (four train, one selection, one test). Require opt-in and
two-to-five prepared scans, label outputs unvalidated, preserve source/review
provenance and display scalar/mask disagreement. Default promoted serving and
current v4 fitting requirements remain. Never substitute another patient's example.

D047 adds pre-generated 12-, 24-, and 36-month outputs from the earlier six-subject
CUDA experiment to the separate `/preview` gallery. These use its OAS2_0073
four-scan cutoff; the saved +229-day example remains from the later v3 candidate.
Display each checkpoint's version and split, state that the long intervals have no
matched acquired scan, and show output discrepancies. This gallery does not alter
patient-specific forecast availability.

The explicitly requested immediate visual preview (D045) displays the saved
OAS2_0073 +229-day historical evaluation example on a separate page. Keep its
original subject/time and unvalidated, unpromoted provenance visible. It is
independent of the default serving model and never fills an unavailable horizon.

Current anatomy direction is D044: fit the reference only from baseline-CDR-zero
subjects in the frozen training role. Remove the ten-subject cutoff; require only
enough valid measurements to calculate a positive sample SD. Freeze it with both
forecast checkpoints. Held-out subjects never fit it. This supersedes the fixed
reference experiment below, which is preserved as history.

Latest anatomy request (D042/D043): the new future-anatomy model uses the supplied
fixed age-group nWBV means/SDs to calculate each patient's age-adjusted nWBV Z-score,
MMSE, the 18-region FastSurfer dictionary, AVRA left/right MTA and Koedam estimates,
chronological anatomical changes and actual elapsed intervals, registered acquired
MRI history and masks. Raw nWBV and age are source/provenance values only; education,
SES, sex, handedness, eTIV and ASF do not condition either new forecast model.
The user's correction explicitly replaces training-only reference construction
with the supplied fixed table. Freeze it with the checkpoints and disclose its
OASIS-2 origin and possible held-out overlap. This changes neither the separate
historical classifiers nor the descriptive biomarker's existing purpose.

The original nWBV reference biomarker remains an optional descriptive value alongside
analysis outputs. Compare recorded, method-matched OASIS nWBV with the bundled
age-bin research reference. It is a support value, not an Alzheimer/MCI diagnosis,
future-risk estimate or spatial forecast. Its existing descriptive contract remains
separate from the new saved-model Z-score feature above. See D033/D043.

## Longitudinal anatomy extension requested 2026-10-02

Latest user direction: train only the MTA/Koedam-conditioned anatomy model, using
subjects with the most available scans rather than the historic 40-subject training
membership. The new anatomy study has its own frozen scan-count-based split;
historical classifier/baseline splits are preserved. See decision D029.

Extend the existing workspace/worker with native-resolution anatomical masks,
automatic MTA-left/right and posterior-atrophy estimates, regional changes and a
separate structural forecast. Preserve the baseline-only study and historical
classifier; two-to-five-visit anatomy histories do not change classifier eligibility.
Future 3D anatomy requires a trained/evaluated time-conditioned deformation model,
not uniform shrinkage, rule-derived scores or crossfades. Unsupported outputs remain
unavailable. The implementation and uncompleted scientific gates are tracked in
[17 Longitudinal anatomy](17-longitudinal-anatomy.md).

## Current baseline forecasting direction requested 2026-10-02

The subsequent user request switches the default application to **ML-only serving**:
Clinical + FastSurfer only, no illustrative/rule-based or historical neural fallback.
Keep those artifacts archived, require a promoted release and reviewed anatomy, and
start actual offline processing/training through durable gates. The clinical-production
non-goal and research disclaimer remain: this switch cannot manufacture missing
future events or establish accuracy. See [16 ML-only serving](16-ml-only-serving.md).

The FastSurfer Rewired v2 PRD adds the primary **baseline-only OASIS-2 observed CDR
conversion** study: one earliest CDR-zero baseline per subject, later observations
for labels only, demographics and clinical reference features, and reviewed compact
anatomical features. Twelve-, 24-, and 36-month estimates are available only where
the supplied cohort supports them. This predicts observed CDR conversion; it does
not identify or diagnose Alzheimer disease.
Preserve the existing Next.js/FastAPI/PostgreSQL product and historical models; add
the requested Streamlit study workspace through one shared predictor adapter.
No validated all-horizon default is claimed before runtime, QC, event support and
matched evaluation gates pass. See [15 Architecture](15-fastsurfer-architecture.md)
and [current blockers](blockers.md).

Alzhio is a clinical research platform that analyzes repeated MRI scans from the same subject and presents an understandable progression story over time.

## Primary user

The primary user is a researcher or clinician reviewing longitudinal cases. The application is not patient-facing.

## MVP capabilities

- Researcher login using JWT.
- Patient list and patient creation.
- MRI visit creation and upload.
- MRI storage in local filesystem or local S3-compatible storage.
- Asynchronous analysis jobs.
- Three or more chronological visits per case.
- Progression-risk trajectory.
- Structural-change metrics.
- MRI and explanation comparison.
- Interactive 3D MRI volume exploration, multiplanar slices, cutaway clipping and linked longitudinal comparison (user-requested extension, 2026-10-01).
- Dashboard snapshot for a selected patient and observed visit: available source demographics, recorded clinical values, MTA/Koedam research estimates and regional measurements. Unreviewed outputs remain explicitly labeled; missing values are hidden. BMI, total hippocampus and hippocampal volume change cards are omitted (D068).
- Short, cautious interpretation.
- Research report generation and download.
- Explicit output provenance: demo, precomputed, or inference.
- Persistent research-prototype disclaimer.

## Explicit non-goals

- Autonomous diagnosis or treatment recommendations
- Production clinical deployment
- EHR integration
- Patient self-service
- Full OASIS-2 processing during a live demo
- Clinical validation claims
- Kubernetes, Kafka, Redis, service mesh, or unnecessary microservices

## Demo acceptance criteria

Within one minute, a reviewer can sign in, select or create a patient, see three visits, start analysis, observe job progress, view the risk trajectory, inspect structural metrics and a heatmap, and download a research report.

## Product language

Use “progression-risk estimate” and “research visualization.” Avoid “diagnosis,” “clinically proven,” “medical recommendation,” and unsupported certainty.

## Trained retrospective integration (requested 2026-10-01)

The user subsequently requested use of the existing 40-subject checkpoint in the application. Provide explicit experimental trained inference, one sequence-level observed-CDR-increase score, frozen cohort and checkpoint provenance, strict source-input checks and prominent poor-performance/in-sample caveats. Do not invent a neural trajectory or claim improved accuracy. See [14 Trained inference](14-trained-inference.md).
