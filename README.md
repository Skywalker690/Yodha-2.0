# NeuroPredict AI

## Longitudinal anatomy extension

The existing workspace now has native regional masks/measurements, explicit visual
QC, score-availability/history cards and separate anatomy reports. All five baseline
pilot outputs are verified but await visual QC. Future-brain forecasting is NOT
complete: no evaluated spatial model or real predicted NIfTI/GIFTI release exists.
Setup, delivered boundaries and remaining acceptance criteria are in
[Longitudinal anatomy](docs/17-longitudinal-anatomy.md).

## Current default: ML-only serving

The app now serves only a promoted Clinical + FastSurfer release, with no demo,
feature-delta, cached-baseline or historical neural fallback. Existing MRI/data/models
are preserved. Prediction is blocked until real anatomy, human QC and model/evaluation
release gates pass. Docker's socket runtime was repaired with user approval and the
five-scan processing pilot resumed. See [run/resume instructions](docs/16-ml-only-serving.md).
This is stricter research serving, not clinical production readiness.

## Baseline forecasting with FastSurfer

The new FastSurfer Rewired v2 study is implemented in `src/`, with baseline-only
clinical/compact anatomy models, censored 12/24/36-month labels, one prediction adapter,
a local Streamlit dashboard and a separate forecast panel in the existing app.
Read [current architecture](docs/15-fastsurfer-architecture.md) and [completion blockers](docs/blockers.md)
before running. Real FastSurfer processing/Tier B training are not completed. Docker
readiness now passes after repair, but the source's outcomes cannot support all horizons.
Only an experimental 36-month clinical head has been fitted; it has no known positive
test outcomes and is not an independently validated Alzheimer forecast.

```powershell
.\.venv\Scripts\python -m pip install -r requirements-base.txt
.\.venv\Scripts\python -m streamlit run src/app/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

The existing local database, MRI uploads, accounts and historical 40-subject checkpoint
are preserved. The downloaded FastSurfer source is a dependency reference, not another
patient dataset. Forecast artifacts/data remain outside Git.

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
