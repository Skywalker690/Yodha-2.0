"""Offline volume forecast comparisons. NOT a promoted spatial/clinical predictor."""

from dataclasses import dataclass

import numpy as np

from ml.anatomy.contracts import AnatomyVisit

DEMOGRAPHICS = ("Age", "EDUC", "SES", "MMSE", "eTIV", "nWBV", "ASF")
SCORES = ("mta_left", "mta_right", "posterior_atrophy")


def history_features(
    history: list[AnatomyVisit], interval_days: int, with_scores: bool
) -> tuple[np.ndarray, list[str]]:
    if not 2 <= len(history) <= 5 or interval_days <= 0:
        raise ValueError("Two-to-five earlier visits and positive future interval required")
    if any(v.qc != "passed" for v in history):
        raise ValueError("Reviewed anatomy required")
    if any(b.days_from_baseline <= a.days_from_baseline for a, b in zip(history, history[1:])):
        raise ValueError("Strict visit ordering required")
    regions = sorted(history[0].volumes_mm3)
    if any(sorted(v.volumes_mm3) != regions for v in history):
        raise ValueError("Inconsistent regional dictionary")
    years = np.array([v.days_from_baseline - history[-1].days_from_baseline for v in history]) / 365.25
    values, names = (
        [interval_days / 365.25, -years[0], len(history)],
        ["interval_years", "history_years", "visit_count"],
    )
    for region in regions:
        observed = np.array([v.volumes_mm3[region] for v in history])
        slope = float(np.polyfit(years, observed, 1)[0])
        values.extend([observed[-1], slope])
        names.extend([region, region + "_slope_per_year"])
    for name in DEMOGRAPHICS:
        value = history[-1].observed_metadata.get(name)
        values.append(np.nan if value is None else float(value))
        names.append(name)
    sex = history[-1].observed_metadata.get("M/F")
    values.append(0.0 if sex == "F" else 1.0 if sex == "M" else np.nan)
    names.append("sex_F0_M1")
    hand = history[-1].observed_metadata.get("Hand")
    values.append(0.0 if hand == "R" else 1.0 if hand == "L" else np.nan)
    names.append("hand_R0_L1")
    if with_scores:
        if any(v.ratings.status != "ok" for v in history):
            raise ValueError("Matched score-conditioned comparison requires verified automatic estimates")
        for name in SCORES:
            scores = np.array([getattr(v.ratings, name) for v in history], dtype=float)
            values.extend([scores[-1], float(np.polyfit(years, scores, 1)[0])])
            names.extend([name, name + "_slope_per_year"])
    return np.asarray(values, dtype=float), names


def simple_baselines(history: list[AnatomyVisit], interval_days: int) -> dict[str, dict[str, float]]:
    history_features(history, interval_days, False)
    years = np.array([v.days_from_baseline - history[-1].days_from_baseline for v in history]) / 365.25
    no_change = dict(history[-1].volumes_mm3)
    trend = {
        name: float(
            last + np.polyfit(years, [v.volumes_mm3[name] for v in history], 1)[0] * interval_days / 365.25
        )
        for name, last in no_change.items()
    }
    if any(v <= 0 for v in trend.values()):
        raise ValueError("Linear extrapolation produced unsupported nonpositive anatomy; do not clip")
    return {"no_change": no_change, "individual_linear_trend": trend}


@dataclass
class StructuralExample:
    subject_id: str
    history: list[AnatomyVisit]
    target: AnatomyVisit

    @property
    def interval_days(self) -> int:
        gap = self.target.days_from_baseline - self.history[-1].days_from_baseline
        if (
            gap <= 0
            or self.target.visit_id in {v.visit_id for v in self.history}
            or self.target.qc != "passed"
        ):
            raise ValueError("Target must be hidden, reviewed and strictly later than all inputs")
        return gap


