"""normalize_database_url (app/database.py): Neon/Vercel hand back a bare
postgres:// or postgresql:// URL — rewritten to use the psycopg (v3) driver
explicitly, since modern SQLAlchemy no longer guesses a default Postgres
driver. SQLite URLs (local dev/tests) pass through unchanged.
"""
from __future__ import annotations

from app.database import normalize_database_url


def test_sqlite_url_passes_through_unchanged():
    url = "sqlite:///./backend/boneage.db"
    assert normalize_database_url(url) == url


def test_postgres_scheme_gets_psycopg_driver():
    url = "postgres://user:pass@host.neon.tech/dbname?sslmode=require"
    assert normalize_database_url(url) == (
        "postgresql+psycopg://user:pass@host.neon.tech/dbname?sslmode=require"
    )


def test_postgresql_scheme_gets_psycopg_driver():
    url = "postgresql://user:pass@host.neon.tech/dbname"
    assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host.neon.tech/dbname"


def test_already_explicit_driver_passes_through_unchanged():
    url = "postgresql+psycopg://user:pass@host.neon.tech/dbname"
    assert normalize_database_url(url) == url
