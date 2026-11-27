"""App settings, read from environment variables / .env.

See backend/.env.example for the full list and docs/architecture.md for how
these map onto the deployment (Vercel: frontend + backend, both as separate
Vercel projects — see README.md#deployment-setup-vercel--github-actions).
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

# Vercel sets VERCEL=1 in every deployed function's environment (local dev
# and CI never set it). The deployed function's own filesystem — where the
# repo checkout, including ml/checkpoints/, lives — is read-only; only /tmp
# is writable, and it persists across invocations handled by the same warm
# instance (reset on the next cold start). Defaulting the ONNX model
# directory there means a warm function reuses the already-downloaded model
# instead of re-fetching it from ONNX_DOWNLOAD_URL on every request — see
# inference_adapter.py.
_ON_VERCEL = os.environ.get("VERCEL") == "1"
_DEFAULT_ML_ONNX_DIR = Path("/tmp/boneage-onnx") if _ON_VERCEL else REPO_ROOT / "ml" / "checkpoints" / "onnx"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / "backend" / ".env"), extra="ignore")

    # sqlite for local dev/tests (default); a Postgres URL (e.g. Neon, via
    # the Vercel Marketplace) in production — see database.py for how a
    # bare `postgres://`/`postgresql://` URL gets normalised to use psycopg.
    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'boneage.db'}"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480

    # Local disk, used whenever Blob isn't configured (local dev, tests) —
    # see storage.py.
    upload_dir: Path = REPO_ROOT / "backend" / "uploads"

    # Vercel Blob — set automatically by Vercel when a Blob store is
    # connected to the project. Connecting a store via `vercel storage
    # connect` (the current, OIDC-based credential mode) sets
    # `BLOB_STORE_ID` (paired with an OIDC token the `vercel-blob` SDK reads
    # from the request context itself — no static secret involved); an
    # older/manually-issued read-write token would instead be
    # `BLOB_READ_WRITE_TOKEN`. Either one's mere presence is what switches
    # storage.py from local disk to Blob (no separate on/off setting) — see
    # `use_blob_storage` below.
    blob_store_id: str = ""
    blob_read_write_token: str = ""

    # Where the ONNX graphs + metadata.json (ml/boneage/onnx_export.py) live
    # — gitignored, like the .pt checkpoint used to be. Lazily downloaded
    # from `onnx_download_url` on first real prediction if missing (see
    # inference_adapter.py) rather than at a separate startup step, since
    # Vercel's Python functions have no pre-start hook to run one in.
    ml_onnx_dir: Path = _DEFAULT_ML_ONNX_DIR
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
        return bool(self.blob_store_id or self.blob_read_write_token)


def get_settings() -> Settings:
    return Settings()
