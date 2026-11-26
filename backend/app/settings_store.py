"""Reads/creates the singleton GrowthReviewSettings row (id=1).

Defaults here (fixed_months, ±12 months, etc.) are reasonable hackathon
starting points, not clinical facts — see docs/model.md and
docs/requirements.md#settings. Everything is admin-editable via
PUT /settings.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import models

SETTINGS_ROW_ID = 1


def get_or_create_settings(db: Session) -> models.GrowthReviewSettings:
    settings_row = db.get(models.GrowthReviewSettings, SETTINGS_ROW_ID)
    if settings_row is None:
        settings_row = models.GrowthReviewSettings(id=SETTINGS_ROW_ID)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row
