"""Connects the backend to ml/boneage/inference.py, with a clearly-labelled
mock fallback when no trained checkpoint exists yet (no real training has
been run — see docs/model.md). The API always reports which path produced a
result via `prediction_source` ("real" | "mock") — see docs/api.md.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from .config import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ML_DIR = _REPO_ROOT / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


@dataclass(frozen=True)
class PredictionResult:
    bone_age_months: float
    uncertainty_months: float
    heatmap_image: Image.Image
    source: str  # "real" | "mock"


# The mock predictor deliberately returns a WIDE uncertainty, so a mock
# result naturally gets flagged "uncertain" by the growth review agent
# (backend/app/agent/tools.py) rather than being silently trusted as a real
# measurement — see docs/safety-and-ethics.md's "flag when uncertain" rule.
MOCK_UNCERTAINTY_MONTHS = 24.0
MOCK_BONE_AGE_RANGE_MONTHS = (24.0, 216.0)


def _mock_predict(image_path: str | Path, sex_is_male: bool) -> PredictionResult:
    """Deterministic-but-fake: the same image + sex always gives the same
    mock number, so repeated calls/tests are stable — this is NOT a model
    prediction of any kind, just a stand-in so the app is demoable before
    training finishes.
    """
    digest = hashlib.sha256(f"{Path(image_path).name}:{sex_is_male}".encode("utf-8")).hexdigest()
    pseudo_random = int(digest[:8], 16) / 0xFFFFFFFF  # in [0, 1)
    lo, hi = MOCK_BONE_AGE_RANGE_MONTHS
    bone_age_months = lo + pseudo_random * (hi - lo)

    heatmap = Image.new("RGB", (384, 384), color=(28, 25, 23))
    draw = ImageDraw.Draw(heatmap)
    draw.rectangle([8, 8, 375, 375], outline=(242, 166, 90), width=4)
    draw.text((24, 168), "MOCK PREDICTION", fill=(242, 166, 90))
    draw.text((24, 192), "No trained checkpoint available", fill=(168, 160, 151))

    return PredictionResult(
        bone_age_months=round(bone_age_months, 1),
        uncertainty_months=MOCK_UNCERTAINTY_MONTHS,
        heatmap_image=heatmap,
        source="mock",
    )


class InferenceAdapter:
    """Lazily loads the real checkpoint on first use, if one exists."""

    def __init__(
        self, checkpoint_path: str | Path | None = None, ml_config_path: str | Path | None = None
    ) -> None:
        settings = get_settings()
        self.checkpoint_path = Path(checkpoint_path or settings.ml_checkpoint_path)
        self.ml_config_path = Path(ml_config_path or settings.ml_config_path)
        self._model = None
        self._pipeline_config = None

    @property
    def is_real(self) -> bool:
        return self.checkpoint_path.exists()

    def _ensure_real_model_loaded(self) -> None:
        if self._model is not None:
            return
        from boneage.config import load_config
        from boneage.inference import load_checkpoint

        self._pipeline_config = load_config(self.ml_config_path)
        self._model, _ = load_checkpoint(self.checkpoint_path, device="cpu")

    def predict(
        self, image_path: str | Path, sex_is_male: bool, mc_dropout_passes: int = 20
    ) -> PredictionResult:
        if not self.is_real:
            return _mock_predict(image_path, sex_is_male)

        from boneage.inference import predict_single_image

        self._ensure_real_model_loaded()
        result = predict_single_image(
            self._model,
            image_path,
            sex_is_male,
            preprocessing_config=self._pipeline_config.preprocessing,
            mc_dropout_passes=mc_dropout_passes,
            device="cpu",
        )
        return PredictionResult(
            bone_age_months=result.bone_age_months,
            uncertainty_months=result.uncertainty_months,
            heatmap_image=result.heatmap_image,
            source="real",
        )
