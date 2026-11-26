from __future__ import annotations

import torch

from boneage.config import ModelConfig
from boneage.model import BoneAgeModel, set_mc_dropout_mode


def _tiny_model_config() -> ModelConfig:
    # pretrained=False -> no network access, no ImageNet weight download.
    return ModelConfig(backbone="resnet18", pretrained=False, dropout=0.5, hidden_dim=16)


def test_forward_pass_output_shape():
    model = BoneAgeModel(_tiny_model_config())
    model.eval()

    batch_size = 5
    images = torch.rand(batch_size, 3, 64, 64)
    sex = torch.randint(0, 2, (batch_size, 1)).float()

    with torch.no_grad():
        out = model(images, sex)

    assert out.shape == (batch_size,)
    assert out.dtype == torch.float32


def test_forward_pass_accepts_different_input_sizes():
    model = BoneAgeModel(_tiny_model_config())
    model.eval()

    for size in (32, 64, 96):
        images = torch.rand(2, 3, size, size)
        sex = torch.zeros(2, 1)
        with torch.no_grad():
            out = model(images, sex)
        assert out.shape == (2,)


def test_model_head_contains_dropout_layers():
    model = BoneAgeModel(_tiny_model_config())
    dropout_layers = [m for m in model.head.modules() if isinstance(m, torch.nn.Dropout)]
    assert len(dropout_layers) >= 1


def test_eval_mode_is_deterministic_across_calls():
    model = BoneAgeModel(_tiny_model_config())
    model.eval()

    images = torch.rand(3, 3, 64, 64)
    sex = torch.ones(3, 1)

    with torch.no_grad():
        out1 = model(images, sex)
        out2 = model(images, sex)

    assert torch.equal(out1, out2)


def test_mc_dropout_mode_produces_stochastic_outputs():
    model = BoneAgeModel(_tiny_model_config())
    set_mc_dropout_mode(model, True)

    images = torch.rand(3, 3, 64, 64)
    sex = torch.ones(3, 1)

    with torch.no_grad():
        out1 = model(images, sex)
        out2 = model(images, sex)

    # With dropout active, repeated forward passes on the same input should
    # (almost certainly) differ — that's the whole point of MC dropout.
    assert not torch.equal(out1, out2)


def test_mc_dropout_mode_false_restores_deterministic_eval():
    model = BoneAgeModel(_tiny_model_config())
    set_mc_dropout_mode(model, True)
    set_mc_dropout_mode(model, False)

    images = torch.rand(3, 3, 64, 64)
    sex = torch.zeros(3, 1)

    with torch.no_grad():
        out1 = model(images, sex)
        out2 = model(images, sex)

    assert torch.equal(out1, out2)


def test_unknown_backbone_raises():
    import pytest

    with pytest.raises(ValueError):
        BoneAgeModel(ModelConfig(backbone="not_a_real_backbone", pretrained=False))
