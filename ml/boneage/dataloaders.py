"""DataLoader construction for the RSNA bone age dataset."""
from __future__ import annotations

from torch.utils.data import DataLoader, Dataset

from .config import DataLoaderConfig, PipelineConfig


def build_dataloader(dataset: Dataset, config: DataLoaderConfig, shuffle: bool) -> DataLoader:
    return DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=shuffle,
        num_workers=config.num_workers,
    )


def build_dataloaders_from_pipeline_config(
    pipeline_config: PipelineConfig,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    """Build train/val/test RSNA datasets + dataloaders from a loaded config.

    Seeds the run (see boneage.seed.set_seed) before constructing anything,
    so augmentation and shuffling are reproducible.
    """
    from .datasets import RSNABoneAgeDataset
    from .seed import set_seed
    from .transforms import build_transforms

    set_seed(pipeline_config.seed)

    train_transform = build_transforms(
        pipeline_config.preprocessing, pipeline_config.augmentation, train=True
    )
    eval_transform = build_transforms(
        pipeline_config.preprocessing, pipeline_config.augmentation, train=False
    )

    train_ds = RSNABoneAgeDataset(
        labels_csv=pipeline_config.data.train.labels_csv,
        images_dir=pipeline_config.data.train.images_dir,
        column_aliases=pipeline_config.data.column_aliases,
        transform=train_transform,
        image_extension=pipeline_config.data.image_extension,
    )
    val_ds = RSNABoneAgeDataset(
        labels_csv=pipeline_config.data.val.labels_csv,
        images_dir=pipeline_config.data.val.images_dir,
        column_aliases=pipeline_config.data.column_aliases,
        transform=eval_transform,
        image_extension=pipeline_config.data.image_extension,
    )
    test_ds = RSNABoneAgeDataset(
        labels_csv=pipeline_config.data.test.labels_csv,
        images_dir=pipeline_config.data.test.images_dir,
        column_aliases=pipeline_config.data.column_aliases,
        transform=eval_transform,
        image_extension=pipeline_config.data.image_extension,
    )

    train_loader = build_dataloader(train_ds, pipeline_config.dataloader, shuffle=True)
    val_loader = build_dataloader(val_ds, pipeline_config.dataloader, shuffle=False)
    test_loader = build_dataloader(test_ds, pipeline_config.dataloader, shuffle=False)

    return train_loader, val_loader, test_loader
