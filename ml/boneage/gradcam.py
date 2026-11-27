"""Grad-CAM explainability for the bone age model.

See docs/model.md#explainability — heatmap is rendered with the inferno-style
colour scale used throughout the UI (see docs/design.md#design-tokens).
"""
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from torch import nn

from .colormap import heatmap_layer_image, overlay_heatmap_on_image  # noqa: F401 - re-exported
from .model import BoneAgeModel


def get_target_layer(model: BoneAgeModel) -> nn.Module:
    """The backbone's last convolutional block — the layer whose activations
    both Grad-CAM (here) and Score-CAM (`score_cam.py`, via `onnx_export.py`)
    read, for the same reason: it's the finest-resolution feature map that
    still reflects high-level, whole-hand structure.
    """
    backbone_name = model.config.backbone
    if backbone_name.startswith("resnet"):
        return model.backbone.layer4
    if backbone_name.startswith("efficientnet"):
        return model.backbone.features[-1]
    raise ValueError(f"No explainability target layer known for backbone {backbone_name!r}")


class GradCAM:
    """Hooks a backbone's last conv layer to compute a Grad-CAM heatmap.

    Use with the model in plain eval mode (dropout off) for a deterministic
    explanation — MC dropout (for uncertainty) and Grad-CAM (for
    explainability) are separate passes, see `boneage.inference`.
    """

    def __init__(self, model: BoneAgeModel) -> None:
        self.model = model
        self.target_layer = get_target_layer(model)
        self._activations: torch.Tensor | None = None
        self._gradients: torch.Tensor | None = None
        self._fwd_handle = self.target_layer.register_forward_hook(self._save_activation)
        self._bwd_handle = self.target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, inputs, output) -> None:
        self._activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output) -> None:
        self._gradients = grad_output[0].detach()

    def __call__(self, image: torch.Tensor, sex: torch.Tensor) -> np.ndarray:
        """`image`: (1, 3, H, W), `sex`: (1, 1). Returns a (h, w) heatmap in [0, 1]
        at the backbone's feature-map resolution (caller resizes to the image)."""
        self.model.zero_grad(set_to_none=True)
        prediction = self.model(image, sex)
        prediction.sum().backward()

        if self._activations is None or self._gradients is None:
            raise RuntimeError("Grad-CAM hooks did not fire — check the target layer.")

        weights = self._gradients.mean(dim=(2, 3), keepdim=True)  # (1, C, 1, 1)
        cam = torch.relu((weights * self._activations).sum(dim=1)).squeeze(0)  # (h, w)

        cam = cam - cam.min()
        max_val = cam.max()
        if max_val > 0:
            cam = cam / max_val
        return cam.cpu().numpy()

    def close(self) -> None:
        self._fwd_handle.remove()
        self._bwd_handle.remove()

    def __enter__(self) -> "GradCAM":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


#  `overlay_heatmap_on_image` and `heatmap_layer_image` now live in
#  `colormap.py` (imported above) — shared, framework-agnostic rendering code
#  used by both this (PyTorch) Grad-CAM path and the ONNX Score-CAM path in
#  `score_cam.py`, so the two methods produce pixel-identical colouring for
#  the side-by-side comparison in `ml/compare_heatmaps.py`.
