"""Internal, non-clinical endpoints — not part of the doctor/radiographer/
admin permission matrix (docs/requirements.md#user-roles). Currently just
the data-retention cleanup task, triggered by Vercel Cron rather than a
user — guarded by a shared secret (`CRON_SECRET`), not a user JWT. See
`vercel.json`'s `crons` entry and
https://vercel.com/docs/cron-jobs/manage-cron-jobs#securing-cron-jobs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..retention import cleanup_expired_images

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_cron_secret(authorization: str | None = Header(default=None)) -> None:
    cron_secret = get_settings().cron_secret
    # No configured secret -> always reject, rather than accept every caller
    # (an unset CRON_SECRET must never mean "this endpoint is open").
    if not cron_secret or authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")


@router.get("/retention-cleanup")
def retention_cleanup(
    db: Session = Depends(get_db), _verified: None = Depends(_verify_cron_secret)
) -> dict:
    cleaned = cleanup_expired_images(db)
    return {"ok": True, "cases_cleaned": cleaned}
