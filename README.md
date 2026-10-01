# NeuroPredict AI

NeuroPredict AI is a full-stack clinical research platform for analyzing longitudinal brain MRI scans and presenting structural-change metrics, progression-risk estimates, MRI comparisons, explainability visualizations, and research reports.

The project is based on the supplied project deck:

`NeuroPredict AI_ Predicting Alzheimer's Progression from Longitudinal Brain MRI-2.pptx`

This is a research prototype and clinical decision-support demonstration. It is not a medical diagnostic system and must not present predictions as clinical diagnoses.

## Documentation-first rule

Before making any change or starting any build task, read [`AGENTS.md`](AGENTS.md) and the relevant documents in [`docs/`](docs/00-index.md). Every implementation decision must follow those documents. If a new technical or product decision is required, record it in [`docs/09-decision-log.md`](docs/09-decision-log.md).

## MVP scope

The MVP uses a Next.js and TypeScript frontend, a FastAPI backend, PostgreSQL metadata storage, local object storage, and a Python ML pipeline using PyTorch and MONAI. It supports researcher login, patient creation, longitudinal MRI visits, asynchronous analysis jobs, progression trajectories, biomarkers, heatmaps, and research report generation.

The application runs locally. Docker is the standard local packaging method. There is no AWS deployment target in the current plan.

The documented MVP is implemented in `frontend/`, `backend/`, and `ml/`. The workspace now initially selects experimental Trained mode, using the audited 40-subject CNN/demographic-MLP/LSTM checkpoint for one retrospective CDR-increase sequence score. Its poor reused-holdout performance is disclosed; this is not future Alzheimer forecasting or a calibrated disease probability. Legacy feature-delta/demo/precomputed modes and existing results remain available. See [trained-model integration](docs/14-trained-inference.md).

The MRI workspace also supports actual-voxel 3D rendering, orthogonal slices, cutaways, linked baseline comparisons and volumetric difference proxies with NiiVue. See [3D library research and scope](docs/11-3d-visualization.md). These are research displays, not segmented or registered anatomy.

## Start the application

```powershell
python scripts/setup_env.py
docker compose up -d --build
docker compose exec backend python -m scripts.import_oasis --precompute
docker compose exec backend python -m scripts.smoke_3d --prepare
```

Open http://localhost:3000. Local login credentials are `SEED_EMAIL` and `SEED_PASSWORD` in the ignored root `.env` file. Keep both dataset parts and the demographics workbook in `dataset/`; the importer prepares five subjects with three real visits each. Re-running setup/import preserves existing records.

See [`docs/06-local-development.md`](docs/06-local-development.md) for development, data import, tests and recovery. See [`docs/10-implementation-status.md`](docs/10-implementation-status.md) for verification evidence and limitations.

## Safety and honesty requirements

- Clearly label illustrative, cached, and model-generated results.
- Never invent evaluation metrics or imply clinical validation.
- Keep the research-prototype disclaimer visible.
- Preserve dataset terms, attribution, and access restrictions.
- Do not commit raw MRI archives, credentials, secrets, or private patient information.
