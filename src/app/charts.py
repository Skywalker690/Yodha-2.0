import pandas as pd


def trajectory(probabilities: dict) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Month": [int(h) for h, v in probabilities.items() if v is not None],
            "Estimated cumulative risk": [v for v in probabilities.values() if v is not None],
        }
    )
