from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles
from ..settings_store import get_or_create_settings

router = APIRouter(prefix="/settings", tags=["settings"])

# Settings (flagging rules, agent behaviour, data & privacy) — admin only
# per the permission matrix in docs/requirements.md#user-roles. The personal
# theme/age-unit preference (docs/design.md#8-settings: "remain available to
# all roles outside this screen") is intentionally NOT served from this
# endpoint — it's a per-user, client-side preference for the eventual
# frontend to own (e.g. local storage), not part of the shared admin config.
_ADMIN_ONLY = ("admin",)


@router.get("", response_model=schemas.SettingsOut)
def get_settings_endpoint(
    db: Session = Depends(get_db), _user: models.User = Depends(require_roles(*_ADMIN_ONLY))
) -> models.GrowthReviewSettings:
    return get_or_create_settings(db)


@router.put("", response_model=schemas.OkResponse)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_ADMIN_ONLY)),
) -> schemas.OkResponse:
    settings_row = get_or_create_settings(db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(settings_row, field, value)
    db.commit()
    return schemas.OkResponse(ok=True)
