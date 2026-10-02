from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "postgresql+psycopg://neuropredict:neuropredict@127.0.0.1:55432/neuropredict"
    jwt_secret: str
    seed_email: str = "researcher@neuropredict.local"
    seed_password: str
    storage_root: Path = ROOT / "storage"
    dataset_root: Path = ROOT / "dataset"
    trained_model_path: Path = ROOT / "data/training_multimodal/runs/20261001T134908Z/multimodal_model.pt"
    ml_only: bool = True
    forecast_artifact_dir: Path = ROOT / "artifacts/forecast_v2"
    forecast_processed_dir: Path = ROOT / "data/forecast_v2"
    avra_runtime_manifest: Path | None = None
    anatomy_release_dir: Path = ROOT / "artifacts/anatomy-release"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    secure_cookies: bool = False
    max_upload_bytes: int = 100 * 1024 * 1024
    token_minutes: int = 480
    worker_poll_seconds: float = 1.0

    @field_validator("jwt_secret")
    @classmethod
    def secret_length(cls, value: str) -> str:
        if len(value) < 32 or value.startswith("replace-"):
            raise ValueError("Set a random JWT_SECRET of at least 32 characters. Run scripts/setup_env.py.")
        return value

    @field_validator("seed_password")
    @classmethod
    def password_length(cls, value: str) -> str:
        if len(value) < 12 or value.startswith("replace-"):
            raise ValueError("Set SEED_PASSWORD to at least 12 characters. Run scripts/setup_env.py.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
