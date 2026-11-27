"""Data-retention cleanup: deletes X-ray images and heatmaps for cases older
than the configured retention period (docs/safety-and-ethics.md#privacy,
`GrowthReviewSettings.retention_days`, admin-configurable via PUT /settings).

Scope is deliberately narrow: only the image files on disk, and the DB path
columns pointing at them, are removed — the case record itself (prediction
numbers, flag status, doctor decision) is kept so review history and model
performance stats stay intact. After cleanup, `GET /cases/{id}/image` and
friends 404 (see backend/app/routers/cases.py), same as a case that never had
an image.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models
from .settings_store import get_or_create_settings


def _unlink_if_exists(path_str: str | None) -> None:
    if not path_str:
        return
    path = Path(path_str)
    if path.exists():
        path.unlink()


def cleanup_expired_images(db: Session, *, now: dt.datetime | None = None) -> int:
    """Deletes image/heatmap files for cases past the configured retention
    period and clears their path columns. Returns the number of cases cleaned.
    """
    now = now or dt.datetime.now(dt.UTC)
    settings_row = get_or_create_settings(db)
    cutoff = now - dt.timedelta(days=settings_row.retention_days)

    expired_cases = (
        db.query(models.Case)
        .filter(models.Case.created_at < cutoff)
        .filter(
            or_(
                models.Case.image_path.is_not(None),
                models.Case.display_image_path.is_not(None),
                models.Case.heatmap_path.is_not(None),
                models.Case.heatmap_layer_path.is_not(None),
            )
        )
        .all()
    )

    for case in expired_cases:
        _unlink_if_exists(case.image_path)
        _unlink_if_exists(case.display_image_path)
        _unlink_if_exists(case.heatmap_path)
        _unlink_if_exists(case.heatmap_layer_path)
        case.image_path = None
        case.display_image_path = None
        case.heatmap_path = None
        case.heatmap_layer_path = None

    db.commit()
    return len(expired_cases)
