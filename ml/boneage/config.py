"""Load the ML pipeline config (dataset paths, preprocessing, augmentation).

The dataset location is never hard-coded — it always comes from a config file
(ml/config/config.yaml, copied from ml/config/config.example.yaml), per
docs/data.md and docs/tasks.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SplitPaths:
    images_dir: Path
    labels_csv: Path


@dataclass(frozen=True)
class DataConfig:
    train: SplitPaths
    val: SplitPaths
    test: SplitPaths
    column_aliases: dict[str, list[str]]
    image_extension: str = ".png"


@dataclass(frozen=True)
class PreprocessingConfig:
    image_size: int
    normalize_mean: list[float]
    normalize_std: list[float]


@dataclass(frozen=True)
class AugmentationConfig:
    rotation_degrees: float
    translate_frac: float
    zoom_range: tuple[float, float]
    brightness: float
    contrast: float


@dataclass(frozen=True)
class DataLoaderConfig:
    batch_size: int
    num_workers: int


@dataclass(frozen=True)
class PipelineConfig:
    seed: int
    data: DataConfig
    preprocessing: PreprocessingConfig
    augmentation: AugmentationConfig
    dataloader: DataLoaderConfig


def _split_paths(raw: dict[str, Any]) -> SplitPaths:
    return SplitPaths(
        images_dir=Path(raw["images_dir"]),
        labels_csv=Path(raw["labels_csv"]),
    )


def load_config(config_path: str | Path) -> PipelineConfig:
    """Parse a YAML config file into a `PipelineConfig`.

    Raises FileNotFoundError if config_path doesn't exist, so callers get a
    clear error instead of silently falling back to made-up defaults for
    dataset location (the dataset path must always come from this file).
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"ML config not found at {config_path}. Copy "
            "ml/config/config.example.yaml to ml/config/config.yaml and fill "
            "in your local dataset paths."
        )

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rsna = raw["data"]["rsna"]
    data_cfg = DataConfig(
        train=_split_paths(rsna["train"]),
        val=_split_paths(rsna["val"]),
        test=_split_paths(rsna["test"]),
        column_aliases=raw["data"]["column_aliases"],
        image_extension=raw["data"].get("image_extension", ".png"),
    )

    prep_raw = raw["preprocessing"]
    preprocessing_cfg = PreprocessingConfig(
        image_size=prep_raw["image_size"],
        normalize_mean=list(prep_raw["normalize_mean"]),
        normalize_std=list(prep_raw["normalize_std"]),
    )

    aug_raw = raw["augmentation"]
    augmentation_cfg = AugmentationConfig(
        rotation_degrees=aug_raw["rotation_degrees"],
        translate_frac=aug_raw["translate_frac"],
        zoom_range=tuple(aug_raw["zoom_range"]),
        brightness=aug_raw["brightness"],
        contrast=aug_raw["contrast"],
    )

    dl_raw = raw["dataloader"]
    dataloader_cfg = DataLoaderConfig(
        batch_size=dl_raw["batch_size"],
        num_workers=dl_raw["num_workers"],
    )

    return PipelineConfig(
        seed=raw["seed"],
        data=data_cfg,
        preprocessing=preprocessing_cfg,
        augmentation=augmentation_cfg,
        dataloader=dataloader_cfg,
    )
