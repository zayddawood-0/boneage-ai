"""Shared fixtures: generate a small fake RSNA-style dataset for tests.

No real data is used or required — every test in this package runs against
synthetic images/CSVs created on the fly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from boneage.config import (
    AugmentationConfig,
    DataConfig,
    DataLoaderConfig,
    PipelineConfig,
    PreprocessingConfig,
    SplitPaths,
)

DEFAULT_COLUMN_ALIASES = {
    "id": ["id", "Case ID", "case_id"],
    "boneage": ["boneage", "Bone Age", "bone_age"],
    "male": ["male", "Sex", "sex"],
}


@pytest.fixture
def column_aliases() -> dict[str, list[str]]:
    return DEFAULT_COLUMN_ALIASES


@pytest.fixture
def make_fake_split(tmp_path):
    """Factory fixture: build a fake images dir + labels CSV.

    Call as `make_fake_split("train", n=8, seed=1)`; returns
    (images_dir, labels_csv_path, dataframe_used_to_generate_it).
    """

    def _make(name: str, n: int = 6, seed: int = 0) -> tuple:
        rng = np.random.default_rng(seed)
        images_dir = tmp_path / f"{name}_images"
        images_dir.mkdir()

        rows = []
        for i in range(n):
            image_id = f"{name}_{i}"
            # Deliberately non-square, varying sizes, to exercise resize+pad.
            width = int(rng.integers(80, 140))
            height = int(rng.integers(100, 160))
            pixels = rng.integers(0, 256, size=(height, width), dtype=np.uint8)
            Image.fromarray(pixels, mode="L").save(images_dir / f"{image_id}.png")

            rows.append(
                {
                    "id": image_id,
                    "boneage": float(rng.integers(12, 216)),
                    "male": bool(rng.integers(0, 2)),
                }
            )

        df = pd.DataFrame(rows)
        labels_csv = tmp_path / f"{name}_labels.csv"
        df.to_csv(labels_csv, index=False)
        return images_dir, labels_csv, df

    return _make


@pytest.fixture
def small_pipeline_config(make_fake_split, column_aliases) -> PipelineConfig:
    """A full PipelineConfig pointing at fake train/val/test splits."""
    train_images, train_csv, _ = make_fake_split("train", n=8, seed=1)
    val_images, val_csv, _ = make_fake_split("val", n=4, seed=2)
    test_images, test_csv, _ = make_fake_split("test", n=4, seed=3)

    return PipelineConfig(
        seed=42,
        data=DataConfig(
            train=SplitPaths(images_dir=train_images, labels_csv=train_csv),
            val=SplitPaths(images_dir=val_images, labels_csv=val_csv),
            test=SplitPaths(images_dir=test_images, labels_csv=test_csv),
            column_aliases=column_aliases,
            image_extension=".png",
        ),
        preprocessing=PreprocessingConfig(
            image_size=64,
            normalize_mean=[0.485, 0.456, 0.406],
            normalize_std=[0.229, 0.224, 0.225],
        ),
        augmentation=AugmentationConfig(
            rotation_degrees=10,
            translate_frac=0.05,
            zoom_range=(0.95, 1.05),
            brightness=0.2,
            contrast=0.2,
        ),
        dataloader=DataLoaderConfig(batch_size=4, num_workers=0),
    )
