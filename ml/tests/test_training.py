from __future__ import annotations

from pathlib import Path

import torch

from boneage.training import EpochMetrics, TrainingSummary, train_model


def test_smoke_training_run_one_epoch_cpu(small_pipeline_config):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")

    assert isinstance(summary, TrainingSummary)
    assert len(summary.history) == 1
    assert isinstance(summary.history[0], EpochMetrics)
    assert summary.history[0].epoch == 1
    assert summary.history[0].train_mae >= 0
    assert summary.history[0].val_mae >= 0

    assert summary.best_epoch == 1
    assert summary.best_val_mae == summary.history[0].val_mae
    assert summary.stopped_early is False

    assert summary.checkpoint_path is not None
    assert Path(summary.checkpoint_path).exists()


def test_checkpoint_contains_expected_fields(small_pipeline_config):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")

    checkpoint = torch.load(summary.checkpoint_path, map_location="cpu", weights_only=False)

    assert "model_state_dict" in checkpoint
    assert "model_config" in checkpoint
    assert checkpoint["epoch"] == 1
    assert checkpoint["val_mae"] == summary.best_val_mae


def test_training_respects_max_epochs_override(small_pipeline_config):
    # config has epochs=1 already, but early_stopping_patience=1 means a
    # multi-epoch run without improvement would also stop after 1 extra
    # non-improving epoch — here we just check max_epochs is honoured as a cap.
    summary = train_model(small_pipeline_config, max_epochs=2, device="cpu")

    assert len(summary.history) <= 2
    assert all(isinstance(m, EpochMetrics) for m in summary.history)


def test_invalid_epochs_raises(small_pipeline_config):
    import pytest

    with pytest.raises(ValueError):
        train_model(small_pipeline_config, max_epochs=0, device="cpu")
