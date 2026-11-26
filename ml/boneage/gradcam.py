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


def _resize_and_colorize_cam(cam: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Resizes `cam` (values in [0, 1]) to `size` = (width, height) and
    colours it with matplotlib's "inferno" colormap, matching the
    `#3B0F70 → #B73779 → #FC8961 → #FCFDBF` scale in docs/design.md.

    Returns `(colored_rgb_uint8, cam_resized_float)` — the resized cam is
    also returned so callers can derive a per-pixel alpha from it.
    """
    import matplotlib

    width, height = size
    cam_uint8 = (np.clip(cam, 0.0, 1.0) * 255).astype(np.uint8)
    cam_resized = np.asarray(
        Image.fromarray(cam_uint8).resize((width, height), Image.BILINEAR)
    ).astype(np.float32) / 255.0

    colormap = matplotlib.colormaps["inferno"]
    colored = (colormap(cam_resized)[:, :, :3] * 255).astype(np.uint8)
    return colored, cam_resized


def overlay_heatmap_on_image(
    base_image: Image.Image, cam: np.ndarray, alpha: float = 0.45
) -> Image.Image:
    """Alpha-blend an inferno-coloured `cam` (values in [0, 1]) over `base_image`.

    `cam` is resized (nearest the feature-map resolution) up to `base_image`'s
    size before colouring. This is the single flattened (pre-blended) image
    used for the PDF report — see `heatmap_layer_image` for the separate,
    transparent heatmap layer used by the frontend's independent-layer viewer.
    """
    base_rgb = base_image.convert("RGB")
    colored, _ = _resize_and_colorize_cam(cam, base_rgb.size)
    heatmap_img = Image.fromarray(colored, mode="RGB")
    return Image.blend(base_rgb, heatmap_img, alpha=alpha)


def heatmap_layer_image(cam: np.ndarray, size: tuple[int, int], max_alpha: int = 200) -> Image.Image:
    """The Grad-CAM heatmap alone, as an RGBA image the same `size` as the
    base image it's meant to sit on top of — inferno colours, with each
    pixel's alpha channel proportional to its own attention value (so
    low-attention regions are near-transparent and high-attention regions
    are vividly coloured), scaled by `max_alpha` (0-255).

    Lets the frontend composite this over the plain X-ray itself and control
    the layer's overall opacity independently (see docs/api.md
    `GET /cases/{id}/heatmap-layer`).
    """
    colored, cam_resized = _resize_and_colorize_cam(cam, size)
    alpha_channel = (np.clip(cam_resized, 0.0, 1.0) * max_alpha).astype(np.uint8)
    rgba = np.dstack([colored, alpha_channel])
    return Image.fromarray(rgba, mode="RGBA")
