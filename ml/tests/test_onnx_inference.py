from __future__ import annotations

import numpy as np
from PIL import Image

from boneage.inference import load_checkpoint, predict_single_image
from boneage.model import set_mc_dropout_mode
from boneage.onnx_export import export_to_onnx
from boneage.onnx_inference import predict_single_image_onnx
from boneage.training import train_model


def _train_export_and_image(small_pipeline_config, make_fake_split, tmp_path, split_name, seed):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")
    onnx_dir = export_to_onnx(summary.checkpoint_path, small_pipeline_config, tmp_path / "onnx")

    images_dir, _, df = make_fake_split(split_name, n=1, seed=seed)
    image_path = images_dir / f"{df.iloc[0]['id']}.png"
    return summary, onnx_dir, image_path


def test_onnx_predict_returns_age_uncertainty_and_heatmap(
    small_pipeline_config, make_fake_split, tmp_path
):
    _, onnx_dir, image_path = _train_export_and_image(
        small_pipeline_config, make_fake_split, tmp_path, "onnx_infer", 200
    )

    result = predict_single_image_onnx(
        onnx_dir.metadata.parent,
        image_path,
        sex_is_male=True,
        mc_dropout_passes=small_pipeline_config.inference.mc_dropout_passes,
    )

    assert isinstance(result.bone_age_months, float)
    assert isinstance(result.uncertainty_months, float)
    assert result.uncertainty_months >= 0.0
    assert len(result.mc_dropout_samples) == small_pipeline_config.inference.mc_dropout_passes

    size = small_pipeline_config.preprocessing.image_size
    assert isinstance(result.heatmap_image, Image.Image)
    assert result.heatmap_image.size == (size, size)
    assert result.heatmap_image.mode == "RGB"

    assert isinstance(result.plain_image, Image.Image)
    assert result.plain_image.size == (size, size)
    assert result.plain_image.mode == "RGB"

    assert isinstance(result.heatmap_layer, Image.Image)
    assert result.heatmap_layer.size == (size, size)
    assert result.heatmap_layer.mode == "RGBA"


def test_mc_dropout_passes_count_is_configurable(small_pipeline_config, make_fake_split, tmp_path):
    _, onnx_dir, image_path = _train_export_and_image(
        small_pipeline_config, make_fake_split, tmp_path, "onnx_infer2", 201
    )

    result = predict_single_image_onnx(
        onnx_dir.metadata.parent, image_path, sex_is_male=False, mc_dropout_passes=9
    )

    assert len(result.mc_dropout_samples) == 9


def test_mc_dropout_samples_actually_vary(small_pipeline_config, make_fake_split, tmp_path):
    # If the numpy-side dropout masking silently did nothing, every sample
    # would be identical — this is the empirical check that MC-dropout
    # really is stochastic on the ONNX path (see onnx_inference.py's
    # module docstring for why it isn't done via ONNX Runtime's own Dropout
    # training-mode behaviour).
    _, onnx_dir, image_path = _train_export_and_image(
        small_pipeline_config, make_fake_split, tmp_path, "onnx_infer3", 202
    )

    result = predict_single_image_onnx(
        onnx_dir.metadata.parent, image_path, sex_is_male=True, mc_dropout_passes=20
    )

    assert len(set(result.mc_dropout_samples)) > 1


def test_deterministic_score_matches_real_torch_model(small_pipeline_config, make_fake_split, tmp_path):
    summary, onnx_dir, image_path = _train_export_and_image(
        small_pipeline_config, make_fake_split, tmp_path, "onnx_infer4", 203
    )
    model, _ = load_checkpoint(summary.checkpoint_path, device="cpu")
    set_mc_dropout_mode(model, False)

    import torch

    from boneage.transforms import build_transforms

    transform = build_transforms(small_pipeline_config.preprocessing, augmentation_cfg=None, train=False)
    image_tensor = transform(Image.open(image_path).convert("L")).unsqueeze(0)
    sex_tensor = torch.tensor([[1.0]])
    with torch.no_grad():
        torch_pred = model(image_tensor, sex_tensor).item()

    # The ONNX path's full-image Score-CAM reference score is the same
    # deterministic (dropout-off) forward pass as the real model's.
    from boneage.onnx_inference import OnnxModel

    onnx_model = OnnxModel(onnx_dir.metadata.parent)
    image_array = np.asarray(image_tensor.numpy(), dtype=np.float32)
    features, _ = onnx_model.run_backbone(image_array)
    combined = np.concatenate([features, np.array([[1.0]], dtype=np.float32)], axis=1)
    onnx_pred = onnx_model.run_head(combined)

    assert np.isclose(onnx_pred, torch_pred, atol=1e-4)


def test_onnx_path_runs_without_ever_importing_torch(small_pipeline_config, make_fake_split, tmp_path):
    # Export still needs torch (it's a training-time step), but exercising
    # predict_single_image_onnx afterwards must not require it — that's the
    # entire point of this module (see docs/architecture.md#deployment-notes).
    _, onnx_dir, image_path = _train_export_and_image(
        small_pipeline_config, make_fake_split, tmp_path, "onnx_infer5", 204
    )

    import subprocess
    import sys
    from pathlib import Path

    ml_dir = Path(__file__).resolve().parents[1]
    script = (
        "import sys; sys.path.insert(0, r'%s'); "
        "assert 'torch' not in sys.modules; "
        "from boneage.onnx_inference import predict_single_image_onnx; "
        "assert 'torch' not in sys.modules, 'importing onnx_inference pulled in torch'; "
        "result = predict_single_image_onnx(r'%s', r'%s', sex_is_male=True, mc_dropout_passes=2); "
        "assert 'torch' not in sys.modules, 'running predict_single_image_onnx pulled in torch'; "
        "print('OK', result.bone_age_months)"
    ) % (ml_dir, onnx_dir.metadata.parent, image_path)

    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK" in completed.stdout
