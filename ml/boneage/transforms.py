"""Preprocessing + training-time augmentation for RSNA hand X-rays.

See docs/data.md#preprocessing for the spec this implements.
"""
from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image, ImageOps
from torchvision import transforms as T

from .config import AugmentationConfig, PreprocessingConfig


class ResizeWithPad:
    """Resize preserving aspect ratio, then pad to a square `size x size`.

    Plain resize would distort the hand's proportions; padding keeps the
    aspect ratio intact instead.
    """

    def __init__(self, size: int, fill: int = 0) -> None:
        self.size = size
        self.fill = fill

    def __call__(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        scale = self.size / max(width, height)
        new_width = max(1, round(width * scale))
        new_height = max(1, round(height * scale))
        resized = image.resize((new_width, new_height), Image.BILINEAR)

        pad_width = self.size - new_width
        pad_height = self.size - new_height
        left = pad_width // 2
        top = pad_height // 2
        right = pad_width - left
        bottom = pad_height - top
        return ImageOps.expand(resized, border=(left, top, right, bottom), fill=self.fill)


def load_and_orient(image_path: str | Path) -> Image.Image:
    """Open an image, apply EXIF orientation, and convert to grayscale.

    This only corrects EXIF-tagged rotation and normalises the colour mode
    (some RSNA images are stored as RGB with all channels equal). Full
    automatic hand-orientation correction (ensuring fingers point up,
    regardless of how the film/sensor was oriented) is out of scope for this
    pipeline — see docs/data.md#preprocessing (`[TBD]`).
    """
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    return image.convert("L")


class GrayscaleTo3Channel:
    """Repeat a 1-channel tensor to 3 channels, for the pretrained RGB backbone."""

    def __call__(self, tensor: torch.Tensor) -> torch.Tensor:
        if tensor.shape[0] == 3:
            return tensor
        return tensor.repeat(3, 1, 1)


def build_transforms(
    preprocessing_cfg: PreprocessingConfig,
    augmentation_cfg: AugmentationConfig | None = None,
    train: bool = False,
) -> T.Compose:
    """Build the preprocessing (+ training-time augmentation) pipeline.

    Augmentation is only ever included when `train=True` — validation/test
    transforms never include it. Horizontal flips are deliberately never
    used anywhere: every RSNA image is a left hand, so flipping would turn it
    into a right-hand pose (see docs/data.md#preprocessing).
    """
    steps: list = [ResizeWithPad(preprocessing_cfg.image_size)]

    if train and augmentation_cfg is not None:
        steps.append(
            T.RandomAffine(
                degrees=augmentation_cfg.rotation_degrees,
                translate=(augmentation_cfg.translate_frac, augmentation_cfg.translate_frac),
                scale=augmentation_cfg.zoom_range,
            )
        )
        steps.append(
            T.ColorJitter(
                brightness=augmentation_cfg.brightness,
                contrast=augmentation_cfg.contrast,
            )
        )

    steps.append(T.ToTensor())
    steps.append(GrayscaleTo3Channel())
    steps.append(
        T.Normalize(mean=preprocessing_cfg.normalize_mean, std=preprocessing_cfg.normalize_std)
    )

    return T.Compose(steps)
