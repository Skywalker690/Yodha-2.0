# Product Requirements

## Product

## Longitudinal anatomy extension requested 2026-10-02

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

The FastSurfer Rewired v2 PRD adds the primary **baseline-only OASIS observed CDR
conversion** study: one earliest CDR-zero baseline per subject, later observations
for labels only, clinical reference and compact reviewed anatomical features,
12/24/36-month estimates only where supported. This is not strict MCI-to-Alzheimer
forecasting. That earlier objective remains unfulfilled and separately documented.
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

## Strict forecasting extension (requested 2026-10-01)

The user selected the strict MCI-to-Alzheimer forecasting direction from the supplied October 2026 complete PRD. The new research task uses a documented MCI baseline and future study-defined Alzheimer dementia diagnoses at 12, 24 and 36 months. Do not infer MCI from CDR alone, MRI appearance or the OASIS-2 Group field. Do not equate any dementia diagnosis with Alzheimer dementia without documented source semantics.

Acquire an authorized longitudinal dataset and audit eligibility, event counts, follow-up and MRI linkage before training. Unknown/censored horizons remain unknown. Fit baseline models before the advanced MRI/fusion branch; suppress unsupported horizons. Baseline inputs must not contain future visits or features computed using them. Follow-up visits establish outcomes, not baseline predictors.

This changes the research objective, not the deployed application immediately. Existing OASIS cases, split manifests, checkpoints and analyses remain intact and explicitly historical/demo or retrospective. They do not satisfy the strict forecasting requirement. Preserve the local Next.js/FastAPI/PostgreSQL architecture; the supplied PRD's alternative stack is a suggestion, not a requirement to replace functioning services. See [13 Strict forecasting data](13-strict-forecasting-data.md) for the acquisition gates and current limitations.

## Trained retrospective integration (requested 2026-10-01)

The user subsequently requested use of the existing 40-subject checkpoint in the application. Provide explicit experimental trained inference, one sequence-level observed-CDR-increase score, frozen cohort and checkpoint provenance, strict source-input checks and prominent poor-performance/in-sample caveats. Do not invent a neural trajectory or claim improved accuracy. See [14 Trained inference](14-trained-inference.md). Strict future forecasting remains a separate unmet requirement.
