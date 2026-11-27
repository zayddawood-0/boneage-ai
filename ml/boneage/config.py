"""Load the ML pipeline config (dataset paths, preprocessing, augmentation).

The dataset location is never hard-coded — it always comes from a config file
(ml/config/config.yaml, copied from ml/config/config.example.yaml), per
docs/data.md and docs/tasks.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
class ModelConfig:
    """See docs/model.md#architecture — exact backbone choice is still [TBD]."""

    backbone: str = "resnet18"
    pretrained: bool = True
    dropout: float = 0.3
    hidden_dim: int = 128


@dataclass(frozen=True)
class TrainingConfig:
    """See docs/model.md#training-plan — hyperparameters are still [TBD]."""

    epochs: int = 50
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    lr_scheduler: str = "cosine"  # "cosine" or "plateau"
    early_stopping_patience: int = 5
    mixed_precision: bool = True  # only takes effect when a CUDA GPU is available
    checkpoint_dir: Path = field(default_factory=lambda: Path("ml/checkpoints"))
    log_every_n_steps: int = 10


@dataclass(frozen=True)
class EvaluationConfig:
    """See docs/model.md#evaluation-metrics.

    `age_band_edges_months` are bucket boundaries for the MAE-by-age-band
    breakdown, not a clinical claim — the real boundaries are still [TBD]
    (see docs/model.md), this is just a placeholder bucketing so
    evaluate.py has something to group by.
    """

    age_band_edges_months: list[float] = field(
        default_factory=lambda: [0.0, 60.0, 120.0, 180.0, 240.0]
    )
    within_months_threshold: float = 12.0
    output_dir: Path = field(default_factory=lambda: Path("ml/results"))


@dataclass(frozen=True)
class InferenceConfig:
    """See docs/model.md#uncertainty-approach — exact N is still [TBD]."""

    mc_dropout_passes: int = 20
    # Score-CAM's top-k channel limit (ONNX inference path only — see
    # docs/model.md#explainability and ml/boneage/score_cam.py). Exact
    # Grad-CAM's channel count (every channel of the target layer, e.g. 512
    # for resnet18's layer4) would mean one extra forward pass per channel;
    # this caps it.
    score_cam_top_k: int = 32


@dataclass(frozen=True)
class PipelineConfig:
    seed: int
    data: DataConfig
    preprocessing: PreprocessingConfig
    augmentation: AugmentationConfig
    dataloader: DataLoaderConfig
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)


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

    model_raw = raw.get("model", {})
    model_cfg = ModelConfig(
        backbone=model_raw.get("backbone", ModelConfig.backbone),
        pretrained=model_raw.get("pretrained", ModelConfig.pretrained),
        dropout=model_raw.get("dropout", ModelConfig.dropout),
        hidden_dim=model_raw.get("hidden_dim", ModelConfig.hidden_dim),
    )

    training_raw = raw.get("training", {})
    default_training = TrainingConfig()
    training_cfg = TrainingConfig(
        epochs=training_raw.get("epochs", default_training.epochs),
        learning_rate=training_raw.get("learning_rate", default_training.learning_rate),
        weight_decay=training_raw.get("weight_decay", default_training.weight_decay),
        lr_scheduler=training_raw.get("lr_scheduler", default_training.lr_scheduler),
        early_stopping_patience=training_raw.get(
            "early_stopping_patience", default_training.early_stopping_patience
        ),
        mixed_precision=training_raw.get("mixed_precision", default_training.mixed_precision),
        checkpoint_dir=Path(training_raw.get("checkpoint_dir", default_training.checkpoint_dir)),
        log_every_n_steps=training_raw.get(
            "log_every_n_steps", default_training.log_every_n_steps
        ),
    )

    eval_raw = raw.get("evaluation", {})
    default_eval = EvaluationConfig()
    evaluation_cfg = EvaluationConfig(
        age_band_edges_months=list(
            eval_raw.get("age_band_edges_months", default_eval.age_band_edges_months)
        ),
        within_months_threshold=eval_raw.get(
            "within_months_threshold", default_eval.within_months_threshold
        ),
        output_dir=Path(eval_raw.get("output_dir", default_eval.output_dir)),
    )

    inference_raw = raw.get("inference", {})
    inference_cfg = InferenceConfig(
        mc_dropout_passes=inference_raw.get(
            "mc_dropout_passes", InferenceConfig.mc_dropout_passes
        ),
        score_cam_top_k=inference_raw.get(
            "score_cam_top_k", InferenceConfig.score_cam_top_k
        ),
    )

    return PipelineConfig(
        seed=raw["seed"],
        data=data_cfg,
        preprocessing=preprocessing_cfg,
        augmentation=augmentation_cfg,
        dataloader=dataloader_cfg,
        model=model_cfg,
        training=training_cfg,
        evaluation=evaluation_cfg,
        inference=inference_cfg,
    )
