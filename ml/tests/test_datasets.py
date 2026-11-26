from __future__ import annotations

import torch

from boneage.config import AugmentationConfig, PreprocessingConfig
from boneage.datasets import RSNABoneAgeDataset
from boneage.transforms import build_transforms


def _eval_transform(image_size: int = 64):
    preprocessing = PreprocessingConfig(
        image_size=image_size,
        normalize_mean=[0.485, 0.456, 0.406],
        normalize_std=[0.229, 0.224, 0.225],
    )
    augmentation = AugmentationConfig(
        rotation_degrees=10,
        translate_frac=0.05,
        zoom_range=(0.95, 1.05),
        brightness=0.2,
        contrast=0.2,
    )
    return build_transforms(preprocessing, augmentation, train=False)


def test_dataset_length_matches_csv_row_count(make_fake_split, column_aliases):
    images_dir, labels_csv, df = make_fake_split("train", n=7)

    dataset = RSNABoneAgeDataset(
        labels_csv=labels_csv,
        images_dir=images_dir,
        column_aliases=column_aliases,
        transform=_eval_transform(),
    )

    assert len(dataset) == len(df) == 7


def test_dataset_item_shapes_and_dtypes(make_fake_split, column_aliases):
    images_dir, labels_csv, _ = make_fake_split("train", n=3)

    dataset = RSNABoneAgeDataset(
        labels_csv=labels_csv,
        images_dir=images_dir,
        column_aliases=column_aliases,
        transform=_eval_transform(image_size=48),
    )

    image, sex, bone_age = dataset[0]

    assert isinstance(image, torch.Tensor)
    assert image.shape == (3, 48, 48)
    assert image.dtype == torch.float32

    assert sex.shape == (1,)
    assert sex.dtype == torch.float32
    assert sex.item() in (0.0, 1.0)

    assert bone_age.dtype == torch.float32
    assert bone_age.ndim == 0


def test_dataset_sex_matches_csv_male_flag(make_fake_split, column_aliases):
    images_dir, labels_csv, df = make_fake_split("train", n=5)

    dataset = RSNABoneAgeDataset(
        labels_csv=labels_csv,
        images_dir=images_dir,
        column_aliases=column_aliases,
        transform=_eval_transform(),
    )

    for idx in range(len(dataset)):
        _, sex, _ = dataset[idx]
        expected = float(bool(df.iloc[idx]["male"]))
        assert sex.item() == expected


def test_dataset_bone_age_matches_csv_value(make_fake_split, column_aliases):
    images_dir, labels_csv, df = make_fake_split("train", n=4)

    dataset = RSNABoneAgeDataset(
        labels_csv=labels_csv,
        images_dir=images_dir,
        column_aliases=column_aliases,
        transform=_eval_transform(),
    )

    for idx in range(len(dataset)):
        _, _, bone_age = dataset[idx]
        assert bone_age.item() == df.iloc[idx]["boneage"]


def test_dataset_without_transform_returns_pil_image(make_fake_split, column_aliases):
    images_dir, labels_csv, _ = make_fake_split("train", n=2)

    dataset = RSNABoneAgeDataset(
        labels_csv=labels_csv,
        images_dir=images_dir,
        column_aliases=column_aliases,
        transform=None,
    )

    image, _, _ = dataset[0]
    assert image.mode == "L"  # grayscale handling applied even without a transform
