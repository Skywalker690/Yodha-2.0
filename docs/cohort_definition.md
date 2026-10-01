# OASIS baseline forecast cohort

This is a new experiment, not a relabeling of the old forty-person retrospective model.
Use the earliest MR Delay visit per subject, require baseline CDR=0, and select one
original acquisition for that baseline (mpr-1 preferred). All later visits are labels
only. Group is longitudinal study grouping and is excluded from predictors.

The study endpoint is **first observed CDR > 0 after baseline CDR=0**. The original
[OASIS longitudinal publication](https://pubmed.ncbi.nlm.nih.gov/19929323/) describes
conversion this way. This implementation forecasts that recorded research proxy;
it does not establish MCI eligibility, Alzheimer pathology, biological onset or a
new clinical diagnosis. MR Delay is MRI observation timing, not independently supplied
clinical diagnosis dates. Those distinctions are essential when interpreting horizons.

Months are elapsed days / (365.25/12). An event observed on or before a horizon is
positive. A zero observation before the first event at or beyond a horizon establishes
a known negative under the recorded first-conversion endpoint. A gap between a last
zero and a later event spanning the horizon is unknown. Do not backfill earlier
negatives merely because the first positive was later. Reversions do not erase the
first recorded conversion. No conversion observed with insufficient follow-up is
unknown, not event-free. Baseline-relative calendar dates remain null.

Audit of the supplied workbook on 2026-10-02: 150 subjects, 373 visits, **85** earliest
visits with CDR=0, all with matched raw baseline MRI. This is the inspected workbook
count, not an assumption from the publication's aggregate sample.

| Horizon | Recorded events | Known negatives | Unknown |
|---|---:|---:|---:|
| 12 months | 0 | 74 | 11 |
| 24 months | 3 | 55 | 27 |
| 36 months | 8 | 35 | 42 |

Seed 20261002 gives frozen 61/12/12 train/development/test subjects, stratified by
whether conversion was ever observed. This split is separate from the old 40/8/8
split, but participants can overlap earlier examined experiments; it is not an
independent external validation cohort. Never change the split after reviewing scores.

Training at 12 months is impossible with zero events. At 24 months the fixed training
split has one positive and fails the support guard. The 36-month clinical head trains
on 36 known training outcomes (6 events, 30 negatives); 25 unknown training outcomes
are excluded. Development has 5 known outcomes (2/3), test only 2 known negatives and
zero events. ROC-AUC and sensitivity for that test set are unavailable. No validated
default forecasting model can be claimed with this evidence.
