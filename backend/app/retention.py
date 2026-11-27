"""Data-retention cleanup: deletes X-ray images and heatmaps for cases older
than the configured retention period (docs/safety-and-ethics.md#privacy,
`GrowthReviewSettings.retention_days`, admin-configurable via PUT /settings).

Scope is deliberately narrow: only the stored image files (local disk or
Vercel Blob, see storage.py), and the DB path columns pointing at them, are
removed — the case record itself (prediction numbers, flag status, doctor
decision) is kept so review history and model performance stats stay intact.
After cleanup, `GET /cases/{id}/image` and friends 404 (see
backend/app/routers/cases.py), same as a case that never had an image.

Run on a schedule via Vercel Cron (see `routers/internal.py`'s
`GET /internal/retention-cleanup`, called from `vercel.json`'s `crons`) —
not a separate background process, since Vercel's Python functions have no
long-running process to attach one to.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models
from .settings_store import get_or_create_settings
from .storage import delete_case_image


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
        delete_case_image(case.image_path)
        delete_case_image(case.display_image_path)
        delete_case_image(case.heatmap_path)
        delete_case_image(case.heatmap_layer_path)
        case.image_path = None
        case.display_image_path = None
        case.heatmap_path = None
        case.heatmap_layer_path = None

    db.commit()
    return len(expired_cases)
