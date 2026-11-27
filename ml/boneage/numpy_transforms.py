"""Torch-free preprocessing for ONNX Runtime inference.

Mirrors the eval-time half of `transforms.py`'s pipeline (`ResizeWithPad` ->
`ToTensor` -> repeat-to-3-channels -> normalize) exactly, but with plain
PIL + numpy only — no `torch`, no `torchvision`. This file exists so
`onnx_inference.py` (the backend's deployed inference path, see
docs/architecture.md#deployment-notes) never pulls torch in: importing even
one name from `transforms.py` would, since that module imports torch/
torchvision at the top level regardless of which symbol is used.

Training-time augmentation (random affine/colour jitter) stays torch-only in
`transforms.py`, since it's only ever used during training, never here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def load_and_orient(image_path: str | Path) -> Image.Image:
    """Open an image, apply EXIF orientation, and convert to grayscale.

    Identical behaviour to `transforms.load_and_orient` — duplicated rather
    than imported so this module stays torch-free (see module docstring).
    """
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    return image.convert("L")


def resize_with_pad(image: Image.Image, size: int, fill: int = 0) -> Image.Image:
    """Resize preserving aspect ratio, then pad to a square `size x size`.

    Identical behaviour to `transforms.ResizeWithPad` — duplicated rather
    than imported so this module stays torch-free (see module docstring).
    """
    width, height = image.size
    scale = size / max(width, height)
    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))
    resized = image.resize((new_width, new_height), Image.BILINEAR)

    pad_width = size - new_width
    pad_height = size - new_height
    left = pad_width // 2
    top = pad_height // 2
    right = pad_width - left
    bottom = pad_height - top
    return ImageOps.expand(resized, border=(left, top, right, bottom), fill=fill)


def preprocess_to_numpy(
    image: Image.Image,
    image_size: int,
    normalize_mean: list[float],
    normalize_std: list[float],
) -> np.ndarray:
    """Grayscale `image` -> a (1, 3, H, W) float32 array, preprocessed the
    same way the real (PyTorch) eval pipeline does: resize+pad, scale to
    [0, 1], repeat to 3 channels, normalize by `normalize_mean`/`normalize_std`.

    This is the exact numeric contract an exported ONNX graph expects as its
    `image` input (see `onnx_export.py`).
    """
    padded = resize_with_pad(image, image_size)
    array = np.asarray(padded.convert("L"), dtype=np.float32) / 255.0  # (H, W) in [0, 1]

    channels = np.stack([array, array, array], axis=0)  # (3, H, W)
    mean = np.array(normalize_mean, dtype=np.float32).reshape(3, 1, 1)
    std = np.array(normalize_std, dtype=np.float32).reshape(3, 1, 1)
    normalized = (channels - mean) / std

    return normalized[np.newaxis, ...].astype(np.float32)  # (1, 3, H, W)
