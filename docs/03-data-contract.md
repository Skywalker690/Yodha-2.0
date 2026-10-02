# Data Contract

Longitudinal anatomy has its own optional versioned `anatomy` result and patient
`latestAnatomy`/`completedAnatomy` payloads. It never populates legacy risk/proxy fields.
Native stats/masks, hashes, dictionary, source units, review provenance, continuous
automatic-rating availability and unsupported future horizons are defined in
[17 Longitudinal anatomy](17-longitudinal-anatomy.md). Existing JSON persistence
is sufficient; no migration or second ingestion system is added.

## New baseline-only forecast contract

ML-only patient payloads add `servingPolicy=ml_only`, with historical latest-analysis
fields null. MRI uploads return 202 with `status=stored`, `visitId` and an explicit
processing requirement, not a queued rule-based Analysis. `/health` adds serving
policy and release readiness; legacy POST analysis modes return 409. Forecast defaults
to Clinical + FastSurfer. See [16](16-ml-only-serving.md) for release hashes/gates.

The current FastSurfer study uses separate `baseline.csv`, `manifest.csv`, `labels.csv`,
`split.csv` and `fastsurfer_features.csv` under ignored `data/forecast_v2`.
See [data dictionary](../contracts/data_dictionary.md) and [feature dictionary](fastsurfer_feature_dictionary.md).
`PredictionRequest`/`PredictionResult` are validated in `src/contracts.py`, with exported
JSON schemas under `contracts/`. Every horizon is present and unsupported probabilities
are null. Future records and Group are forbidden predictors. Calendar dates unavailable
in the source remain null. `GET /patients/{id}/forecast` preserves researcher ownership
and returns a separate baseline prediction, reviewed anatomy and QC, without raw paths.
No existing longitudinal analysis contract or database record is relabeled or replaced.

## Dataset and storage

The initial dataset is OASIS-2 longitudinal MRI data. Raw archives remain outside source control. MRI files and generated artifacts live on the local filesystem or in a local S3-compatible adapter such as MinIO. PostgreSQL stores metadata and analysis records.

The new strict MCI-to-Alzheimer forecasting task requires a separate authorized dataset with documented baseline and future diagnoses. ADNI is the acquisition candidate; no ADNI files or cohort have been verified. Do not reuse OASIS Group/CDR as an MCI diagnosis or merge the old split into the new study. Real-data ingestion remains pending account, terms and containment review. See [13 Strict forecasting data](13-strict-forecasting-data.md); the existing MRI/API contract below continues to describe the running OASIS demonstration.

## Supported MRI input

Public uploads accept `.nii` and `.nii.gz`, at most 100 MiB. The supplied OASIS-2 files are paired NIfTI-1 (`Nifti1Pair`, `ni1` magic) with `.nifti.hdr`/`.nifti.img` files. The offline importer converts one acquisition per visit to managed `.nii.gz`, preserving affine and voxel values. Singleton fourth dimensions are reduced to 3D. `mpr-1` is selected when present.

Validate extension, MIME type, readable image structure, real numeric dtype, finite voxels, non-singular affine, and shape. Accept 3D or a singleton 4D volume, at least 8 voxels per spatial axis and at most 32 million voxels. Existing visit files cannot be overwritten; create another visit for a new MRI.

Dataset audit: 150 subjects, 373 visits, 1,368 paired acquisitions; all MRI IDs match the supplied workbook. 56 subjects have at least three visits. Headers and expected image sizes passed. Whole-volume validation is performed on selected imported/uploaded scans. Missing SES (19) and MMSE (2) stay missing. XLSX and CSV demographics are both supported.

## Patient and visit manifest

```csv
patient_id,visit_id,visit_index,days_from_baseline,mri_path,reference_path,cdr,split,output_mode
OAS2_0001,V0,0,0,data/OAS2_0001/V0.nii.gz,,0.5,demo,precomputed
```

Required fields: `patient_id`, `visit_id`, `visit_index`, `days_from_baseline`, and `mri_path`.

Offline manifests may reference `.hdr` files inside the dataset root. Match metadata by MRI ID and order by MR Delay in days. Visit numbers need not be consecutive. A deterministic subject hash assigns full-cohort train/validation/test splits. Prepared demo subjects are not a validation cohort.

## Database entities

- `users`: researcher accounts and password hashes
- `patients`: patient code and timestamps
- `visits`: patient, visit date/month, and MRI object key
- `analyses`: visit, status, score, confidence, model version, and timestamps
- `biomarkers`: analysis metrics
- `heatmaps`: analysis and object-key metadata

Do not introduce additional tables until a documented requirement exists.

## Analysis status

Allowed values are `queued`, `processing`, `completed`, and `failed`.

## Result contract

```python
ProgressionResult(
    patient_id: str,
    visit_ids: list[str],
    risk_scores: list[float],
    biomarkers: dict[str, list[float]],
    selected_visit: str,
    heatmap_url: str | None,
    output_mode: str,
    confidence: float | None,
    caveats: list[str],
    volume_overlays_ready: bool = False,
)
```

Risk scores are normalized to 0–1 internally and displayed as percentages only with an explicit label. Internal Python fields use snake_case; frontend API responses use camelCase.

The implementation also includes `days_from_baseline` and `model_version`. All series lengths match; visits are unique and chronological. Confidence is null for the baseline. Analyses persist ordered input snapshots, progress and the validated result. API responses exclude snapshots, host paths, storage keys and password hashes. Observed visit metadata keeps original source field names (`nWBV`, `eTIV`, `CDR`, `MMSE`, `ASF`). Patients have researcher ownership, optional age/sex, notes and source.

Experimental `trained` output adds an optional structured `prediction` (score, saved validation threshold, classification, checkpoint fingerprint, cohort role and aggregate reused-holdout evidence). It provides one retrospective sequence prediction and an empty `risk_scores`, not a fabricated visit trajectory. Other modes retain their existing aligned score series. Trained input snapshots additionally contain only the eleven source covariates; CDR/Group/identifiers are excluded. Confidence remains null. See [14 Trained inference](14-trained-inference.md).

Report PDF/JSON artifacts persist under generated keys in `storage/reports/`, with researcher ownership checks on list/download. No extra database tables are needed.

## 3D visualization artifacts

Visits with MRI expose an authenticated `volumeUrl`; the URL serves the original managed `.nii`/`.nii.gz` rather than a derived illustration. The frontend bounds downloads to 100 MiB and uses gzip magic bytes to select the NIfTI loader name.

New inference produces `{index}-difference.nii.gz` alongside `{index}-overlay.png` under the existing analysis artifact prefix. Each contains finite float32 absolute normalized intensity differences from baseline, shape 64×64×64, and the selected scan's canonical field-of-view affine. This is not a registered change map. `volumeOverlaysReady` is true only for results with these artifacts; the default is false for old contracts/caches. Precomputed mode checks claimed artifacts before marking a job completed. Existing heatmap rows identify the corresponding artifact, avoiding new database tables. A missing/unavailable artifact returns 404 with an explicit recomputation message.

## Upload rules

- Store objects under generated keys, never user-provided paths.
- Never expose private bucket credentials to the browser.
- Keep raw and derived data clearly separated.
- Never commit raw MRI files, archives, private metadata, or credentials.
