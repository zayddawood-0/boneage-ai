"""Grad-CAM explainability for the bone age model.

See docs/model.md#explainability — heatmap is rendered with the inferno-style
colour scale used throughout the UI (see docs/design.md#design-tokens).
"""
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from torch import nn

from .model import BoneAgeModel


def _get_target_layer(model: BoneAgeModel) -> nn.Module:
    backbone_name = model.config.backbone
    if backbone_name.startswith("resnet"):
        return model.backbone.layer4
    if backbone_name.startswith("efficientnet"):
        return model.backbone.features[-1]
    raise ValueError(f"No Grad-CAM target layer known for backbone {backbone_name!r}")


class GradCAM:
    """Hooks a backbone's last conv layer to compute a Grad-CAM heatmap.

    Use with the model in plain eval mode (dropout off) for a deterministic
    explanation — MC dropout (for uncertainty) and Grad-CAM (for
    explainability) are separate passes, see `boneage.inference`.
    """

    def __init__(self, model: BoneAgeModel) -> None:
        self.model = model
        self.target_layer = _get_target_layer(model)
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


def overlay_heatmap_on_image(
    base_image: Image.Image, cam: np.ndarray, alpha: float = 0.45
) -> Image.Image:
    """Alpha-blend an inferno-coloured `cam` (values in [0, 1]) over `base_image`.

    `cam` is resized (nearest the feature-map resolution) up to `base_image`'s
    size before colouring. Uses matplotlib's "inferno" colormap, matching the
    `#3B0F70 → #B73779 → #FC8961 → #FCFDBF` scale in docs/design.md.
    """
    import matplotlib

    base_rgb = base_image.convert("RGB")
    width, height = base_rgb.size

    cam_uint8 = (np.clip(cam, 0.0, 1.0) * 255).astype(np.uint8)
    cam_resized = np.asarray(
        Image.fromarray(cam_uint8).resize((width, height), Image.BILINEAR)
    ).astype(np.float32) / 255.0

    colormap = matplotlib.colormaps["inferno"]
    colored = (colormap(cam_resized)[:, :, :3] * 255).astype(np.uint8)
    heatmap_img = Image.fromarray(colored, mode="RGB")

    return Image.blend(base_rgb, heatmap_img, alpha=alpha)
