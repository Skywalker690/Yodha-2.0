from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = (12, 24, 36)
TARGET = "observed_cdr_conversion"
VERSION = "oasis-baseline-fastsurfer-v2"
CLINICAL = ("age_years", "sex", "education", "ses", "mmse", "cdr", "etiv", "nwbv", "asf")


def config(path: str | Path) -> dict:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Configuration must be a mapping")
    return value


def resolve(value: str) -> Path:
    path = Path(value)
    return (ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def read_table(path: Path, key: str = "patient_id") -> pd.DataFrame:
    frame = pd.read_csv(path)
    if key not in frame or frame[key].isna().any() or frame[key].duplicated().any():
        raise ValueError(f"Table requires unique nonmissing {key}")
    return frame


def command(default: str = "configs/experiment.yaml", model: bool = False) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=default)
    if model:
        parser.add_argument("--model", choices=("clinical", "clinical_fastsurfer"), default="clinical")
        parser.add_argument("--matched", action="store_true", help="Fit clinical on the exact MRI-QC cohort")
    return parser.parse_args()
