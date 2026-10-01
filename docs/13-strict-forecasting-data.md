# Strict MCI-to-Alzheimer forecasting data

## Objective and current state

On 2026-10-01 the user selected strict forecasting under the supplied `NeuroPredict_AI_Complete_PRD (1).docx`, rather than adapting OASIS-2 to a different conversion task. Eligible inputs must come from a documented MCI baseline. The outcome is a later study-defined clinical Alzheimer dementia diagnosis, not an MRI class, a CDR increase alone or biomarker-confirmed pathology unless that is separately documented.

The old 40-person OASIS training run remains a retrospective experiment. Preserve its raw scans, database records, assignments and checkpoints. It cannot supply the required documented MCI cohort. The new participant count and split must be determined from suitable data, not forced to 40 or inherited from OASIS.

ADNI is the primary acquisition candidate, **not an acquired or verified training dataset**. No strict forecasting model has been trained. A filename search of the project's `dataset/`, `data/` and the user's Downloads directory found no ADNI/DXSUM/ROSTER/data-dictionary-named files; this is not an inventory of every possible location or proof that the user lacks an account.

## Access and containment first

The researcher must have approved ADNI access through [LONI IDA](https://ida.loni.usc.edu/collaboration/access/appApply.jsp?project=ADNI). The application needs truthful affiliation and research-purpose information. The researcher, not the agent, reviews and accepts the agreement. ADNI describes a typical review period of approximately two weeks, not guaranteed immediate approval. See the [official access instructions](https://adni.loni.usc.edu/data-samples/adni-data/).

The [current agreement and Appendix A](https://ida.loni.usc.edu/collaboration/access/appApply.jsp?project=ADNI) restrict participant-level redistribution and third-party AI processing without containment guarantees. A local application does not by itself establish that data-bearing outputs returned to a remote assistant are compliant. Do not attach clinical CSVs, images, individual predictions or subject records here. Account approval also does not establish approval for this assistant's processing environment. Review both requirements before any real-data tools run.

Until that review is complete, work may use public documentation and fully synthetic fixtures only. Store real data in an access-controlled location outside the checkout, excluded from Git, synchronization and logs as required by the approved workflow. Do not change the existing OASIS locations or delete data to create space. At the check on 2026-10-01, C: had approximately 8.4 GiB free; an MRI storage plan remains necessary.

## Acquisition order after approval

1. Download the release-specific data dictionary, methods/procedures documentation and diagnostic history from IDA. Also obtain the enrollment/identifier mapping, baseline demographics/cognition and the matching MRI inventory/QC information. Preserve original files, download dates and SHA-256 hashes in controlled local provenance records.
2. Reconcile diagnosis history with a merged convenience table such as ADNIMERGE if available. Do not assume one numeric diagnosis mapping applies to every phase. The [ADNI FAQ](https://adni.loni.usc.edu/help-faqs/faqs/) distinguishes ADNI1 `DXCURREN`, GO/2 `DXCHANGE` and ADNI3 `DIAGNOSIS`, and identifies Diagnostic Summary and ROSTER as the relevant sources. Verify the downloaded dictionary and Alzheimer-specific meaning before implementing mappings, especially for newer dementia codes.
3. Audit eligibility and outcomes before downloading large MRI collections. Use actual assessment dates and phase-aware visit identifiers. Record stable identifiers for rollover participants to prevent cross-phase leakage. Exclude baseline Alzheimer dementia and ambiguous diagnoses; do not infer MCI from a score. Trace at least three cases locally from source to cohort without returning individual data to this chat.
4. Select baseline T1 MRI with a documented clinical/MRI date rule and QC/acquisition tie-breaker. An input must have been available at the prediction cutoff. Reject ambiguous or post-cutoff matches. Download a bounded QC sample first; determine compressed, extracted, tensor/cache and checkpoint storage needs before bulk download.
5. Use baseline-available, QC-supported anatomical summaries if present. Verify region definitions, physical units and processing version. Measurements from longitudinal processing that used future scans are not baseline-only features. Missing hippocampal/cortical/ventricular values remain unavailable rather than inferred from attention maps.

## Training-readiness gates

| Gate | Required evidence before training |
|---|---|
| Permission | Approved account, accepted intended-use terms and approved contained processing/storage workflow |
| Baseline | One dated, documented MCI baseline per unique participant; phase-specific diagnosis mappings reviewed |
| Outcome | Future clinical Alzheimer dementia diagnosis supported by source definitions; uncertain or alternative dementia causes handled explicitly |
| Timing | Actual assessment dates; documented event observation interval and last event-free follow-up |
| Horizons | Positive, negative and unknown counts at 12/24/36 months; gaps spanning a horizon are not silently labelled event-free |
| Leakage | Unique subjects and scans; no rollover subject across splits; no post-baseline predictors or future-derived preprocessing |
| Support | Both outcome classes and adequate event/nonevent counts in the proposed training and evaluation design at each supported horizon |
| Inputs | Baseline clinical/MRI alignment, missingness, MRI QC and source-unit verification |
| Reproduction | Frozen cohort/split, feature order, source hashes, preprocessing/configuration and software versions |

The first observed Alzheimer diagnosis dates detection, not exact biological onset. A horizon preceding that observation may remain unknown if the previous event-free assessment does not cover it. Write and test the interval/ascertainment policy before constructing labels. Insufficient follow-up is never converted to a negative.

Having both classes is necessary but not evidence of adequate precision. Report event counts and uncertainty, and specify the evaluation design before inspecting final-test performance. Suppress unsupported horizons. Do not oversample before splitting, use test data for model selection or promise a particular accuracy before evaluation.

After the gates pass, train the regularized clinical baseline and a matched clinical-plus-verified-MRI-summary baseline before adding a compact 3D branch. Keep future visits solely for labels in the baseline task. Fit preprocessing on training subjects only; select settings/calibration using development data; keep final-test subjects untouched. The dashboard must distinguish unavailable, illustrative and actually evaluated outputs.

## Research-purpose draft

The following is a draft purpose statement, not a submitted application or a claim of affiliation:

> We propose a local research prototype for forecasting study-defined progression from documented baseline mild cognitive impairment to a later clinical Alzheimer dementia diagnosis at 12, 24 and 36 months. We will first audit diagnosis definitions, follow-up coverage and event counts, then evaluate regularized baseline clinical models and the incremental value of verified structural MRI measurements. MRI representation learning will be considered only after input quality and feasibility checks. We will use participant-level splits, baseline-available predictors and explicit handling of unknown outcomes. The project is not a diagnostic device. Data access, storage, processing, publication and acknowledgement will follow the approved ADNI agreement and applicable institutional requirements.

The researcher must review this statement for accuracy, supply their own affiliation/team details, and confirm the approved environment. No account registration, application, agreement acceptance, restricted-data download or real-data audit has been performed by this acquisition-planning step.

## Verification of this planning change

On 2026-10-01, the existing Python suite passed with 33 tests and one upstream Starlette deprecation warning. Ruff passed. `git diff --check` and local documentation-link checks passed. These verify the existing code and the documentation change only, not strict forecasting eligibility, diagnosis mappings, event counts, calibration or model performance. No runtime code, application model, existing raw MRI or database record was changed by this planning step. The official ADNI access-information page was queued to open in the application's browser panel; that is not access approval or a dataset download.
