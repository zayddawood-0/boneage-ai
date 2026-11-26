"""GET /model/performance — docs/api.md. Every figure stays `[TBD]` until a
real checkpoint has actually been trained and evaluated (see
ml/evaluate.py, ml/README.md) — this endpoint never fabricates a number.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from .. import models
from ..config import get_settings
from ..deps import require_roles

router = APIRouter(prefix="/model", tags=["model"])

# Model performance — doctor and admin only, per docs/requirements.md#user-roles.
_ALLOWED = ("doctor", "admin")

_TBD = "[TBD]"


@router.get("/performance")
def get_model_performance(
    _user: models.User = Depends(require_roles(*_ALLOWED)),
) -> dict:
    settings = get_settings()
    results_dir = settings.ml_checkpoint_path.parent.parent / "results"

    val_results_path = results_dir / "val_results.json"
    if val_results_path.exists():
        with val_results_path.open("r", encoding="utf-8") as f:
            real = json.load(f)
        return {
            "mae_overall_months": real.get("mae_overall_months", _TBD),
            "mae_by_sex": real.get("mae_by_sex_months", {"male": _TBD, "female": _TBD}),
            "mae_by_age_band": real.get("mae_by_age_band_months", _TBD),
            "pct_within_12_months": real.get("percent_within_threshold", _TBD),
            "model_card": {"version": _TBD},
        }

    return {
        "mae_overall_months": _TBD,
        "mae_by_sex": {"male": _TBD, "female": _TBD},
        "mae_by_age_band": _TBD,
        "pct_within_12_months": _TBD,
        "model_card": {"version": _TBD},
    }
