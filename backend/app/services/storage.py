from pathlib import Path
from uuid import uuid4

from backend.app.core.config import get_settings


def root() -> Path:
    path = get_settings().storage_root.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_key(key: str) -> Path:
    if "\\" in key or ":" in key or key.startswith("/"):
        raise ValueError("Invalid storage key")
    target = (root() / key).resolve()
    if not target.is_relative_to(root()) or target == root():
        raise ValueError("Invalid storage key")
    return target


def new_key(kind: str, suffix: str) -> str:
    if kind not in {"raw", "derived", "reports", "staging", "cache"}:
        raise ValueError("Invalid object category")
    key = f"{kind}/{uuid4().hex}{suffix}"
    resolve_key(key).parent.mkdir(parents=True, exist_ok=True)
    return key
