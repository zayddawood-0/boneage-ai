from __future__ import annotations

import json
from pathlib import Path

from boneage.dataloaders import build_dataloaders_from_pipeline_config
from boneage.evaluation import (
    EvaluationResult,
    evaluate_model,
    load_checkpoint,
    save_results_json,
    save_scatter_plot,
)
from boneage.model import BoneAgeModel
from boneage.training import train_model


def test_evaluate_model_output_format(small_pipeline_config):
    model = BoneAgeModel(small_pipeline_config.model)
    _, val_loader, _ = build_dataloaders_from_pipeline_config(small_pipeline_config)

    result = evaluate_model(
        model,
        val_loader,
        split="val",
        age_band_edges_months=small_pipeline_config.evaluation.age_band_edges_months,
        within_months_threshold=small_pipeline_config.evaluation.within_months_threshold,
        device="cpu",
    )

    assert isinstance(result, EvaluationResult)
    assert result.split == "val"
    assert result.n_samples == 4  # fixture's val split size
    assert result.mae_overall >= 0
    assert 0.0 <= result.percent_within_threshold <= 100.0
    assert result.within_threshold_months == 12.0

    # Only sexes actually present should show a real number; any absent
    # sex maps to None rather than being silently dropped.
    assert set(result.mae_by_sex) <= {"male", "female"}
    for mae in result.mae_by_sex.values():
        assert mae is None or mae >= 0

    for mae in result.mae_by_age_band.values():
        assert mae is None or mae >= 0

    assert len(result.predictions) == result.n_samples
    assert len(result.targets) == result.n_samples


def test_evaluate_model_after_training_end_to_end(small_pipeline_config):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")
    model, checkpoint_meta = load_checkpoint(summary.checkpoint_path, device="cpu")

    assert checkpoint_meta["epoch"] == 1

    _, val_loader, test_loader = build_dataloaders_from_pipeline_config(small_pipeline_config)
    result = evaluate_model(
        model,
        test_loader,
        split="test",
        age_band_edges_months=small_pipeline_config.evaluation.age_band_edges_months,
        within_months_threshold=small_pipeline_config.evaluation.within_months_threshold,
        device="cpu",
    )

    assert result.n_samples == 4  # fixture's test split size
    assert result.mae_overall >= 0


def test_save_results_json_writes_valid_json(tmp_path, small_pipeline_config):
    model = BoneAgeModel(small_pipeline_config.model)
    _, val_loader, _ = build_dataloaders_from_pipeline_config(small_pipeline_config)
    result = evaluate_model(
        model,
        val_loader,
        split="val",
        age_band_edges_months=small_pipeline_config.evaluation.age_band_edges_months,
        within_months_threshold=small_pipeline_config.evaluation.within_months_threshold,
        device="cpu",
    )

    output_path = tmp_path / "nested" / "val_results.json"
    save_results_json(result, output_path)

    assert output_path.exists()
    with output_path.open() as f:
        data = json.load(f)
    assert data["split"] == "val"
    assert data["n_samples"] == result.n_samples
    assert "mae_overall_months" in data


def test_save_scatter_plot_writes_image_file(tmp_path, small_pipeline_config):
    model = BoneAgeModel(small_pipeline_config.model)
    _, val_loader, _ = build_dataloaders_from_pipeline_config(small_pipeline_config)
    result = evaluate_model(
        model,
        val_loader,
        split="val",
        age_band_edges_months=small_pipeline_config.evaluation.age_band_edges_months,
        within_months_threshold=small_pipeline_config.evaluation.within_months_threshold,
        device="cpu",
    )

    output_path = tmp_path / "plots" / "val_scatter.png"
    save_scatter_plot(result, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
