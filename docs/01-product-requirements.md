# Product Requirements

## Product

The user-provided nWBV reference is an optional descriptive biomarker alongside
analysis outputs. Compare recorded, method-matched OASIS nWBV with the bundled
age-bin research reference. It is a support value, not an Alzheimer/MCI diagnosis,
future-risk estimate, spatial forecast or model training feature. See D033.

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

NeuroPredict AI is a clinical research platform that analyzes repeated MRI scans from the same subject and presents an understandable progression story over time.

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
- Dashboard snapshot for a selected patient and observed visit: source demographics, recorded clinical values, automatically available MTA/Koedam research estimates, regional hippocampal measurements and provenance-labeled longitudinal volume change. Unreviewed outputs remain explicitly labeled; missing source values remain unavailable.
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
