"""score_cam.py is framework-agnostic (see its module docstring) — these
tests drive it with a plain numpy `score_fn`, no ONNX Runtime or PyTorch
needed, to check the combination/weighting logic in isolation.
"""
from __future__ import annotations

import numpy as np

from boneage.score_cam import compute_score_cam


def test_output_shape_and_range():
    rng = np.random.default_rng(0)
    activations = rng.random((6, 4, 4)).astype(np.float32)

    def score_fn(mask: np.ndarray) -> float:
        return float(mask.mean())

    cam = compute_score_cam(
        activations, full_score=0.5, score_fn=score_fn, mask_size=(16, 16), top_k=6
    )

    assert cam.shape == (4, 4)
    assert cam.min() >= 0.0
    assert cam.max() <= 1.0 + 1e-6


def test_channel_closest_to_full_score_dominates_the_combination():
    # Two channels: channel 0 is a hotspot in the top-left, channel 1 in the
    # bottom-right. Make score_fn report that masking with channel 0 exactly
    # reproduces the full-image score (distance 0), while channel 1 is far
    # off — channel 0's spatial pattern should dominate the combined cam.
    activations = np.zeros((2, 4, 4), dtype=np.float32)
    activations[0, 0, 0] = 1.0  # channel 0: top-left hotspot
    activations[1, 3, 3] = 1.0  # channel 1: bottom-right hotspot

    full_score = 10.0

    def score_fn(mask: np.ndarray) -> float:
        # mask is the upsampled channel map; channel 0's mask peaks top-left.
        return full_score if mask[0, 0] > 0.5 else 0.0

    cam = compute_score_cam(
        activations, full_score=full_score, score_fn=score_fn, mask_size=(8, 8), top_k=2
    )

    assert cam[0, 0] > cam[3, 3]


def test_top_k_limits_the_number_of_score_fn_calls():
    rng = np.random.default_rng(1)
    activations = rng.random((10, 3, 3)).astype(np.float32)
    calls = {"n": 0}

    def score_fn(mask: np.ndarray) -> float:
        calls["n"] += 1
        return 0.0

    compute_score_cam(activations, full_score=0.0, score_fn=score_fn, mask_size=(12, 12), top_k=4)

    assert calls["n"] == 4


def test_top_k_larger_than_channel_count_uses_every_channel():
    rng = np.random.default_rng(2)
    activations = rng.random((3, 3, 3)).astype(np.float32)
    calls = {"n": 0}

    def score_fn(mask: np.ndarray) -> float:
        calls["n"] += 1
        return 0.0

    compute_score_cam(activations, full_score=0.0, score_fn=score_fn, mask_size=(12, 12), top_k=32)

    assert calls["n"] == 3


def test_flat_activations_do_not_raise():
    activations = np.zeros((4, 4, 4), dtype=np.float32)

    cam = compute_score_cam(
        activations, full_score=0.0, score_fn=lambda m: 0.0, mask_size=(8, 8), top_k=4
    )

    assert cam.shape == (4, 4)
    assert np.all(cam == 0.0)
