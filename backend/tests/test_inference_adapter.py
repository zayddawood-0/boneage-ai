"""InferenceAdapter: mock fallback when no checkpoint exists, and the real
path when one does (trains a tiny throwaway checkpoint via ml.boneage, the
same way ml/tests/conftest.py does, so this never touches real RSNA data).
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.inference_adapter import MOCK_UNCERTAINTY_MONTHS, InferenceAdapter


def _write_fake_image(path) -> None:
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 256, size=(300, 260), dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(path)


def test_mock_predictor_used_when_no_checkpoint_exists(tmp_path):
    image_path = tmp_path / "xray.png"
    _write_fake_image(image_path)

    adapter = InferenceAdapter(
        checkpoint_path=tmp_path / "does_not_exist.pt", ml_config_path=tmp_path / "unused.yaml"
    )

    assert adapter.is_real is False

    result = adapter.predict(image_path, sex_is_male=True)

    assert result.source == "mock"
    assert result.uncertainty_months == MOCK_UNCERTAINTY_MONTHS
    assert 0 < result.bone_age_months < 300
    assert result.heatmap_image.mode == "RGB"


def test_mock_predictor_is_deterministic_for_same_image_and_sex(tmp_path):
    image_path = tmp_path / "xray.png"
    _write_fake_image(image_path)
    adapter = InferenceAdapter(checkpoint_path=tmp_path / "missing.pt")

    first = adapter.predict(image_path, sex_is_male=False)
    second = adapter.predict(image_path, sex_is_male=False)

    assert first.bone_age_months == second.bone_age_months


def test_real_predictor_used_once_a_checkpoint_exists(tmp_path):
    # Train a tiny, throwaway checkpoint on a fake dataset — exactly the
    # pattern ml/tests use — purely to exercise the "real" branch honestly,
    # without needing the actual RSNA dataset or a pretrained-weights download.
    import sys
    from pathlib import Path

    ml_dir = Path(__file__).resolve().parents[2] / "ml"
    if str(ml_dir) not in sys.path:
        sys.path.insert(0, str(ml_dir))

    from boneage.config import (
        AugmentationConfig,
        DataConfig,
        DataLoaderConfig,
        EvaluationConfig,
        InferenceConfig,
        ModelConfig,
        PipelineConfig,
        PreprocessingConfig,
        SplitPaths,
        TrainingConfig,
    )
    from boneage.training import train_model

    column_aliases = {
        "id": ["id"],
        "boneage": ["boneage"],
        "male": ["male"],
    }

    def _make_split(name: str, n: int):
        rng = np.random.default_rng(hash(name) % (2**32))
        images_dir = tmp_path / f"{name}_images"
        images_dir.mkdir()
        import pandas as pd

        rows = []
        for i in range(n):
            img_id = f"{name}_{i}"
            arr = rng.integers(0, 256, size=(120, 100), dtype=np.uint8)
            Image.fromarray(arr, mode="L").save(images_dir / f"{img_id}.png")
            rows.append(
                {"id": img_id, "boneage": float(rng.integers(12, 216)), "male": bool(rng.integers(0, 2))}
            )
        df = pd.DataFrame(rows)
        labels_csv = tmp_path / f"{name}_labels.csv"
        df.to_csv(labels_csv, index=False)
        return images_dir, labels_csv

    train_images, train_csv = _make_split("train", 6)
    val_images, val_csv = _make_split("val", 4)
    test_images, test_csv = _make_split("test", 4)

    pipeline_config = PipelineConfig(
        seed=0,
        data=DataConfig(
            train=SplitPaths(train_images, train_csv),
            val=SplitPaths(val_images, val_csv),
            test=SplitPaths(test_images, test_csv),
            column_aliases=column_aliases,
        ),
        preprocessing=PreprocessingConfig(
            image_size=64, normalize_mean=[0.485, 0.456, 0.406], normalize_std=[0.229, 0.224, 0.225]
        ),
        augmentation=AugmentationConfig(
            rotation_degrees=5, translate_frac=0.02, zoom_range=(0.98, 1.02), brightness=0.1, contrast=0.1
        ),
        dataloader=DataLoaderConfig(batch_size=2, num_workers=0),
        model=ModelConfig(backbone="resnet18", pretrained=False, dropout=0.3, hidden_dim=8),
        training=TrainingConfig(
            epochs=1,
            learning_rate=1e-3,
            weight_decay=0.0,
            lr_scheduler="cosine",
            early_stopping_patience=1,
            mixed_precision=False,
            checkpoint_dir=tmp_path / "checkpoints",
            log_every_n_steps=1,
        ),
        evaluation=EvaluationConfig(output_dir=tmp_path / "results"),
        inference=InferenceConfig(mc_dropout_passes=2),
    )

    summary = train_model(pipeline_config, max_epochs=1, device="cpu")

    # Write a minimal ml-style config.yaml pointing at the same preprocessing
    # settings, so InferenceAdapter can load it the same way it would for a
    # real trained checkpoint.
    import yaml

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "seed": 0,
                "data": {
                    "rsna": {
                        "train": {"images_dir": str(train_images), "labels_csv": str(train_csv)},
                        "val": {"images_dir": str(val_images), "labels_csv": str(val_csv)},
                        "test": {"images_dir": str(test_images), "labels_csv": str(test_csv)},
                    },
                    "column_aliases": column_aliases,
                    "image_extension": ".png",
                },
                "preprocessing": {
                    "image_size": 64,
                    "normalize_mean": [0.485, 0.456, 0.406],
                    "normalize_std": [0.229, 0.224, 0.225],
                },
                "augmentation": {
                    "rotation_degrees": 5,
                    "translate_frac": 0.02,
                    "zoom_range": [0.98, 1.02],
                    "brightness": 0.1,
                    "contrast": 0.1,
                },
                "dataloader": {"batch_size": 2, "num_workers": 0},
            }
        )
    )

    adapter = InferenceAdapter(checkpoint_path=summary.checkpoint_path, ml_config_path=config_path)
    assert adapter.is_real is True

    image_path = tmp_path / "predict_me.png"
    _write_fake_image(image_path)

    result = adapter.predict(image_path, sex_is_male=True, mc_dropout_passes=2)

    assert result.source == "real"
    assert isinstance(result.bone_age_months, float)
    assert result.uncertainty_months >= 0.0
    assert result.heatmap_image.mode == "RGB"
