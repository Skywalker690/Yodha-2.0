# Baseline forecasting architecture with FastSurfer

The subsequent [ML-only serving policy](16-ml-only-serving.md) supersedes selectable
serving modes below. The manual Tier A/B commands remain research/processing utilities;
models need explicit promotion before serving. Docker engine has been repaired and
the real pilot resumed; consult local pipeline status for actual progress.

The user-supplied FastSurfer Rewired v2 PRD is implemented as a separate baseline-only
study layer within the existing repository. It does not destroy the full-stack product,
database, source MRIs or historical 40/8/8 models. Current real-data completion limits
are authoritative in [blockers](blockers.md).

```text
OASIS source workbook ──> earliest CDR-zero baseline ──> clinical predictors ─┐
                                                                         │
Same baseline native T1 ──> pinned FastSurfer ──> reviewed mm³ features ────┤
                                                                         ▼
Later clinical observations ──> 0/1/unknown horizon labels       frozen subject split
                                                                         │
                                      train-only preprocessing + logistic heads
                                                                         │
                              JSON model + hashes + support + evaluation evidence
                                                                         ▼
                  src.risk.predict.predict ──> Streamlit / owned FastAPI / Next.js
```

FastSurfer is an isolated offline processor, not an always-running extra microservice.
No processing/training runs inside browser/HTTP requests. CPU tabular prediction reads
small saved JSON parameters; it is independent of optional PyTorch and sklearn imports.
MRI segmentation/feature batches are explicit durable CLI jobs. Existing analysis
jobs continue using the PostgreSQL worker and prior contracts. No database migration.

## Repository responsibilities

- `src/data/`: source validation, baseline assembly, censoring-aware labels, frozen split,
  physical MRI QC/conversion.
- `src/fastsurfer/`: pinned Docker CPU/CUDA runner, per-scan provenance, exact statistics
  parser, compact DKT map, source matching and explicit visual-review gate.
- `src/risk/`: training-only preprocessing, regularized reference/primary logistic models,
  immutable JSON artifacts, matched evaluation, safe predictor adapter and explanations.
- `src/mri/model.py`: optional tested 128³ fusion interface and masked loss, not a trained model.
- `src/app/`: localhost Streamlit research workspace, no participant processing on external services.
- `backend/app/services/forecast.py`: owned-case bridge; returns only baseline, reviewed
  features and prediction, never MRI/storage paths. `GET /patients/{id}/forecast` is read-only.
- `frontend/components/baseline-forecast.tsx`: separate baseline target/provenance/null cards.
- `configs/`, `contracts/`: versioned defaults, typed schemas, feature/data definitions.
- `data/forecast_v2`, `storage/fastsurfer_v2`, `artifacts/forecast_v2`: ignored study artifacts.

The downloaded dev repository was reviewed, including README, input requirements,
VINN architecture/config, LUT, statistics column/unit writer, output specification,
dependencies and container interface. It is 2.6.0-dev0; experiments instead pin the
official 2.5.4 container and validate that version's outputs. Vendor code is unchanged.

## Reproducible commands

From repository root:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-base.txt
.\.venv\Scripts\python -m src.data.validate --config configs/paths.example.yaml
.\.venv\Scripts\python -m src.data.build_cohort --config configs/experiment.yaml
.\.venv\Scripts\python -m src.data.labels --config configs/experiment.yaml
.\.venv\Scripts\python -m src.data.split --config configs/experiment.yaml
.\.venv\Scripts\python -m src.risk.train --config configs/experiment.yaml --model clinical
.\.venv\Scripts\python -m src.risk.evaluate --config configs/experiment.yaml --model clinical
docker pull deepmi/fastsurfer:cuda-v2.5.4
.\.venv\Scripts\python -m src.fastsurfer.runner --config configs/fastsurfer.yaml --pilot 5
.\.venv\Scripts\python -m src.fastsurfer.parse_stats --config configs/fastsurfer.yaml
.\.venv\Scripts\python -m src.fastsurfer.qc --config configs/fastsurfer.yaml
# After inspecting each real segmentation over its T1, use --approve-scan <scan_id> --reviewer <name>.
# Then rebuild features. Change artifact_dir to a fresh run before matched model training.
.\.venv\Scripts\python -m src.risk.train --config configs/experiment.yaml --model clinical --matched
.\.venv\Scripts\python -m src.risk.train --config configs/experiment.yaml --model clinical_fastsurfer
.\.venv\Scripts\python -m src.risk.evaluate --config configs/experiment.yaml --model clinical --matched
.\.venv\Scripts\python -m src.risk.evaluate --config configs/experiment.yaml --model clinical_fastsurfer
.\.venv\Scripts\python -m streamlit run src/app/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Models refuse overwrite; use a fresh versioned artifact directory for retraining. The
current application bridge reads the default forecast directory; after changing the
experiment directory, promote only reviewed compatible artifacts deliberately.
The runner never pulls an image implicitly. Missing engine, image, digest, data, required
labels or visual QC produces explicit failure/unavailability. Rerunning a completed
segmentation requires a new output directory rather than overwriting it.

Hardware observed: RTX 3050 Laptop GPU 6 GiB, approximately 15.3 GiB RAM, 41.5 GiB free
disk at the initial check. Use one scan at a time and CPU view aggregation. Actual runtime,
peak memory and output sizes have not been measured because Docker readiness failed.
FastSurfer surface reconstruction is disabled by default; if enabled, supply a legitimate
local FreeSurfer license, validate actual surface results and extend the feature contract.

See [cohort](cohort_definition.md), [feature dictionary](fastsurfer_feature_dictionary.md),
[preprocessing](preprocessing.md), [evaluation](evaluation.md), [demo](demo_script.md).
