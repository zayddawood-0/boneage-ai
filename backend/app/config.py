"""App settings, read from environment variables / .env.

See backend/.env.example for the full list and docs/architecture.md for how
these map onto the deployment (Vercel: frontend + backend, both as separate
Vercel projects — see README.md#deployment-setup-vercel--github-actions).
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / "backend" / ".env"), extra="ignore")

    # sqlite for local dev/tests (default); a Postgres URL (e.g. Neon, via
    # the Vercel Marketplace) in production — see database.py for how a
    # bare `postgres://`/`postgresql://` URL gets normalised to use psycopg.
    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'boneage.db'}"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480

    # Local disk, used whenever `blob_read_write_token` is unset (local dev,
    # tests) — see storage.py.
    upload_dir: Path = REPO_ROOT / "backend" / "uploads"

    # Vercel Blob — set automatically by Vercel when a Blob store is
    # connected to the project. Its mere presence is what switches
    # storage.py from local disk to Blob (no separate on/off setting).
    blob_read_write_token: str = ""

    # Where the ONNX graphs + metadata.json (ml/boneage/onnx_export.py) live
    # — gitignored, like the .pt checkpoint used to be. Lazily downloaded
    # from `onnx_download_url` on first real prediction if missing (see
    # inference_adapter.py) rather than at a separate startup step, since
    # Vercel's Python functions have no pre-start hook to run one in.
    ml_onnx_dir: Path = REPO_ROOT / "ml" / "checkpoints" / "onnx"
    onnx_download_url: str = ""

    # Where ml/evaluate.py writes val_results.json (see
    # ml/boneage/config.py's EvaluationConfig.output_dir) — read by
    # GET /model/performance (routers/model_performance.py).
    ml_results_dir: Path = REPO_ROOT / "ml" / "results"

    openai_api_key: str = ""

    reference_table_path: Path = (
        REPO_ROOT / "backend" / "data" / "reference_tables" / "greulich_pyle_sd_reference.json"
    )

    # Comma-separated list of allowed frontend origins for CORS — set to the
    # Vercel frontend project's URL in production.
    cors_origin: str = "http://localhost:5173"

    # Verifies that GET /internal/retention-cleanup really was invoked by
    # Vercel Cron (which sends this as `Authorization: Bearer <value>`) and
    # not a public hit on that URL — see routers/internal.py and
    # https://vercel.com/docs/cron-jobs/manage-cron-jobs#securing-cron-jobs.
    # Empty (the local-dev default) means the endpoint always 401s.
    cron_secret: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origin.split(",") if origin.strip()]

    @property
    def use_blob_storage(self) -> bool:
        return bool(self.blob_read_write_token)


def get_settings() -> Settings:
    return Settings()
