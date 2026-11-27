#!/usr/bin/env python
"""Deletes X-ray images and heatmaps for cases past the configured retention
period (docs/safety-and-ethics.md#privacy, Settings > Data & privacy).

Not wired into a scheduler by default for the hackathon build — run it
manually (e.g. before/after a demo), or point a host-level cron / Render Cron
Job at it. Safe to run repeatedly: cases already cleaned are skipped.

Usage (from the repo root, after `alembic upgrade head` in backend/):
    python backend/scripts/cleanup_retention.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.retention import cleanup_expired_images  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        cleaned = cleanup_expired_images(db)
    finally:
        db.close()
    print(
        f"Retention cleanup: removed images/heatmaps for {cleaned} case(s) "
        "past the configured retention period."
    )


if __name__ == "__main__":
    main()
