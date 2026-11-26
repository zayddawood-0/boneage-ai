"""Single-image inference: bone age + MC-dropout uncertainty + Grad-CAM heatmap.

See docs/model.md#uncertainty-approach and docs/model.md#explainability.
Keep this module the one place that knows how to go from (checkpoint, image,
sex) to a prediction — the FastAPI backend should call into this rather than
reimplementing any of it (see CLAUDE.md#coding-conventions).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .config import PreprocessingConfig
from .gradcam import GradCAM, heatmap_layer_image, overlay_heatmap_on_image
from .model import BoneAgeModel, set_mc_dropout_mode
from .transforms import ResizeWithPad, build_transforms, load_and_orient


@dataclass
class PredictionResult:
    bone_age_months: float
    uncertainty_months: float
    mc_dropout_samples: list[float]
    heatmap_image: Image.Image  # pre-blended X-ray + heatmap (PDF report)
    plain_image: Image.Image  # the preprocessed X-ray alone (RGB), no heatmap
    heatmap_layer: Image.Image  # the Grad-CAM heatmap alone (RGBA), same size as plain_image


def load_checkpoint(
    checkpoint_path: str | Path, device: torch.device | str | None = None
) -> tuple[BoneAgeModel, dict]:
    """Load a `BoneAgeModel` from a checkpoint saved by `boneage.training.train_model`."""
    device = (
        torch.device(device)
        if device is not None
        else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = BoneAgeModel(checkpoint["model_config"]).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


def predict_single_image(
    model: BoneAgeModel,
    image_path: str | Path,
    sex_is_male: bool,
    preprocessing_config: PreprocessingConfig,
    mc_dropout_passes: int,
    device: torch.device | str | None = None,
) -> PredictionResult:
    """Predict bone age + MC-dropout uncertainty + Grad-CAM heatmap for one image.

    - Point estimate + uncertainty: mean/std over `mc_dropout_passes`
      stochastic forward passes, dropout left on and BatchNorm frozen (see
      `boneage.model.set_mc_dropout_mode`) — this *is* the MC-dropout
      technique from docs/model.md#uncertainty-approach, not a separate
      deterministic prediction.
    - Heatmap: Grad-CAM from one deterministic (dropout off) pass, overlaid
      on the preprocessed X-ray with the inferno colour scale.
    """
    device = torch.device(device) if device is not None else next(model.parameters()).device

    base_image = load_and_orient(image_path)
    eval_transform = build_transforms(preprocessing_config, augmentation_cfg=None, train=False)
    image_tensor = eval_transform(base_image).unsqueeze(0).to(device)
    sex_tensor = torch.tensor([[float(sex_is_male)]], dtype=torch.float32, device=device)

    # 1. MC dropout: stochastic passes -> mean (point estimate) + spread (uncertainty).
    set_mc_dropout_mode(model, True)
    samples: list[float] = []
    with torch.no_grad():
        for _ in range(mc_dropout_passes):
            pred = model(image_tensor, sex_tensor)
            samples.append(pred.item())
    bone_age_months = float(np.mean(samples))
    uncertainty_months = float(np.std(samples))

    # 2. Grad-CAM: one deterministic pass (dropout off) for the heatmap.
    set_mc_dropout_mode(model, False)
    with GradCAM(model) as cam_fn:
        cam = cam_fn(image_tensor, sex_tensor)

    padded_image = ResizeWithPad(preprocessing_config.image_size)(base_image)
    plain_image = padded_image.convert("RGB")
    heatmap_image = overlay_heatmap_on_image(padded_image, cam)
    heatmap_layer = heatmap_layer_image(cam, plain_image.size)

    return PredictionResult(
        bone_age_months=bone_age_months,
        uncertainty_months=uncertainty_months,
        mc_dropout_samples=samples,
        heatmap_image=heatmap_image,
        plain_image=plain_image,
        heatmap_layer=heatmap_layer,
    )


def predict(
    checkpoint_path: str | Path,
    image_path: str | Path,
    sex_is_male: bool,
    preprocessing_config: PreprocessingConfig,
    mc_dropout_passes: int,
    device: torch.device | str | None = None,
) -> PredictionResult:
    """Convenience one-shot entry point: load the checkpoint, then predict.

    Prefer `load_checkpoint` + `predict_single_image` directly when
    predicting more than one image, so the checkpoint is only loaded once.
    """
    model, _ = load_checkpoint(checkpoint_path, device=device)
    return predict_single_image(
        model,
        image_path,
        sex_is_male,
        preprocessing_config,
        mc_dropout_passes,
        device=device,
    )
