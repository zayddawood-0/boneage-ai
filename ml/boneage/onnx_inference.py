"""Torch-free single-image inference: bone age + MC-dropout uncertainty +
Score-CAM heatmap, via ONNX Runtime + numpy only. This is the backend's
deployed inference path (see docs/architecture.md#deployment-notes) —
deliberately imports neither `torch` nor `torchvision`, so it carries none
of their ~750 MB. See `onnx_export.py`'s module docstring for why the
exported model is split into three graphs (backbone+activations, head part
1, head part 2) and how that lets MC-dropout be reproduced exactly via
numpy-side Bernoulli masking instead of relying on ONNX Runtime semantics
PyTorch's exporter can't cleanly produce.

Mirrors `inference.py`'s `predict_single_image` contract (same
`PredictionResult` shape) so `backend/app/inference_adapter.py` can call
either one interchangeably.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

from .colormap import heatmap_layer_image, overlay_heatmap_on_image
from .numpy_transforms import load_and_orient, preprocess_to_numpy, resize_with_pad
from .prediction_result import PredictionResult
from .score_cam import compute_score_cam

# Filenames written by `onnx_export.export_to_onnx` and read here. Defined in
# this (torch-free) module, not `onnx_export.py`, so importing them never
# pulls torch in — `onnx_export.py` imports these from here instead, not the
# other way around (see this module's docstring).
BACKBONE_FILENAME = "backbone.onnx"
HEAD1_FILENAME = "head_part1.onnx"
HEAD2_FILENAME = "head_part2.onnx"
METADATA_FILENAME = "metadata.json"


@dataclass(frozen=True)
class OnnxMetadata:
    image_size: int
    normalize_mean: list[float]
    normalize_std: list[float]
    backbone: str
    feature_dim: int
    hidden_dim: int
    dropout: float
    mc_dropout_passes: int
    score_cam_top_k: int


def load_metadata(onnx_dir: str | Path) -> OnnxMetadata:
    raw = json.loads((Path(onnx_dir) / METADATA_FILENAME).read_text(encoding="utf-8"))
    return OnnxMetadata(**raw)


def _dropout_mask(rng: np.random.Generator, shape: tuple[int, ...], p: float) -> np.ndarray:
    """"Inverted dropout" mask — zero with probability `p`, survivors scaled
    by `1 / (1 - p)` — the exact scheme `torch.nn.Dropout` uses, so running
    this against the (dropout-free) exported head graphs is numerically
    equivalent to the real model's `set_mc_dropout_mode(model, True)` path.
    """
    if p <= 0:
        return np.ones(shape, dtype=np.float32)
    keep_prob = 1.0 - p
    keep = (rng.random(shape) < keep_prob).astype(np.float32)
    return keep / keep_prob


class OnnxModel:
    """Lazily loads and caches the three ONNX Runtime sessions for one
    export directory (see `onnx_export.export_to_onnx`)."""

    def __init__(self, onnx_dir: str | Path) -> None:
        self.onnx_dir = Path(onnx_dir)
        self.metadata = load_metadata(self.onnx_dir)
        self._backbone: ort.InferenceSession | None = None
        self._head1: ort.InferenceSession | None = None
        self._head2: ort.InferenceSession | None = None

    def _session(self, attr: str, filename: str) -> ort.InferenceSession:
        session = getattr(self, attr)
        if session is None:
            session = ort.InferenceSession(str(self.onnx_dir / filename))
            setattr(self, attr, session)
        return session

    def run_backbone(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """`image`: (1, 3, H, W) float32 -> `(features, activations)`."""
        session = self._session("_backbone", BACKBONE_FILENAME)
        features, activations = session.run(None, {"image": image.astype(np.float32)})
        return features, activations

    def run_head(self, combined: np.ndarray) -> float:
        """Deterministic (no masking) head forward — `combined`:
        `(1, feature_dim + 1)` -> the scalar bone-age prediction."""
        head1 = self._session("_head1", HEAD1_FILENAME)
        head2 = self._session("_head2", HEAD2_FILENAME)
        (hidden,) = head1.run(None, {"masked_combined": combined.astype(np.float32)})
        (pred,) = head2.run(None, {"masked_hidden": hidden.astype(np.float32)})
        return float(pred.reshape(-1)[0])

    def run_head_with_dropout(self, combined: np.ndarray, rng: np.random.Generator) -> float:
        """One stochastic MC-dropout pass through the head only — the
        backbone has no dropout of its own, so it's never rerun here (see
        `predict_single_image_onnx`, which calls `run_backbone` once)."""
        head1 = self._session("_head1", HEAD1_FILENAME)
        head2 = self._session("_head2", HEAD2_FILENAME)
        p = self.metadata.dropout

        mask1 = _dropout_mask(rng, combined.shape, p)
        (hidden,) = head1.run(None, {"masked_combined": (combined * mask1).astype(np.float32)})

        mask2 = _dropout_mask(rng, hidden.shape, p)
        (pred,) = head2.run(None, {"masked_hidden": (hidden * mask2).astype(np.float32)})
        return float(pred.reshape(-1)[0])


def predict_single_image_onnx(
    onnx_dir: str | Path,
    image_path: str | Path,
    sex_is_male: bool,
    mc_dropout_passes: int | None = None,
    rng: np.random.Generator | None = None,
) -> PredictionResult:
    """Predict bone age + MC-dropout uncertainty + Score-CAM heatmap for one
    image, using the ONNX graphs exported by `onnx_export.export_to_onnx`
    into `onnx_dir`. See this module's docstring for the overall approach.
    """
    rng = rng or np.random.default_rng()
    onnx_model = OnnxModel(onnx_dir)
    meta = onnx_model.metadata
    n_passes = mc_dropout_passes or meta.mc_dropout_passes
    sex_value = 1.0 if sex_is_male else 0.0

    base_image = load_and_orient(image_path)
    image_array = preprocess_to_numpy(base_image, meta.image_size, meta.normalize_mean, meta.normalize_std)

    # The backbone has no dropout of its own, so one deterministic pass
    # gives both the pooled features every MC-dropout sample reuses, and the
    # activations Score-CAM reads — cheaper than the real PyTorch path,
    # which reruns the (also-deterministic) backbone on every MC pass.
    features, activations = onnx_model.run_backbone(image_array)
    activations = activations[0]  # drop the batch dim -> (C, h, w)
    combined = np.concatenate([features, np.array([[sex_value]], dtype=np.float32)], axis=1)

    # 1. MC dropout: stochastic head-only passes -> mean (point estimate) + spread (uncertainty).
    samples = [onnx_model.run_head_with_dropout(combined, rng) for _ in range(n_passes)]
    bone_age_months = float(np.mean(samples))
    uncertainty_months = float(np.std(samples))

    # 2. Score-CAM: one deterministic pass for the reference score, then up
    # to `score_cam_top_k` masked deterministic passes (dropout off throughout).
    full_score = onnx_model.run_head(combined)

    def score_fn(mask: np.ndarray) -> float:
        masked_image = image_array * mask[np.newaxis, np.newaxis, :, :]
        masked_features, _ = onnx_model.run_backbone(masked_image)
        masked_combined = np.concatenate(
            [masked_features, np.array([[sex_value]], dtype=np.float32)], axis=1
        )
        return onnx_model.run_head(masked_combined)

    cam = compute_score_cam(
        activations=activations,
        full_score=full_score,
        score_fn=score_fn,
        mask_size=(meta.image_size, meta.image_size),
        top_k=meta.score_cam_top_k,
    )

    padded_image = resize_with_pad(base_image, meta.image_size)
    plain_image = padded_image.convert("RGB")
    heatmap_image = overlay_heatmap_on_image(padded_image, cam)
    heatmap_layer = heatmap_layer_image(cam, plain_image.size)

    return PredictionResult(
        bone_age_months=bone_age_months,
        uncertainty_months=uncertainty_months,
        mc_dropout_samples=samples,
        heatmap_image=heatmap_image,
        plain_image=plain_image,
        heatmap_layer=heatmap_layer,
    )
