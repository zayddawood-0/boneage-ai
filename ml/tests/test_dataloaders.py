from __future__ import annotations

import torch

from boneage.config import DataLoaderConfig
from boneage.dataloaders import build_dataloader, build_dataloaders_from_pipeline_config
from boneage.datasets import RSNABoneAgeDataset
from boneage.transforms import build_transforms


def test_build_dataloader_batch_shapes(make_fake_split, column_aliases, small_pipeline_config):
    images_dir, labels_csv, _ = make_fake_split("ad_hoc", n=9)
    transform = build_transforms(
        small_pipeline_config.preprocessing, small_pipeline_config.augmentation, train=False
    )
    dataset = RSNABoneAgeDataset(
        labels_csv=labels_csv,
        images_dir=images_dir,
        column_aliases=column_aliases,
        transform=transform,
    )

    loader = build_dataloader(dataset, DataLoaderConfig(batch_size=4, num_workers=0), shuffle=False)
    images, sexes, bone_ages = next(iter(loader))

    assert images.shape == (4, 3, small_pipeline_config.preprocessing.image_size,
                             small_pipeline_config.preprocessing.image_size)
    assert sexes.shape == (4, 1)
    assert bone_ages.shape == (4,)


def test_build_dataloaders_from_pipeline_config_sizes(small_pipeline_config):
    train_loader, val_loader, test_loader = build_dataloaders_from_pipeline_config(
        small_pipeline_config
    )

    assert len(train_loader.dataset) == 8
    assert len(val_loader.dataset) == 4
    assert len(test_loader.dataset) == 4


def test_build_dataloaders_from_pipeline_config_is_seed_reproducible(small_pipeline_config):
    train_loader_a, _, _ = build_dataloaders_from_pipeline_config(small_pipeline_config)
    first_batch_a = next(iter(train_loader_a))

    train_loader_b, _, _ = build_dataloaders_from_pipeline_config(small_pipeline_config)
    first_batch_b = next(iter(train_loader_b))

    # Same seed, same config -> identical shuffled order and identical
    # (seeded) augmentation output for the first batch.
    assert torch.equal(first_batch_a[2], first_batch_b[2])  # bone_age order matches
    assert torch.equal(first_batch_a[0], first_batch_b[0])  # augmented image tensors match
