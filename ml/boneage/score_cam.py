"""Score-CAM: a gradient-free stand-in for Grad-CAM, for the ONNX inference
path (ONNX Runtime gives forward passes only — no backprop, so Grad-CAM's
gradient-weighted channel combination isn't available there; see
docs/model.md#explainability for the full write-up of why and what this
trades off).

Framework-agnostic on purpose: this module only ever sees numpy arrays and a
`score_fn` callback — it doesn't know or care whether that callback is backed
by an ONNX Runtime session (`onnx_inference.py`, the backend's deployed path)
or a plain PyTorch forward pass (`ml/compare_heatmaps.py`, which runs this
same code against the real model to sanity-check it against true Grad-CAM).
That's what lets both callers produce heatmaps through the exact same
combination/normalisation logic.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
from PIL import Image


def _normalize01(array: np.ndarray) -> np.ndarray:
    array = array - array.min()
    max_val = array.max()
    if max_val > 0:
        array = array / max_val
    return array


def _upsample_to_mask(channel: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """channel: (h, w) raw activation map -> a (H, W) mask in [0, 1], resized
    up to `size` = (width, height) (the resolution `score_fn` expects)."""
    normalized = _normalize01(channel)
    as_image = Image.fromarray((normalized * 255).astype(np.uint8))
    resized = as_image.resize(size, Image.BILINEAR)
    return np.asarray(resized).astype(np.float32) / 255.0


def _softmax(x: np.ndarray) -> np.ndarray:
    shifted = x - x.max()  # numerically stable
    exp = np.exp(shifted)
    return exp / exp.sum()


def compute_score_cam(
    activations: np.ndarray,
    full_score: float,
    score_fn: Callable[[np.ndarray], float],
    mask_size: tuple[int, int],
    top_k: int = 32,
) -> np.ndarray:
    """Computes a Score-CAM attention map from one layer's activations.

    - `activations`: `(C, h, w)` feature maps from the target conv layer
      (the same layer Grad-CAM reads — see `gradcam.get_target_layer`), for
      the full, unmasked image.
    - `full_score`: the model's scalar prediction (bone age, months) for
      that same full image — the reference point every masked prediction is
      compared against.
    - `score_fn`: given a `(H, W)` mask in `[0, 1]` at `mask_size` resolution,
      multiplies it elementwise against the original image and returns the
      model's scalar prediction for that masked image. Must be a
      deterministic forward pass (dropout off) — the stochastic, MC-dropout
      graph is a separate concern (see `onnx_inference.py`).
    - `mask_size`: `(width, height)` of the image `score_fn` expects.
    - `top_k`: only the `top_k` channels with the highest raw activation
      energy are evaluated — Score-CAM normally scores every channel (512
      for a resnet18 `layer4`), which would mean 512 extra forward passes per
      case; restricting to the most active channels keeps this to a bounded,
      interactive-latency cost (configurable via
      `InferenceConfig.score_cam_top_k`, see docs/model.md#explainability).

    Returns an `(h, w)` heatmap in `[0, 1]`, at `activations`' own (small,
    feature-map) resolution — same contract as `GradCAM.__call__` — so
    callers resize/colour it identically either way (see `colormap.py`).

    **Channel weighting (regression, not classification):** bone age has no
    "more positive is better" direction the way a classification logit does,
    so Score-CAM's usual "weight by the raw increase in the target logit"
    doesn't make sense here. Instead, each channel is weighted by how close
    masking the image down to just that channel's region kept the
    prediction to the full image's prediction: `weight_i = softmax_i(-|f(masked_i) - f(full)|)`.
    A channel whose region alone reproduces the full prediction gets the
    largest weight; a channel whose region barely matters (far from
    `full_score`) gets driven toward zero by the softmax. The weighted
    channels are summed, ReLU'd, and renormalised to `[0, 1]`, mirroring
    Grad-CAM's own combination step.
    """
    num_channels = activations.shape[0]
    k = min(top_k, num_channels)

    # Cheap proxy for "this channel probably matters" so we only pay for `k`
    # extra forward passes, not one per channel.
    energies = activations.reshape(num_channels, -1).sum(axis=1)
    top_indices = np.argsort(energies)[::-1][:k]

    masked_scores = np.empty(k, dtype=np.float64)
    native_maps = np.empty((k, activations.shape[1], activations.shape[2]), dtype=np.float32)
    for i, channel_idx in enumerate(top_indices):
        raw_map = activations[channel_idx]
        mask = _upsample_to_mask(raw_map, mask_size)
        masked_scores[i] = score_fn(mask)
        native_maps[i] = _normalize01(raw_map)

    distances = np.abs(masked_scores - full_score)
    weights = _softmax(-distances)

    cam = np.tensordot(weights, native_maps, axes=(0, 0))  # (h, w)
    cam = np.maximum(cam, 0.0)
    return _normalize01(cam).astype(np.float32)
