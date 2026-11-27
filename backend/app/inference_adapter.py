"""Connects the backend to ml/boneage/onnx_inference.py (ONNX Runtime, no
torch/torchvision — see docs/architecture.md#deployment-notes for why), with
a clearly-labelled mock fallback when no exported model exists yet (no real
training has been run — see docs/model.md). The API always reports which
path produced a result via `prediction_source` ("real" | "mock") — see
docs/api.md.

Even in mock mode, the displayed X-ray (`plain_image`) is always the real
uploaded image — only the *heatmap* is fabricated when there's no trained
model to produce a real one, and that fake layer is visibly marked as such
(see `_mock_heatmap_layer`), never dressed up to look like a real measurement.
"""
from __future__ import annotations

import hashlib
import logging
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from .config import get_settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ML_DIR = _REPO_ROOT / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

# Used only to size/orient the displayed X-ray when there's no real pipeline
# config to read a size from (mock mode) — a display concern, not a model
# parameter. The real path uses the exported model's own metadata.json size.
_MOCK_DISPLAY_SIZE = 384

_REQUIRED_ONNX_FILENAMES = (
    "backbone.onnx",
    "head_part1.onnx",
    "head_part2.onnx",
    "metadata.json",
)

# Tracks whether a download has already been attempted this cold start, so a
# failed/unset ONNX_DOWNLOAD_URL doesn't retry a slow network call on every
# single request — Vercel's Python functions have no pre-start hook to run
# this once up front the way a long-running process would (see
# backend/README.md and docs/architecture.md#deployment-notes).
_download_attempted = False


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
    attention map.
    """
    width, height = size
    layer = Image.new("RGBA", size, (242, 166, 90, 90))  # flat amber tint, modest alpha
    draw = ImageDraw.Draw(layer)
    draw.rectangle([4, 4, width - 5, height - 5], outline=(122, 62, 0, 255), width=3)
    draw.text((16, height // 2 - 20), "MOCK HEATMAP", fill=(122, 62, 0, 255))
    draw.text((16, height // 2 + 4), "No trained checkpoint", fill=(122, 62, 0, 255))
    return layer


def _onnx_dir_is_populated(onnx_dir: Path) -> bool:
    return all((onnx_dir / name).exists() for name in _REQUIRED_ONNX_FILENAMES)


def _try_download_onnx_dir(onnx_dir: Path, download_url: str) -> None:
    """Best-effort fetch of a zip (containing `backbone.onnx`,
    `head_part1.onnx`, `head_part2.onnx`, `metadata.json` at its root) from
    `download_url`, extracted into `onnx_dir`. Never raises — a failure here
    must fall back to the mock predictor, not break the request.
    """
    try:
        onnx_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        urllib.request.urlretrieve(download_url, tmp_path)  # noqa: S310 - trusted, operator-configured URL
        with zipfile.ZipFile(tmp_path) as archive:
            archive.extractall(onnx_dir)
        tmp_path.unlink(missing_ok=True)
        logger.info("Downloaded and extracted the ONNX model into %s", onnx_dir)
    except Exception:  # noqa: BLE001 - never fail a request over this
        logger.warning("Could not download the ONNX model from ONNX_DOWNLOAD_URL", exc_info=True)


class InferenceAdapter:
    """Checks for an exported ONNX model on each use (lazily downloading it
    once per cold start if missing and `ONNX_DOWNLOAD_URL` is set), and
    falls back to the mock predictor otherwise.
    """

    def __init__(self, onnx_dir: str | Path | None = None) -> None:
        settings = get_settings()
        self.onnx_dir = Path(onnx_dir or settings.ml_onnx_dir)
        self._onnx_download_url = settings.onnx_download_url

    @property
    def is_real(self) -> bool:
        global _download_attempted
        if not _onnx_dir_is_populated(self.onnx_dir) and self._onnx_download_url and not _download_attempted:
            _download_attempted = True
            _try_download_onnx_dir(self.onnx_dir, self._onnx_download_url)
        return _onnx_dir_is_populated(self.onnx_dir)

    def predict(
        self, image_path: str | Path, sex_is_male: bool, mc_dropout_passes: int = 20
    ) -> PredictionResult:
        if self.is_real:
            return self._predict_real(image_path, sex_is_male, mc_dropout_passes)
        return self._predict_mock(image_path, sex_is_male)

    def _predict_real(
        self, image_path: str | Path, sex_is_male: bool, mc_dropout_passes: int
    ) -> PredictionResult:
        from boneage.onnx_inference import predict_single_image_onnx

        result = predict_single_image_onnx(
            self.onnx_dir, image_path, sex_is_male, mc_dropout_passes=mc_dropout_passes
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
        # Torch-free on purpose, same as the real path — see
        # ml/boneage/numpy_transforms.py's module docstring. The mock
        # fallback must never be the reason torch ends up installed.
        from boneage.numpy_transforms import load_and_orient, resize_with_pad

        base_image = load_and_orient(image_path)
        plain_image = resize_with_pad(base_image, _MOCK_DISPLAY_SIZE).convert("RGB")
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
