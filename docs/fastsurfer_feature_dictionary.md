# FastSurfer feature dictionary

The supplied root framework is `FastSurfer-dev/FastSurfer-dev`, version **2.6.0-dev0**:
whole-brain VINN segmentation, optional CerebNet/HypVINN/corpus-callosum modules,
surface reconstruction, pretrained-weight download configuration, Docker scripts and
training code. No checkpoint or patient MRI/training-data files were found inside it.
It is reviewed as a dependency reference, not installed into the application's Python
environment or used as an unpinned final experiment.

The runner pins `deepmi/fastsurfer:cuda-v2.5.4`, records the pulled registry digest,
and uses CPU view aggregation for the local 6 GiB GPU. Explicit `device: cpu` is also
supported. Configure CPU/GPU deliberately; there is no silent hardware fallback.
The process has read-only input and no network, and writes to separate subject/scan
directories. PostgreSQL remains the existing host-local database.

The compact feature set is `dkt-compact-seg-v1`. These are candidate definitions
verified against the [v2.5.4 LUT](https://github.com/Deep-MI/FastSurfer/blob/v2.5.4/FastSurferCNN/config/FastSurfer_ColorLUT.tsv)
and [versioned output specification](https://github.com/Deep-MI/FastSurfer/blob/v2.5.4/doc/overview/OUTPUT_FILES.md),
not a claim that real patient processing has completed.

| Feature | Exact SegId / StructName | Side | Source | Unit |
|---|---|---|---|---|
| hippocampus_left_mm3 | 17 / Left-Hippocampus | Left | stats/aseg+DKT.stats | mm³ |
| hippocampus_right_mm3 | 53 / Right-Hippocampus | Right | same | mm³ |
| hippocampus_total_mm3 | Sum of verified left/right | Both | same | mm³ |
| ventricle_left_mm3 | 4 / Left-Lateral-Ventricle | Left | same | mm³ |
| ventricle_right_mm3 | 43 / Right-Lateral-Ventricle | Right | same | mm³ |
| entorhinal_left_mm3 | 1006 / ctx-lh-entorhinal | Left | same | mm³ |
| entorhinal_right_mm3 | 2006 / ctx-rh-entorhinal | Right | same | mm³ |

Atlas: DKT cortical parcellation and FreeSurfer-compatible subcortical labels.
The parser requires exact label ID/name, ColHeaders and mm^3 unit declaration,
positive finite values, matching source/scan/version/digest and unchanged output hashes.
Missing labels are failures, not zero measurements. The predictor uses six compact
features, not the redundant hippocampal total as an additional correlated predictor.

Every processed scan remains `pending_review` until segmentation-on-T1 visual review
is recorded. Changed statistics invalidate review. Only passed cases enter Tier B.
No raw voxel count from the resized CNN cube is treated as a physical anatomical volume.

Cortical thickness, whole-brain volume, hippocampal subfields and FastSurfer ICV are
**not implemented features** in this compact subset. Segmentation volume is not
cortical thickness. Surface reconstruction is configurable but requires a local
FreeSurfer license and actual output/measurement validation before extending this
dictionary. OASIS eTIV is retained as source-attributed estimated ICV; no eTIV*nWBV
substitute or unverified normalization is generated.

Pretraining overlap must be audited for the exact VINN checkpoint. The original
[FastSurfer publication](https://arxiv.org/html/1910.03866v2) included OASIS-2 in its
training; using a frozen segmenter is feasible, but does not establish independent
segmentation or end-to-end forecast validation.
