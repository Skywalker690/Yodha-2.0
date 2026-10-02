# Documentation Index

This folder is the working specification for the full-stack Alzhio platform. Read the root AGENTS.md and this file before implementation.

| Document | Purpose |
|---|---|
| [01 Product requirements](01-product-requirements.md) | Product goal, users, scope, and acceptance criteria |
| [02 Architecture](02-architecture.md) | Full-stack system design and service boundaries |
| [03 Data contract](03-data-contract.md) | MRI files, metadata, database entities, and API results |
| [04 ML plan](04-ml-plan.md) | Modeling, inference jobs, explainability, and limitations |
| [05 UI specification](05-ui-spec.md) | Next.js screens and interaction behavior |
| [06 Local development](06-local-development.md) | Frontend, backend, database, storage, and commands |
| [07 Testing and validation](07-testing-validation.md) | Automated, manual, and scientific checks |
| [08 Roadmap](08-roadmap.md) | Prioritized implementation sequence |
| [09 Decision log](09-decision-log.md) | Decisions, assumptions, and unresolved questions |
| [10 Implementation status](10-implementation-status.md) | Delivered MVP, verification evidence and explicit research limitations |
| [11 3D visualization](11-3d-visualization.md) | Library research, interactive MRI workspace and validation |
| [12 Multimodal training](12-multimodal-training.md) | Saved subject split, covariates, audited retraining commands and evaluation limits |
| [13 OASIS-2 data and forecast scope](13-oasis2-data-and-forecast-scope.md) | The supplied OASIS-2 MRI, demographics, observed CDR outcomes and OASIS-only evaluation limits |
| [14 Trained inference](14-trained-inference.md) | Experimental checkpoint integration, frozen cohort, input eligibility and honest prediction limits |
| [15 FastSurfer architecture](15-fastsurfer-architecture.md) | New baseline-only OASIS forecast study, compact anatomy layer and single prediction adapter |
| [16 ML-only serving](16-ml-only-serving.md) | Strict combined-model serving, actual processing/training workflow, promotion gates and Docker repair |
| [17 Longitudinal anatomy](17-longitudinal-anatomy.md) | Native masks, review-bound measurements, automatic scoring and scientific completion boundary |
| [18 Anatomy forecasting lifecycle](18-anatomy-forecast-lifecycle.md) | Implemented registration/training/release, asynchronous forecasts, API, real runtime evidence and remaining gates |
| [19 Fixed-reference anatomy run](19-fixed-reference-anatomy-run.md) | Supplied fixed nWBV age constants, exact new inputs, real GPU candidate, evaluation and remaining cohort execution |
| [20 Training-reference anatomy run](20-training-reference-anatomy-run.md) | Current training-only reference without minimum ten, GPU runs, evaluation and remaining execution |
| [21 Clinical assistant](21-clinical-assistant.md) | Gemini hackathon chat, filtered patient context, optional web references, configuration and checks |
| [Cohort definition](cohort_definition.md) | Observed CDR conversion, horizon censoring and inspected event counts |
| [FastSurfer dictionary](fastsurfer_feature_dictionary.md) | Exact versioned labels, physical units and visual-review gate |
| [Forecast evaluation](evaluation.md) | Matched comparisons, unsupported metrics and monotonic risk semantics |
| [Completion blockers](blockers.md) | Runtime, outcome support and uncompleted real-data work |

The supplied PPT defines the product concept. The current architecture plan defines the implementation direction. If they conflict, preserve the deck's central longitudinal-analysis idea and record the decision before coding.
