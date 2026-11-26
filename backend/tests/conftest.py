"""Test setup: a dedicated temp SQLite DB, migrated with the real Alembic
chain (not `create_all` — see docs/tasks.md Phase 3 "Use SQLite ... with
migrations"), a FastAPI TestClient, and small auth helpers.

Env vars are set *before* any `app.*` import, because `app.database` builds
its SQLAlchemy engine at import time from `app.config.get_settings()`.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_TMP_DIR = Path(tempfile.mkdtemp(prefix="boneage_backend_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(_TMP_DIR / "uploads")
# No checkpoint at this path -> InferenceAdapter.is_real is False by default,
# so tests exercise the mock predictor unless they explicitly point a test
# adapter at a real (tiny, freshly-trained) checkpoint.
os.environ["ML_CHECKPOINT_PATH"] = str(_TMP_DIR / "no_checkpoint_here.pt")
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-prod-needs-32-bytes-minimum")
os.environ.pop("OPENAI_API_KEY", None)  # force the template-note fallback by default

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _run_migrations() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


_run_migrations()

from app import models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402

DEFAULT_PASSWORD = "test-password"


@pytest.fixture(autouse=True)
def _clean_tables():
    """Each test starts from an empty (but migrated) database."""
    yield
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_user(db_session):
    def _make(email: str, role: str, password: str = DEFAULT_PASSWORD, name: str = "Test User") -> models.User:
        user = models.User(
            email=email, hashed_password=hash_password(password), role=role, name=name
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture
def auth_headers(client, make_user):
    """auth_headers("doctor") -> {"Authorization": "Bearer ..."} for a fresh doctor user."""

    def _headers(role: str, email: str | None = None, password: str = DEFAULT_PASSWORD) -> dict:
        email = email or f"{role}@test.local"
        make_user(email, role, password)
        response = client.post("/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers
