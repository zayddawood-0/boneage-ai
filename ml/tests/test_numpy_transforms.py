"""numpy_transforms.py must produce numerically identical output to the real
(PyTorch) eval-time pipeline in transforms.py — it's a torch-free duplicate
specifically so the ONNX inference path never imports torch (see
numpy_transforms.py's module docstring). This test is the one place that
checks the duplication stayed faithful.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from boneage.config import PreprocessingConfig
from boneage.numpy_transforms import preprocess_to_numpy
from boneage.transforms import build_transforms


def _fake_image() -> Image.Image:
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 256, size=(90, 70), dtype=np.uint8)
    return Image.fromarray(arr, mode="L")


def test_numpy_preprocessing_matches_torch_preprocessing():
    image = _fake_image()
    cfg = PreprocessingConfig(
        image_size=32, normalize_mean=[0.485, 0.456, 0.406], normalize_std=[0.229, 0.224, 0.225]
    )

    torch_transform = build_transforms(cfg, augmentation_cfg=None, train=False)
    torch_out = torch_transform(image).numpy()[np.newaxis, ...]  # (1, 3, H, W)

    numpy_out = preprocess_to_numpy(image, cfg.image_size, cfg.normalize_mean, cfg.normalize_std)

    assert numpy_out.shape == torch_out.shape
    assert np.allclose(numpy_out, torch_out, atol=1e-5)


def test_output_shape_and_dtype():
    image = _fake_image()
    out = preprocess_to_numpy(image, image_size=48, normalize_mean=[0.5] * 3, normalize_std=[0.5] * 3)

    assert out.shape == (1, 3, 48, 48)
    assert out.dtype == np.float32
