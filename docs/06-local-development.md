# Local Full-Stack Development

## Prerequisites

- Node.js 22.14+
- Python 3.11
- Git
- Docker Desktop
- Enough disk space for OASIS-2 archives and extracted files
- WebGL2-capable Edge/Chrome with graphics acceleration for interactive 3D (2D remains available without it)

## Local services

- Next.js frontend
- FastAPI backend
- PostgreSQL database
- Local filesystem storage or S3-compatible object storage such as MinIO
- FastAPI background worker or Python ML worker

## Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "monai>=1.4,<2"
```

## Frontend environment

```powershell
cd frontend
npm ci
```

## Run locally

```powershell
python scripts/setup_env.py
# Ensure the host PostgreSQL service is running and the neuropredict database exists.
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed
.\.venv\Scripts\python -m scripts.import_oasis --precompute

# Terminal 1
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - run exactly one worker
.\.venv\Scripts\python -m backend.app.workers.runner

# Terminal 3
cd frontend
npm run dev
```

Open `http://localhost:3000`. FastAPI is available at `http://localhost:8000` and its documentation at `/docs`.

Use `SEED_EMAIL` / `SEED_PASSWORD` from the ignored root `.env`. Setup creates random credentials and preserves existing configuration. Seeding creates the account only once and preserves existing passwords. For local convenience, copy those same values into the ignored `frontend/.env.local` as `NEXT_PUBLIC_LOCAL_LOGIN_EMAIL` and `NEXT_PUBLIC_LOCAL_LOGIN_PASSWORD`; the login form will prefill them. Do not use these frontend defaults outside a local research environment. The supported host-local setup uses the existing PostgreSQL service on `127.0.0.1:5432`; create the `neuropredict` database and role before running migrations. Local filesystem storage was selected, so there is no MinIO dependency. All published service ports are restricted to loopback.

For the complete packaged stack, run from the root:

```powershell
python scripts/setup_env.py
docker compose up -d --build
docker compose exec backend python -m scripts.import_oasis --precompute
docker compose exec backend python -m scripts.smoke_3d --prepare
```

Docker mounts the raw dataset read-only. PostgreSQL persists in `postgres_data`; MRI/results/reports persist in `storage/`, manifests/audits in `data/`. Source data, `.env`, generated artifacts and dependencies are excluded from Git and Docker build contexts. Stop container API/worker/frontend before using host services on the same ports and storage. Do not run two workers against this MVP queue.

Offline manifests contain absolute paths for the current runtime. Default import regenerates them for the host or container; do not reuse a Windows-path manifest inside Linux with `--manifest` unchanged. The frontend lockfile and project .npmrc are required for matching clean installs. Backend and worker share the same local Docker image.

## Data workflow

1. Download both OASIS-2 raw archives.
2. Extract them outside Git-tracked source directories where possible.
3. Inspect the extracted structure and metadata.
4. Select 3–5 subjects with at least three visits.
5. Create a manifest under `data/manifests/`.
6. Upload or register files in local object storage.
7. Generate cached features and demo outputs.
8. Verify each patient through the web UI.

## Suggested scripts

```powershell
python -m scripts.inspect_oasis --root dataset --output data/audit.json
python -m scripts.create_manifest --input dataset/oasis_longitudinal_demographics-8d83e569fa2e2d30.xlsx --output data/manifests/demo.csv
python -m scripts.preprocess --manifest data/manifests/demo.csv
python -m scripts.generate_demo_data --manifest data/manifests/demo.csv
```

The importer reads XLSX or CSV metadata and uses MRI ID/MR Delay for matching and chronology. Public uploads use `.nii`/`.nii.gz`; offline import converts paired NIfTI automatically. Default import prepares five subjects, three real visits each, spread across the eligible cohort. It is idempotent. Precomputed outputs are actual offline baseline calculations, not invented risk values.

`python -m scripts.import_oasis --all` performs explicit offline full-cohort import. Add `--precompute` to process all subjects; this takes longer and is not needed for the one-minute demo. Subject-level split assignment is deterministic and is not an evaluation claim.

## Verification

Offline MRI/demographic model retraining uses the original `data/training/subject_split.csv` and runs outside the HTTP API:

```powershell
.\.venv\Scripts\python -m scripts.train_multimodal_model --epochs 40 --min-epochs 15 --patience 8 --batch-size 4 --threads 4
```

This creates a fresh run directory under ignored `data/training_multimodal/runs/`, reuses a source-fingerprinted MRI cache, and preserves older experiments. The saved split must exist; the runner rejects mismatched or incomplete subject/visit assignments. See [12 Multimodal training](12-multimodal-training.md).

```powershell
.\.venv\Scripts\python -m ruff check backend ml scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m alembic check
.\.venv\Scripts\python -m scripts.create_test_fixture
cd frontend
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Browser tests require the running app, prepared cohort, synthetic fixture and Microsoft Edge. They read local credentials from `.env` without printing them, create visibly prefixed E2E research cases, and test actual report downloads. Unit tests use isolated temporary storage and an in-memory database.

The 3D browser checks require prepared volumetric artifacts. Run `docker compose exec backend python -m scripts.smoke_3d --prepare` once after updating an existing install; it queues normal asynchronous inference only for OASIS cases missing 3D artifacts. Existing results and raw data are retained. Later runs without `--prepare` are read-only geometry/API checks. From the host, use `.\.venv\Scripts\python -m scripts.smoke_3d --prepare` instead. The package is pinned to NiiVue 0.69.0 in the frontend lockfile.

## Troubleshooting

- Frontend cannot reach API: verify backend URL and CORS.
- API cannot connect to PostgreSQL: verify Compose services and migrations.
- Upload fails: verify local storage permissions or adapter settings.
- NIfTI fails: verify extension, pairing, shape, and affine.
- Inference is slow: use precomputed demo mode.
- Heatmap unavailable: show the original MRI with an explicit explanation-unavailable state.
- 3D unavailable: enable WebGL2/browser graphics acceleration or keep using the 2D viewer. Pause 3D releases its resources; Retry recreates a fresh canvas. Old cached results need Local inference for 3D differences.

- Worker offline: start the single worker. Restarted processing jobs become failed with an explicit retry message; queued jobs resume.
- Cache unavailable: run Local inference once. Precomputed mode never silently falls back to demo.
- Stop without deleting data: `docker compose stop`; restart with `docker compose up -d`. Avoid `down -v` unless intentionally deleting the local database.
- Check `docker compose ps` and `docker compose logs backend worker frontend` for service diagnostics.

## One-minute demo

Sign in, open a prepared three-visit OASIS patient, select the latest visit, choose Precomputed and Analyze MRI, review the trajectory/metrics, toggle the difference overlay, navigate visits, then Generate research report and Download PDF. The persistent Research Prototype / Not a medical diagnosis labels and output provenance remain visible.
