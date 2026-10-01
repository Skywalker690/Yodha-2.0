# Full-Stack Implementation Roadmap

All six MVP phases below are implemented and locally verified as of 2026-10-01. See [10 Implementation status](10-implementation-status.md) for requirement mapping, test evidence and the boundary between the completed product and subsequent trained-model research.

## Phase 1: Foundation

- Create Next.js frontend and FastAPI backend.
- Add Docker Compose for PostgreSQL and local object storage.
- Add environment configuration and CORS.
- Add database models and Alembic migrations.
- Add synthetic fixtures for tests.

## Phase 2: Authentication and records

- Implement JWT login.
- Implement patient list and creation.
- Implement visit creation.
- Add typed API client and protected frontend routes.

## Phase 3: Data and uploads

- Inspect extracted OASIS-2 files.
- Create a demo manifest.
- Add local object storage adapter.
- Implement MRI upload and validation.
- Generate thumbnails, cached features, and safe metadata.

## Phase 4: Dashboard

- Build overview page.
- Build patient page.
- Add MRI timeline, risk chart, biomarker cards, and analysis workspace.
- Add visible disclaimers and output provenance.

## Phase 5: ML and jobs

- Add preprocessing.
- Add encoder and temporal-model interfaces.
- Add baseline inference.
- Add explainability interface.
- Add asynchronous analysis lifecycle.
- Persist results and heatmap objects.

## Phase 6: Reports and local packaging

- Generate constrained research reports.
- Add report download.
- Build frontend and backend Docker images.
- Verify the complete stack with Docker Compose.
- Document the local demo and recovery workflow.

If time is limited, prioritize the login-to-patient-to-analysis flow over model complexity. Deployment comes after the local product flow works.

## Phase 7: User-requested 3D extension (implemented 2026-10-01)

- Compare MRI rendering libraries using primary documentation and record D014.
- Add authenticated source/difference NIfTI endpoints using existing ownership/storage.
- Integrate NiiVue volume rendering, slices, cutaways, comparison and annotated export.
- Preserve the 2D fallback and explicit research/provenance limits.
- Verify geometry, permissions, browser interaction, resource cleanup and original workflows.

See [11 3D visualization](11-3d-visualization.md) and [10 Implementation status](10-implementation-status.md) for research and verification evidence.
