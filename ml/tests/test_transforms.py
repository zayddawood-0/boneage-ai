from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from torchvision import transforms as T

from boneage.config import AugmentationConfig, PreprocessingConfig
from boneage.transforms import GrayscaleTo3Channel, ResizeWithPad, build_transforms


def _make_image(width: int, height: int, mode: str = "L") -> Image.Image:
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 256, size=(height, width), dtype=np.uint8)
    return Image.fromarray(arr, mode=mode)


def test_resize_with_pad_produces_exact_square_without_distortion():
    image = _make_image(width=200, height=100)  # 2:1 aspect ratio

    padded = ResizeWithPad(size=64)(image)

    assert padded.size == (64, 64)


def test_resize_with_pad_preserves_aspect_ratio_content_area():
    # Wide image: after fitting to 64x64, height should be padded (letterboxed),
    # i.e. the resized content should be narrower than the full square on one axis.
    image = _make_image(width=200, height=50)  # 4:1 aspect ratio

    padded = ResizeWithPad(size=64)(image)
    arr = np.array(padded)

    # Top and bottom rows should be padding (fill=0) since height was the
    # constrained dimension for a wide image.
    assert np.all(arr[0, :] == 0)
    assert np.all(arr[-1, :] == 0)


def test_grayscale_to_3channel_repeats_single_channel():
    tensor = torch.rand(1, 32, 32)

    out = GrayscaleTo3Channel()(tensor)

    assert out.shape == (3, 32, 32)
    assert torch.equal(out[0], out[1])
    assert torch.equal(out[1], out[2])


def test_grayscale_to_3channel_leaves_3channel_tensor_untouched():
    tensor = torch.rand(3, 32, 32)

    out = GrayscaleTo3Channel()(tensor)

    assert torch.equal(out, tensor)


def _preprocessing_cfg(image_size: int = 64) -> PreprocessingConfig:
    return PreprocessingConfig(
        image_size=image_size,
        normalize_mean=[0.485, 0.456, 0.406],
        normalize_std=[0.229, 0.224, 0.225],
    )


def _augmentation_cfg() -> AugmentationConfig:
    return AugmentationConfig(
        rotation_degrees=10,
        translate_frac=0.05,
        zoom_range=(0.95, 1.05),
        brightness=0.2,
        contrast=0.2,
    )


def test_build_transforms_eval_output_shape_and_dtype():
    transform = build_transforms(_preprocessing_cfg(64), _augmentation_cfg(), train=False)
    image = _make_image(width=120, height=90)

    out = transform(image)

    assert out.shape == (3, 64, 64)
    assert out.dtype == torch.float32


def test_build_transforms_eval_excludes_augmentation_ops():
    transform = build_transforms(_preprocessing_cfg(64), _augmentation_cfg(), train=False)

    op_types = [type(step) for step in transform.transforms]

    assert T.RandomAffine not in op_types
    assert T.ColorJitter not in op_types


def test_build_transforms_train_includes_augmentation_ops_but_never_flip():
    transform = build_transforms(_preprocessing_cfg(64), _augmentation_cfg(), train=True)

    op_types = [type(step) for step in transform.transforms]

    assert T.RandomAffine in op_types
    assert T.ColorJitter in op_types
    assert T.RandomHorizontalFlip not in op_types
    assert T.RandomVerticalFlip not in op_types

    # Also check it still runs end-to-end and produces the right shape.
    image = _make_image(width=120, height=90)
    out = transform(image)
    assert out.shape == (3, 64, 64)


def test_build_transforms_without_augmentation_config_skips_augmentation_even_if_train():
    transform = build_transforms(_preprocessing_cfg(64), augmentation_cfg=None, train=True)

    op_types = [type(step) for step in transform.transforms]

    assert T.RandomAffine not in op_types
    assert T.ColorJitter not in op_types
