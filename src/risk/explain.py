import numpy as np

from src.risk.baseline import transformed


def explain(head: dict, values: np.ndarray, fields: list[str]) -> list[dict]:
    terms = transformed(head, values)[0] * np.asarray(head["coefficients"])
    return sorted(
        [
            {
                "feature": field,
                "standardized_coefficient": float(weight),
                "logit_contribution": float(term),
                "direction": "increases" if term > 0 else "decreases",
            }
            for field, weight, term in zip(fields, head["coefficients"], terms)
        ],
        key=lambda item: abs(item["logit_contribution"]),
        reverse=True,
    )