class RegularizedMixedEffects:
    """Penalized least squares fixed effects + subject random rate/intercept effects.

    Predicts mm3/year changes, not geometry. New subjects have zero cohort random
    effect until their observed prior transitions support posterior adaptation.
    Penalties must be selected on development subjects, never test labels.
    """

    def __init__(self, fixed_penalty: float = 10.0, random_penalty: float = 10.0, with_scores: bool = False):
        if fixed_penalty <= 0 or random_penalty <= 0:
            raise ValueError("Positive regularization required")
        self.fixed_penalty, self.random_penalty, self.with_scores = fixed_penalty, random_penalty, with_scores

    def fit(self, examples: list[StructuralExample], split: dict[str, str]) -> "RegularizedMixedEffects":
        if not examples or any(split.get(e.subject_id) != "train" for e in examples):
            raise ValueError("Fit accepts frozen training subjects only")
        self.subjects = sorted({e.subject_id for e in examples})
        if len(self.subjects) < 2:
            raise ValueError("Cohort patterns require multiple training subjects")
        self.regions = sorted(examples[0].history[-1].volumes_mm3)
        rows, targets = [], []
        for example in examples:
            interval = example.interval_days
            row, names = history_features(example.history, interval, self.with_scores)
            if sorted(example.target.volumes_mm3) != self.regions:
                raise ValueError("Target regional dictionary changed")
            rows.append(row)
            targets.append(
                [
                    (example.target.volumes_mm3[k] - example.history[-1].volumes_mm3[k]) / (interval / 365.25)
                    for k in self.regions
                ]
            )
        self.feature_names = names
        raw = np.asarray(rows)
        # Imputation/scaling use only the accepted training subjects.
        self.median = np.array([np.median(c[np.isfinite(c)]) if np.isfinite(c).any() else 0 for c in raw.T])
        imputed = np.where(np.isfinite(raw), raw, self.median)
        self.scale = np.std(imputed, axis=0)
        self.scale[self.scale < 1e-8] = 1
        x = np.column_stack([np.ones(len(rows)), (imputed - self.median) / self.scale, ~np.isfinite(raw)])
        z = np.zeros((len(rows), len(self.subjects)))
        for index, example in enumerate(examples):
            z[index, self.subjects.index(example.subject_id)] = 1
        design = np.column_stack([x, z])
        penalties = np.array(
            [1e-8, *([self.fixed_penalty] * (x.shape[1] - 1)), *([self.random_penalty] * z.shape[1])]
        )
        self.coefficients = np.linalg.solve(
            design.T @ design + np.diag(penalties), design.T @ np.asarray(targets)
        )
        self.fixed_width = x.shape[1]
        return self

    def predict(self, subject_id: str, history: list[AnatomyVisit], interval_days: int) -> dict[str, float]:
        row, names = history_features(history, interval_days, self.with_scores)
        if names != self.feature_names or sorted(history[-1].volumes_mm3) != self.regions:
            raise ValueError("Prediction feature schema changed")
        clean = np.where(np.isfinite(row), row, self.median)
        fixed = np.r_[1, (clean - self.median) / self.scale, ~np.isfinite(row)]
        rate = fixed @ self.coefficients[: self.fixed_width]
        if subject_id in self.subjects:
            rate += self.coefficients[self.fixed_width + self.subjects.index(subject_id)]
        elif len(history) >= 3:
            residuals = []
            for index in range(2, len(history)):
                gap = history[index].days_from_baseline - history[index - 1].days_from_baseline
                prior, _ = history_features(history[:index], gap, self.with_scores)
                clean_prior = np.where(np.isfinite(prior), prior, self.median)
                prior_rate = (
                    np.r_[1, (clean_prior - self.median) / self.scale, ~np.isfinite(prior)]
                    @ self.coefficients[: self.fixed_width]
                )
                actual_rate = np.array(
                    [
                        (history[index].volumes_mm3[k] - history[index - 1].volumes_mm3[k]) / (gap / 365.25)
                        for k in self.regions
                    ]
                )
                residuals.append(actual_rate - prior_rate)
            rate += np.sum(residuals, axis=0) / (len(residuals) + self.random_penalty)
        result = {
            k: float(history[-1].volumes_mm3[k] + rate[i] * interval_days / 365.25)
            for i, k in enumerate(self.regions)
        }
        if any(not np.isfinite(v) or v <= 0 for v in result.values()):
            raise ValueError("Forecast nonfinite/nonpositive; no clipping")
        return result

    def to_dict(self) -> dict:
        return {"fixed_penalty": self.fixed_penalty, "random_penalty": self.random_penalty,
                "with_scores": self.with_scores, "subjects": self.subjects,
                "regions": self.regions, "feature_names": self.feature_names,
                "median": self.median.tolist(), "scale": self.scale.tolist(),
                "coefficients": self.coefficients.tolist(), "fixed_width": self.fixed_width}

    @classmethod
    def from_dict(cls, data: dict) -> "RegularizedMixedEffects":
        model = cls(data["fixed_penalty"], data["random_penalty"], data["with_scores"])
        for name in ("subjects", "regions", "feature_names", "fixed_width"):
            setattr(model, name, data[name])
        for name in ("median", "scale", "coefficients"):
            setattr(model, name, np.asarray(data[name], dtype=float))
        width = len(model.feature_names)
        if (model.median.shape != (width,) or model.scale.shape != (width,) or model.fixed_width != 1 + 2 * width
            or model.coefficients.shape != (model.fixed_width + len(model.subjects), len(model.regions))
            or not all(np.isfinite(getattr(model, name)).all() for name in ("median", "scale", "coefficients"))
            or np.any(model.scale <= 0)):
            raise ValueError("Invalid structural checkpoint schema")
        return model


def evaluate(
    models: dict[str, RegularizedMixedEffects], examples: list[StructuralExample], split: dict[str, str]
) -> dict:
    if not examples or any(split.get(e.subject_id) != "test" for e in examples):
        raise ValueError("Evaluation requires frozen held-out test subjects")
    if any(e.subject_id in model.subjects for model in models.values() for e in examples):
        raise ValueError("Subject leakage across fit/evaluation")
    errors: dict[str, list[np.ndarray]] = {
        name: [] for name in ["no_change", "individual_linear_trend", *models]
    }
    for example in examples:
        predictions = simple_baselines(example.history, example.interval_days)
        predictions.update(
            {
                name: model.predict(example.subject_id, example.history, example.interval_days)
                for name, model in models.items()
            }
        )
        for method, predicted in predictions.items():
            errors[method].append(
                np.array([predicted[k] - example.target.volumes_mm3[k] for k in sorted(predicted)])
            )
    return {
        "subjects": len({e.subject_id for e in examples}),
        "examples": len(examples),
        "methods": {
            name: {
                "mae_mm3": float(np.mean(np.abs(values))),
                "rmse_mm3": float(np.sqrt(np.mean(np.square(values)))),
            }
            for name, values in errors.items()
        },
        "prediction_intervals": None,
        "coverage": None,
        "clinical_validation": False,
    }
