from pathlib import Path

from src.common import read_table, resolve


def scans(cfg: dict):
    return read_table(resolve(cfg["processed_dir"]) / "manifest.csv")


def subject_dir(cfg: dict, scan_id: str) -> Path:
    if (
        not isinstance(scan_id, str)
        or not scan_id
        or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in scan_id)
    ):
        raise ValueError("Invalid scan ID")
    return resolve(cfg["output_dir"]) / scan_id
