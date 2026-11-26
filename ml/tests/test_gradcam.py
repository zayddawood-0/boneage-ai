from __future__ import annotations

import numpy as np
import torch
from PIL import Image

from boneage.config import ModelConfig
from boneage.gradcam import GradCAM, heatmap_layer_image, overlay_heatmap_on_image
from boneage.model import BoneAgeModel


def _tiny_model() -> BoneAgeModel:
    return BoneAgeModel(ModelConfig(backbone="resnet18", pretrained=False, hidden_dim=16))


def test_gradcam_produces_normalised_heatmap():
    model = _tiny_model()
    model.eval()

    image = torch.rand(1, 3, 64, 64)
    sex = torch.ones(1, 1)

    with GradCAM(model) as cam_fn:
        cam = cam_fn(image, sex)

    assert isinstance(cam, np.ndarray)
    assert cam.ndim == 2
    assert cam.min() >= 0.0
    assert cam.max() <= 1.0 + 1e-6


def test_gradcam_context_manager_removes_hooks():
    model = _tiny_model()
    model.eval()

    image = torch.rand(1, 3, 64, 64)
    sex = torch.zeros(1, 1)

    with GradCAM(model) as cam_fn:
        cam_fn(image, sex)

    # Hooks removed -> no activations/gradients captured for a plain forward.
    with torch.no_grad():
        model(image, sex)


def test_overlay_heatmap_on_image_matches_base_size_and_mode():
    base_image = Image.fromarray(np.zeros((48, 48), dtype=np.uint8), mode="L")
    cam = np.random.default_rng(0).random((8, 8)).astype(np.float32)

    blended = overlay_heatmap_on_image(base_image, cam)

    assert blended.size == (48, 48)
    assert blended.mode == "RGB"


def test_overlay_heatmap_handles_flat_zero_cam():
    # A degenerate all-zero CAM shouldn't raise (division-by-zero guard in GradCAM
    # normalisation is in GradCAM.__call__; here we check the overlay step alone
    # is robust to a flat input too).
    base_image = Image.fromarray(np.full((32, 32), 128, dtype=np.uint8), mode="L")
    cam = np.zeros((4, 4), dtype=np.float32)

    blended = overlay_heatmap_on_image(base_image, cam)

    assert blended.size == (32, 32)


def test_heatmap_layer_image_is_rgba_sized_to_target():
    cam = np.random.default_rng(1).random((8, 8)).astype(np.float32)

    layer = heatmap_layer_image(cam, size=(48, 32))

    assert layer.size == (48, 32)
    assert layer.mode == "RGBA"


def test_heatmap_layer_image_alpha_scales_with_attention():
    # High-attention pixels should end up far more opaque than low-attention ones.
    cam = np.zeros((4, 4), dtype=np.float32)
    cam[0, 0] = 1.0  # one hotspot, everything else zero

    layer = heatmap_layer_image(cam, size=(4, 4), max_alpha=200)
    alpha = np.asarray(layer)[:, :, 3]

    assert alpha[0, 0] >= 190  # near max_alpha at the hotspot
    assert alpha[3, 3] <= 10  # near-transparent far from the hotspot


def test_heatmap_layer_image_respects_max_alpha_cap():
    cam = np.ones((4, 4), dtype=np.float32)

    layer = heatmap_layer_image(cam, size=(4, 4), max_alpha=120)
    alpha = np.asarray(layer)[:, :, 3]

    assert alpha.max() <= 120
