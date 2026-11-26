from __future__ import annotations

from PIL import Image

from boneage.inference import load_checkpoint, predict, predict_single_image
from boneage.training import train_model


def test_predict_single_image_returns_age_uncertainty_and_heatmap(
    small_pipeline_config, make_fake_split
):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")
    model, _ = load_checkpoint(summary.checkpoint_path, device="cpu")

    images_dir, _, df = make_fake_split("infer", n=1, seed=99)
    image_path = images_dir / f"{df.iloc[0]['id']}.png"

    result = predict_single_image(
        model,
        image_path,
        sex_is_male=True,
        preprocessing_config=small_pipeline_config.preprocessing,
        mc_dropout_passes=small_pipeline_config.inference.mc_dropout_passes,
        device="cpu",
    )

    assert isinstance(result.bone_age_months, float)
    assert isinstance(result.uncertainty_months, float)
    assert result.uncertainty_months >= 0.0

    assert len(result.mc_dropout_samples) == small_pipeline_config.inference.mc_dropout_passes

    assert isinstance(result.heatmap_image, Image.Image)
    size = small_pipeline_config.preprocessing.image_size
    assert result.heatmap_image.size == (size, size)
    assert result.heatmap_image.mode == "RGB"

    # Independent layers for the frontend's viewer (see backend
    # /cases/{id}/image and /cases/{id}/heatmap-layer).
    assert isinstance(result.plain_image, Image.Image)
    assert result.plain_image.size == (size, size)
    assert result.plain_image.mode == "RGB"

    assert isinstance(result.heatmap_layer, Image.Image)
    assert result.heatmap_layer.size == (size, size)
    assert result.heatmap_layer.mode == "RGBA"


def test_mc_dropout_passes_count_is_configurable(small_pipeline_config, make_fake_split):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")
    model, _ = load_checkpoint(summary.checkpoint_path, device="cpu")

    images_dir, _, df = make_fake_split("infer2", n=1, seed=100)
    image_path = images_dir / f"{df.iloc[0]['id']}.png"

    result = predict_single_image(
        model,
        image_path,
        sex_is_male=False,
        preprocessing_config=small_pipeline_config.preprocessing,
        mc_dropout_passes=7,
        device="cpu",
    )

    assert len(result.mc_dropout_samples) == 7


def test_predict_one_shot_entry_point_loads_checkpoint_itself(
    small_pipeline_config, make_fake_split
):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")

    images_dir, _, df = make_fake_split("infer3", n=1, seed=101)
    image_path = images_dir / f"{df.iloc[0]['id']}.png"

    result = predict(
        summary.checkpoint_path,
        image_path,
        sex_is_male=True,
        preprocessing_config=small_pipeline_config.preprocessing,
        mc_dropout_passes=4,
        device="cpu",
    )

    assert len(result.mc_dropout_samples) == 4
    assert isinstance(result.bone_age_months, float)


def test_model_left_in_eval_mode_after_predict(small_pipeline_config, make_fake_split):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")
    model, _ = load_checkpoint(summary.checkpoint_path, device="cpu")

    images_dir, _, df = make_fake_split("infer4", n=1, seed=102)
    image_path = images_dir / f"{df.iloc[0]['id']}.png"

    predict_single_image(
        model,
        image_path,
        sex_is_male=True,
        preprocessing_config=small_pipeline_config.preprocessing,
        mc_dropout_passes=3,
        device="cpu",
    )

    # predict_single_image should leave the model deterministic afterwards
    # (dropout off) rather than stuck in MC-dropout mode.
    assert model.training is False
