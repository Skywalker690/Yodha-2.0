# Forecast evaluation and model selection

Report known events, known negatives and unknowns by subject split and horizon. Never
impute labels. Default workflow gates require at least 5 known training examples per
class and 2 development examples per class; these conservative execution guards are
not a power calculation or proof of adequate validation sample size.

ROC-AUC, average precision and balanced accuracy require both classes; Brier and
calibration bins are computed when known outcomes exist. Sensitivity/specificity remain
null when their denominators are absent. No patient bootstrap interval is claimed for
the current tiny/single-class test samples. Calibration is explicitly `uncalibrated`.

Independent head risks are postprocessed with cumulative maximum over available
horizons. Null horizons stay null. This deterministic rule uses no outcome labels,
does not fit on test subjects, and is not probability calibration. Development-only
threshold selection uses the same adjusted outputs; evaluation uses the frozen rule.
Feature explanations describe the raw logistic standardized logit contributions,
not causal effects or an explanation of the monotonic adjustment.

For MRI added-value comparison, run clinical `--matched` and `clinical_fastsurfer` on
the same reviewed subject/scan table and frozen split. Both save cohort membership and
source hashes; evaluate refuses changed source tables or different memberships. Full
clinical-cohort scores must not be called an improvement over a smaller MRI cohort.

Actual current clinical run: only 36 months supported for fitting, six training events,
two development events, zero known test events. Development ROC-AUC=1 on only five
known subjects is **not** generalization evidence. Test ROC-AUC/sensitivity remain null.
No validated strongest-model default is frozen, and no real Tier B comparison exists.
