"""App settings, read from environment variables / .env.

See backend/.env.example for the full list and docs/architecture.md for how
these map onto the hackathon deployment.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / "backend" / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'boneage.db'}"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480

    upload_dir: Path = REPO_ROOT / "backend" / "uploads"

    ml_checkpoint_path: Path = REPO_ROOT / "ml" / "checkpoints" / "best_model.pt"
    ml_config_path: Path = REPO_ROOT / "ml" / "config" / "config.yaml"

    openai_api_key: str = ""

    reference_table_path: Path = (
        REPO_ROOT / "backend" / "data" / "reference_tables" / "greulich_pyle_sd_reference.json"
    )

    # Comma-separated list of allowed frontend origins for CORS — set to the
    # Vercel URL in production (see render.yaml, README.md deployment setup).
    cors_origin: str = "http://localhost:5173"

    # Optional URL to fetch the trained model checkpoint from at startup
    # (see backend/scripts/download_checkpoint.py). The checkpoint itself is
    # gitignored, so Render's ephemeral filesystem needs this on each deploy;
    # if unset or the download fails, the API falls back to the mock
    # predictor automatically (app/inference_adapter.py).
    checkpoint_download_url: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origin.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()
