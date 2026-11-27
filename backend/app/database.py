"""SQLAlchemy engine/session wiring. Schema is managed by Alembic migrations
(backend/migrations/) — run `alembic upgrade head` from backend/ before
starting the API. See backend/README.md.

SQLite locally/in tests; Postgres (Neon, via the Vercel Marketplace) in
production — both go through the same Alembic chain (see migrations/env.py).
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def normalize_database_url(url: str) -> str:
    """Neon/Vercel typically hand back a bare `postgres://` or
    `postgresql://` URL (no driver) — rewrite it to use `psycopg` (v3)
    explicitly, since that's what's installed (see requirements.txt) and
    modern SQLAlchemy no longer guesses a default driver for Postgres.
    SQLite URLs pass through unchanged.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


settings = get_settings()
_database_url = normalize_database_url(settings.database_url)

_connect_args = {"check_same_thread": False} if _database_url.startswith("sqlite") else {}
engine = create_engine(_database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
