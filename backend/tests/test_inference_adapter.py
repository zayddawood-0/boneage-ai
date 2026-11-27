"""InferenceAdapter: mock fallback when no exported ONNX model exists, and
the real (ONNX Runtime) path when one does — trains a tiny throwaway
checkpoint via ml.boneage and exports it, the same pattern ml/tests use, so
this never touches real RSNA data or a real trained model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from app import inference_adapter as inference_adapter_module
from app.inference_adapter import MOCK_UNCERTAINTY_MONTHS, InferenceAdapter

_ML_DIR = Path(__file__).resolve().parents[2] / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


def _write_fake_image(path) -> None:
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 256, size=(300, 260), dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(path)


def test_mock_predictor_used_when_no_onnx_model_exists(tmp_path):
    image_path = tmp_path / "xray.png"
    _write_fake_image(image_path)

    adapter = InferenceAdapter(onnx_dir=tmp_path / "does_not_exist")

    assert adapter.is_real is False

    result = adapter.predict(image_path, sex_is_male=True)

    assert result.source == "mock"
    assert result.uncertainty_months == MOCK_UNCERTAINTY_MONTHS
    assert 0 < result.bone_age_months < 300
    assert result.heatmap_image.mode == "RGB"


def test_mock_predictor_is_deterministic_for_same_image_and_sex(tmp_path):
    image_path = tmp_path / "xray.png"
    _write_fake_image(image_path)
    adapter = InferenceAdapter(onnx_dir=tmp_path / "missing")

    first = adapter.predict(image_path, sex_is_male=False)
    second = adapter.predict(image_path, sex_is_male=False)

    assert first.bone_age_months == second.bone_age_months


def _train_tiny_onnx_model(tmp_path):
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
    from boneage.onnx_export import export_to_onnx
    from boneage.training import train_model

    column_aliases = {"id": ["id"], "boneage": ["boneage"], "male": ["male"]}

    def _make_split(name: str, n: int):
        rng = np.random.default_rng(hash(name) % (2**32))
        images_dir = tmp_path / f"{name}_images"
        images_dir.mkdir()

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
        inference=InferenceConfig(mc_dropout_passes=2, score_cam_top_k=4),
    )

    summary = train_model(pipeline_config, max_epochs=1, device="cpu")
    return export_to_onnx(summary.checkpoint_path, pipeline_config, tmp_path / "onnx")


def test_real_predictor_used_once_an_onnx_model_exists(tmp_path):
    onnx_paths = _train_tiny_onnx_model(tmp_path)

    adapter = InferenceAdapter(onnx_dir=onnx_paths.metadata.parent)
    assert adapter.is_real is True

    image_path = tmp_path / "predict_me.png"
    _write_fake_image(image_path)

    result = adapter.predict(image_path, sex_is_male=True, mc_dropout_passes=2)

    assert result.source == "real"
    assert isinstance(result.bone_age_months, float)
    assert result.uncertainty_months >= 0.0
    assert result.heatmap_image.mode == "RGB"


def test_download_only_attempted_once_per_cold_start(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _fake_download(onnx_dir, download_url):
        calls["n"] += 1

    monkeypatch.setattr(inference_adapter_module, "_download_attempted", False)
    monkeypatch.setattr(inference_adapter_module, "_try_download_onnx_dir", _fake_download)

    onnx_dir = tmp_path / "missing_onnx"
    adapter_one = InferenceAdapter(onnx_dir=onnx_dir)
    adapter_one._onnx_download_url = "https://example.invalid/model.zip"
    adapter_two = InferenceAdapter(onnx_dir=onnx_dir)
    adapter_two._onnx_download_url = "https://example.invalid/model.zip"

    assert adapter_one.is_real is False
    assert adapter_two.is_real is False

    assert calls["n"] == 1
