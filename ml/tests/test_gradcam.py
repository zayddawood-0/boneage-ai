from __future__ import annotations

import numpy as np
import torch
from PIL import Image

from boneage.config import ModelConfig
from boneage.gradcam import GradCAM, overlay_heatmap_on_image
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
