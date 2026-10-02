# Full-Stack Architecture

The merged Alzhio Bot feature adds an optional external text-processing path to
the existing FastAPI service. An authenticated patient endpoint rebuilds an
allowlisted case context and calls Gemini only after a submitted question.
MRI processing and forecasting remain in the existing local worker. This is the
explicit synthetic/de-identified demonstration exception in D063/D066; see
[21 Clinical assistant](21-clinical-assistant.md) for configuration and data scope.

The separate native anatomy job extends existing persistence and worker/viewer
boundaries without new services. Its implemented interfaces and incomplete
forecasting/runtime gates are specified in [17 Longitudinal anatomy](17-longitudinal-anatomy.md).

## Current architecture baseline forecast plus preserved longitudinal product

Default serving now routes only to the promoted combined model under
[16 ML-only serving](16-ml-only-serving.md). Legacy prediction code/data below remains
archival/research-only. An explicit offline pipeline handles container processing,
human QC, training, evaluation and gated promotion; no GPU work runs in HTTP.

The current user-supplied FastSurfer v2 PRD is specified in
[15 Baseline forecast architecture](15-fastsurfer-architecture.md). The architecture
separates patient data, pretrained anatomical processing and outcome modeling:

```text
OASIS-2 workbook → baseline predictors ────────────────────────────────┐
OASIS-2 baseline full-head T1 → isolated pinned FastSurfer → reviewed anatomy
                                                                    │
Follow-up records → censored horizon labels → frozen subject split ──┤
                                                                    ▼
                           Tier A / Tier B training and matched evaluation
                                                                    ▼
                            safe JSON models → src.risk.predict adapter
                                         ├→ loopback Streamlit study UI
                                         └→ owned FastAPI endpoint → Next.js forecast panel

Existing MRI visits → PostgreSQL asynchronous worker → historical longitudinal results
                                  └→ original voxel viewer / retrospective reports
```

No demographic or follow-up data is sent to FastSurfer; it receives the one baseline
T1. It supplies measurements, not forecast labels. No future visit enters the new
predictor. CLI processing and training are outside HTTP; tabular prediction is cheap
CPU inference. All patient files/parameters are ignored local artifacts. Runtime,
anatomy QC and outcome support failures remain explicit. The existing authenticated
product and host-local PostgreSQL remain intact; no new queue or database service.

The real FastSurfer pilot and Tier B model are currently blocked; see
[blockers](blockers.md). The sections below document the retained longitudinal
product, not a claim that its retrospective neural model supplies future probabilities.

## Design goal

Build a genuine full-stack clinical research platform while keeping the number of services small enough for a hackathon. The complete MVP runs locally.

```
Next.js browser application
        │ REST, polling, or WebSocket job updates
        ▼
FastAPI backend
   ├── JWT auth and researcher accounts
   ├── Patient and visit APIs
   ├── MRI upload API
   ├── Analysis job API
   └── Report API
        │
   ┌────┼───────────────┐
   ▼    ▼               ▼
PostgreSQL  Local storage  Python ML pipeline
metadata    MRI/results  PyTorch + MONAI + LSTM + XAI
```

## Repository structure

```
frontend/
  app/ components/ lib/ types/
backend/
  app/api/ app/core/ app/db/ app/models/ app/schemas/
  app/services/ app/workers/
ml/
  preprocessing.py encoder.py temporal_model.py
  inference.py explainability.py contracts.py
scripts/ tests/ infra/
```

## Technology choices

- Next.js and TypeScript: product UI, routing, and typed API integration.
- Tailwind and shadcn/ui: fast, consistent research-platform screens.
- Recharts and Lucide: charts and interface icons.
- NiiVue 0.69.0: client-only NIfTI volume rendering and multiplanar viewing; locally bundled assets, no additional service.
- FastAPI and Pydantic: backend APIs and validation.
- SQLAlchemy and Alembic: PostgreSQL persistence and migrations.
- PostgreSQL: users, patients, visits, analyses, biomarkers, and job status.
- Local filesystem or S3-compatible storage: MRI files, results, heatmaps, and reports.
- PyTorch, MONAI, and NiBabel: medical-image ML pipeline.
- Docker Compose: PostgreSQL, FastAPI, one Python worker and Next.js; local filesystem storage is selected (D008).
- No cloud deployment target is planned for this project.

## Analysis job lifecycle

1. Frontend uploads an MRI visit.
2. Backend stores the file and creates an analysis job.
3. API returns `202 Accepted` with an analysis ID.
4. Background worker performs preprocessing and inference.
5. Worker stores results, biomarkers, heatmaps, and status.
6. Frontend polls `GET /analysis/{analysis_id}` or receives a WebSocket update.

The implementation uses one local Python worker. PostgreSQL persists the queue, claimed with `FOR UPDATE SKIP LOCKED`. Ordered input snapshots preserve each analysis sequence. On worker restart, interrupted processing jobs become failed with an explicit retry message; queued jobs resume.

JWT sessions use HTTP-only same-site cookies. Next.js proxies `/api/*` to FastAPI. Patient and artifact access is researcher-scoped. Errors hide tracebacks and host paths. Unsafe browser origins are rejected.

## API surface

```
POST /auth/login
POST /auth/logout
GET  /auth/me
GET  /health
GET  /patients
POST /patients
GET  /patients/{id}
POST /patients/{id}/visits
POST /visits/{id}/upload
POST /analysis/{visit_id}
GET  /analysis/{analysis_id}
GET  /patients/{id}/trajectory
GET  /patients/{id}/biomarkers
GET  /patients/{id}/heatmaps
POST /reports/{patient_id}
GET  /reports
GET  /reports/{report_id}/download
GET  /visits/{id}/preview
GET  /visits/{id}/volume
GET  /analysis/{id}/visits/{visit_id}/overlay
GET  /analysis/{id}/visits/{visit_id}/difference-volume
```

The ML layer must not import frontend or API routing code. API services orchestrate work but do not contain model logic.

The two volume endpoints apply existing researcher ownership, return generated filenames and private/no-store responses, and never expose storage keys. Source MRI is not modified. 3D inference artifacts are generated by the existing worker; a request only retrieves already completed files. No DB migration or additional table is required.
