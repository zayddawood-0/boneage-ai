"""Connects the backend to ml/boneage/inference.py, with a clearly-labelled
mock fallback when no trained checkpoint exists yet (no real training has
been run — see docs/model.md). The API always reports which path produced a
result via `prediction_source` ("real" | "mock") — see docs/api.md.

Even in mock mode, the displayed X-ray (`plain_image`) is always the real
uploaded image — only the *heatmap* is fabricated when there's no trained
model to produce a real one, and that fake layer is visibly marked as such
(see `_mock_heatmap_layer`), never dressed up to look like a real measurement.
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

# Used only to size/orient the displayed X-ray when there's no real pipeline
# config to read a size from (mock mode) — a display concern, not a model
# parameter. The real path uses the trained model's own configured size.
_MOCK_DISPLAY_SIZE = 384


@dataclass(frozen=True)
class PredictionResult:
    bone_age_months: float
    uncertainty_months: float
    heatmap_image: Image.Image  # pre-blended, for the PDF report
    plain_image: Image.Image  # the X-ray alone (RGB) — always real, even in mock mode
    heatmap_layer: Image.Image  # the heatmap alone (RGBA) — fabricated in mock mode
    source: str  # "real" | "mock"


# The mock predictor deliberately returns a WIDE uncertainty, so a mock
# result naturally gets flagged "uncertain" by the growth review agent
# (backend/app/agent/tools.py) rather than being silently trusted as a real
# measurement — see docs/safety-and-ethics.md's "flag when uncertain" rule.
MOCK_UNCERTAINTY_MONTHS = 24.0
MOCK_BONE_AGE_RANGE_MONTHS = (24.0, 216.0)


def _mock_bone_age_months(image_path: str | Path, sex_is_male: bool) -> float:
    """Deterministic-but-fake: the same image + sex always gives the same
    mock number, so repeated calls/tests are stable — this is NOT a model
    prediction of any kind, just a stand-in so the app is demoable before
    training finishes.
    """
    digest = hashlib.sha256(f"{Path(image_path).name}:{sex_is_male}".encode("utf-8")).hexdigest()
    pseudo_random = int(digest[:8], 16) / 0xFFFFFFFF  # in [0, 1)
    lo, hi = MOCK_BONE_AGE_RANGE_MONTHS
    return round(lo + pseudo_random * (hi - lo), 1)


def _mock_heatmap_layer(size: tuple[int, int]) -> Image.Image:
    """A heatmap layer that's visibly fake — a flat amber tint plus "MOCK"
    text baked into the (semi-transparent) layer itself, so it reads clearly
    wherever the frontend composites it, never mistakeable for a real
    Grad-CAM attention map.
    """
    width, height = size
    layer = Image.new("RGBA", size, (242, 166, 90, 90))  # flat amber tint, modest alpha
    draw = ImageDraw.Draw(layer)
    draw.rectangle([4, 4, width - 5, height - 5], outline=(122, 62, 0, 255), width=3)
    draw.text((16, height // 2 - 20), "MOCK HEATMAP", fill=(122, 62, 0, 255))
    draw.text((16, height // 2 + 4), "No trained checkpoint", fill=(122, 62, 0, 255))
    return layer


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
        if self.is_real:
            return self._predict_real(image_path, sex_is_male, mc_dropout_passes)
        return self._predict_mock(image_path, sex_is_male)

    def _predict_real(
        self, image_path: str | Path, sex_is_male: bool, mc_dropout_passes: int
    ) -> PredictionResult:
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
            plain_image=result.plain_image,
            heatmap_layer=result.heatmap_layer,
            source="real",
        )

    def _predict_mock(self, image_path: str | Path, sex_is_male: bool) -> PredictionResult:
        from boneage.transforms import ResizeWithPad, load_and_orient

        base_image = load_and_orient(image_path)
        plain_image = ResizeWithPad(_MOCK_DISPLAY_SIZE)(base_image).convert("RGB")
        heatmap_layer = _mock_heatmap_layer(plain_image.size)
        heatmap_image = Image.alpha_composite(plain_image.convert("RGBA"), heatmap_layer).convert("RGB")

        return PredictionResult(
            bone_age_months=_mock_bone_age_months(image_path, sex_is_male),
            uncertainty_months=MOCK_UNCERTAINTY_MONTHS,
            heatmap_image=heatmap_image,
            plain_image=plain_image,
            heatmap_layer=heatmap_layer,
            source="mock",
        )
