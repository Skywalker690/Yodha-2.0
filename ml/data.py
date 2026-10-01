from pathlib import Path

import pandas as pd

REQUIRED_METADATA = {"Subject ID", "MRI ID", "Visit", "MR Delay", "CDR"}
REQUIRED_MANIFEST = {"patient_id", "visit_id", "visit_index", "days_from_baseline", "mri_path"}


def read_metadata(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path) if path.suffix.lower() == ".xlsx" else pd.read_csv(path)
    if not REQUIRED_METADATA.issubset(df.columns):
        raise ValueError(f"Metadata needs columns: {', '.join(sorted(REQUIRED_METADATA))}")
    if df["MRI ID"].duplicated().any() or df[list(REQUIRED_METADATA)].isnull().any().any():
        raise ValueError("Metadata has duplicate MRI IDs or missing required values")
    df["MR Delay"] = pd.to_numeric(df["MR Delay"], errors="raise")
    if (df["MR Delay"] < 0).any():
        raise ValueError("MR Delay must be nonnegative")
    return df.sort_values(["Subject ID", "MR Delay"])


def read_manifest(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if not REQUIRED_MANIFEST.issubset(df.columns):
        raise ValueError("Manifest is missing required fields")
    if df[list(REQUIRED_MANIFEST)].isnull().any().any():
        raise ValueError("Manifest has missing required values")
    if (
        df.duplicated(["patient_id", "visit_id"]).any()
        or df.duplicated(["patient_id", "days_from_baseline"]).any()
    ):
        raise ValueError("Manifest has duplicate visits or dates")
    if (pd.to_numeric(df["days_from_baseline"]) < 0).any():
        raise ValueError("Visit days must be nonnegative")
    if "split" in df and (df.groupby("patient_id")["split"].nunique() > 1).any():
        raise ValueError("Subject leakage: a patient appears in more than one split")
    return df.sort_values(["patient_id", "days_from_baseline"])
