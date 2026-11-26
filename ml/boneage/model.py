"""Bone age regression model: pretrained CNN backbone + sex concatenated into the head.

See docs/model.md#architecture. Backbone choice is still `[TBD]` per that doc —
`resnet18` is the default here because it's small and fast to iterate on for a
hackathon; `efficientnet_b0` is also available via `ModelConfig.backbone`.
"""
from __future__ import annotations

import torch
from torch import nn
from torchvision import models

from .config import ModelConfig

_SUPPORTED_BACKBONES = ("resnet18", "resnet34", "efficientnet_b0")


def _build_backbone(name: str, pretrained: bool) -> tuple[nn.Module, int]:
    """Returns `(feature_extractor, feature_dim)` with the classifier head removed."""
    if name == "resnet18":
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        net = models.resnet18(weights=weights)
        feature_dim = net.fc.in_features
        net.fc = nn.Identity()
        return net, feature_dim

    if name == "resnet34":
        weights = models.ResNet34_Weights.DEFAULT if pretrained else None
        net = models.resnet34(weights=weights)
        feature_dim = net.fc.in_features
        net.fc = nn.Identity()
        return net, feature_dim

    if name == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        net = models.efficientnet_b0(weights=weights)
        feature_dim = net.classifier[1].in_features
        net.classifier = nn.Identity()
        return net, feature_dim

    raise ValueError(f"Unknown backbone {name!r}; supported: {_SUPPORTED_BACKBONES}")


class BoneAgeModel(nn.Module):
    """CNN backbone -> image features; concatenated with sex -> regression head.

    Dropout layers live in the regression head so MC dropout works at
    inference time (see docs/model.md#uncertainty-approach and
    `boneage.inference`): call `set_mc_dropout_mode(model, True)` before
    running multiple stochastic forward passes, instead of `model.train()`
    (which would also re-enable BatchNorm batch statistics — wrong for
    single-image inference).
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        self.backbone, feature_dim = _build_backbone(
            self.config.backbone, self.config.pretrained
        )

        self.head = nn.Sequential(
            nn.Dropout(self.config.dropout),
            nn.Linear(feature_dim + 1, self.config.hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.hidden_dim, 1),
        )

    def forward(self, image: torch.Tensor, sex: torch.Tensor) -> torch.Tensor:
        """`image`: (B, 3, H, W). `sex`: (B, 1). Returns (B,) predicted bone age."""
        features = self.backbone(image)
        if features.ndim > 2:
            features = torch.flatten(features, 1)
        combined = torch.cat([features, sex], dim=1)
        return self.head(combined).squeeze(-1)


def set_mc_dropout_mode(model: nn.Module, enabled: bool) -> None:
    """Put the model in eval mode (frozen BatchNorm) but with Dropout layers
    forced into train mode, so repeated forward passes are stochastic only
    in the dropout — the MC dropout technique described in
    docs/model.md#uncertainty-approach.
    """
    model.eval()
    if not enabled:
        return
    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.train()
