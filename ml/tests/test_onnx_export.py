"""Checks the three exported ONNX graphs (backbone+activations, head part 1,
head part 2 — see onnx_export.py's module docstring for why three, not one)
are numerically faithful to the real PyTorch model's deterministic (dropout
off) forward pass, and that the backbone's second output really is the same
activations Grad-CAM reads.
"""
from __future__ import annotations

import json

import numpy as np
import onnxruntime as ort
import torch

from boneage.config import InferenceConfig
from boneage.gradcam import GradCAM, get_target_layer
from boneage.inference import load_checkpoint
from boneage.model import set_mc_dropout_mode
from boneage.onnx_export import export_to_onnx
from boneage.training import train_model


def _train_and_export(small_pipeline_config, tmp_path):
    summary = train_model(small_pipeline_config, max_epochs=1, device="cpu")
    out_dir = tmp_path / "onnx"
    paths = export_to_onnx(summary.checkpoint_path, small_pipeline_config, out_dir)
    return summary, paths


def test_export_writes_all_expected_files(small_pipeline_config, tmp_path):
    _, paths = _train_and_export(small_pipeline_config, tmp_path)

    assert paths.backbone.exists()
    assert paths.head_part1.exists()
    assert paths.head_part2.exists()
    assert paths.metadata.exists()


def test_metadata_matches_pipeline_config(small_pipeline_config, tmp_path):
    _, paths = _train_and_export(small_pipeline_config, tmp_path)

    metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
    assert metadata["image_size"] == small_pipeline_config.preprocessing.image_size
    assert metadata["normalize_mean"] == small_pipeline_config.preprocessing.normalize_mean
    assert metadata["backbone"] == small_pipeline_config.model.backbone
    assert metadata["hidden_dim"] == small_pipeline_config.model.hidden_dim
    assert metadata["dropout"] == small_pipeline_config.model.dropout
    assert metadata["score_cam_top_k"] == small_pipeline_config.inference.score_cam_top_k


def test_three_graph_pipeline_matches_torch_deterministic_forward(small_pipeline_config, tmp_path):
    summary, paths = _train_and_export(small_pipeline_config, tmp_path)
    model, _ = load_checkpoint(summary.checkpoint_path, device="cpu")
    set_mc_dropout_mode(model, False)  # dropout off -> deterministic, matches the exported graphs

    image = torch.rand(1, 3, small_pipeline_config.preprocessing.image_size, small_pipeline_config.preprocessing.image_size)
    sex = torch.tensor([[1.0]])

    with torch.no_grad():
        torch_pred = model(image, sex).item()

    backbone_sess = ort.InferenceSession(str(paths.backbone))
    head1_sess = ort.InferenceSession(str(paths.head_part1))
    head2_sess = ort.InferenceSession(str(paths.head_part2))

    features, activations = backbone_sess.run(None, {"image": image.numpy()})
    combined = np.concatenate([features, sex.numpy()], axis=1).astype(np.float32)
    (hidden,) = head1_sess.run(None, {"masked_combined": combined})
    (onnx_pred,) = head2_sess.run(None, {"masked_hidden": hidden})

    assert np.allclose(onnx_pred.reshape(-1)[0], torch_pred, atol=1e-4)
    assert activations.ndim == 4  # (1, C, h, w)


def test_backbone_activations_match_gradcams_target_layer(small_pipeline_config, tmp_path):
    summary, paths = _train_and_export(small_pipeline_config, tmp_path)
    model, _ = load_checkpoint(summary.checkpoint_path, device="cpu")
    set_mc_dropout_mode(model, False)

    image = torch.rand(1, 3, small_pipeline_config.preprocessing.image_size, small_pipeline_config.preprocessing.image_size)
    sex = torch.tensor([[0.0]])

    with GradCAM(model) as cam_fn:
        cam_fn(image, sex)  # populates the hook's captured activations as a side effect
        torch_activations = cam_fn._activations.numpy()  # noqa: SLF001 - test-only introspection

    backbone_sess = ort.InferenceSession(str(paths.backbone))
    _, onnx_activations = backbone_sess.run(None, {"image": image.numpy()})

    assert onnx_activations.shape == torch_activations.shape
    assert np.allclose(onnx_activations, torch_activations, atol=1e-4)


def test_mc_dropout_passes_in_metadata_default_from_config(small_pipeline_config, tmp_path):
    small_pipeline_config = small_pipeline_config  # inference.mc_dropout_passes == 3 by fixture
    _, paths = _train_and_export(small_pipeline_config, tmp_path)
    metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
    assert metadata["mc_dropout_passes"] == 3
