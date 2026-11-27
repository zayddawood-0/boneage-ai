"""Exports a trained checkpoint to ONNX for the backend's torch-free
inference path (see onnx_inference.py and docs/architecture.md#deployment-notes
— this is what lets the backend run on Vercel's Python serverless functions
without `torch`/`torchvision`, which alone are ~750 MB uncompressed, well
past Vercel's 500 MB limit).

**Why three graphs, not one** — the model is `backbone -> concat(features,
sex) -> Dropout -> Linear -> ReLU -> Dropout -> Linear`. MC-dropout
(`docs/model.md#uncertainty-approach`) needs those two Dropout layers active
and *stochastic* (re-sampled on every one of the N inference passes) while
BatchNorm inside the backbone stays frozen (eval-mode statistics) — exactly
what `boneage.model.set_mc_dropout_mode` does for the real PyTorch path.

`torch.onnx.export`'s own `training=TrainingMode.TRAINING` flag can't
reproduce that: it flips the *entire* traced module into training
behaviour, including BatchNorm — which then fails on export (BatchNorm's
training-mode statistics need a batch size > 1, but inference is one image
at a time) and would be wrong even if it didn't fail, since frozen BatchNorm
is required for a stable prediction. (Verified empirically — exporting with
`TrainingMode.TRAINING` raises `ValueError: Expected more than 1 value per
channel when training` from the backbone's BatchNorm layers.)

So dropout is moved *outside* the graph instead: the backbone (which has no
dropout of its own) is exported once, normally, in plain eval mode; the two
tiny head pieces either side of each Dropout are exported separately as
plain `Linear`/`ReLU` graphs; and `onnx_inference.py` applies the actual
Bernoulli dropout masks itself, in numpy, between calling them — the exact
"inverted dropout" scaling (`mask / (1 - p)`) PyTorch's own `nn.Dropout`
uses, so this is numerically equivalent to the real model, not an
approximation. A side benefit: the backbone (no dropout) only has to run
*once* per MC-dropout request instead of once per pass, which is actually
cheaper than the current PyTorch path.

The backbone graph also exposes the target conv layer's raw activations
(`gradcam.get_target_layer`) as a second output, for Score-CAM
(`score_cam.py`) — ONNX Runtime gives forward passes only, so Score-CAM
reads activations instead of gradients (see docs/model.md#explainability).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from .config import PipelineConfig
from .gradcam import get_target_layer
from .inference import load_checkpoint
from .model import BoneAgeModel
from .onnx_inference import (  # noqa: F401 - re-exported for callers that only need filenames
    BACKBONE_FILENAME,
    HEAD1_FILENAME,
    HEAD2_FILENAME,
    METADATA_FILENAME,
)

_OPSET_VERSION = 17

# `dynamo=False` pins the legacy TorchScript-based exporter. PyTorch 2.9+
# defaults to the newer torch.export-based ("dynamo") exporter instead,
# which needs the extra `onnxscript` dependency and hasn't been verified
# against this module's three-graph split — hence the DeprecationWarning
# these exports raise today. Revisit if/when the legacy exporter is actually
# removed (not just deprecated) in a future torch upgrade.


@dataclass(frozen=True)
class OnnxExportPaths:
    backbone: Path
    head_part1: Path
    head_part2: Path
    metadata: Path


class _BackboneWithActivations(nn.Module):
    """Wraps `model.backbone` to also return the target conv layer's raw
    activations as a second output — a plain forward hook, so this needs no
    gradient machinery (unlike `gradcam.GradCAM`, which hooks the same layer
    but for its *gradient*, not just its output)."""

    def __init__(self, model: BoneAgeModel) -> None:
        super().__init__()
        self.backbone = model.backbone
        target_layer = get_target_layer(model)
        self._activations: torch.Tensor | None = None
        self._hook = target_layer.register_forward_hook(self._save_activation)

    def _save_activation(self, module, inputs, output) -> None:
        self._activations = output

    def forward(self, image: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.backbone(image)
        if features.ndim > 2:
            features = torch.flatten(features, 1)
        return features, self._activations

    def close(self) -> None:
        self._hook.remove()


def export_to_onnx(
    checkpoint_path: str | Path,
    pipeline_config: PipelineConfig,
    out_dir: str | Path,
) -> OnnxExportPaths:
    """Loads `checkpoint_path` and writes the three ONNX graphs + metadata.json
    needed by `onnx_inference.py` into `out_dir`. Returns their paths.
    """
    model, _ = load_checkpoint(checkpoint_path, device="cpu")
    model.eval()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = OnnxExportPaths(
        backbone=out_dir / BACKBONE_FILENAME,
        head_part1=out_dir / HEAD1_FILENAME,
        head_part2=out_dir / HEAD2_FILENAME,
        metadata=out_dir / METADATA_FILENAME,
    )

    image_size = pipeline_config.preprocessing.image_size
    dummy_image = torch.rand(1, 3, image_size, image_size)

    backbone_wrapper = _BackboneWithActivations(model)
    try:
        torch.onnx.export(
            backbone_wrapper,
            (dummy_image,),
            str(paths.backbone),
            input_names=["image"],
            output_names=["features", "activations"],
            dynamic_axes={"image": {0: "batch"}},
            opset_version=_OPSET_VERSION,
            dynamo=False,
        )
    finally:
        backbone_wrapper.close()

    linear1: nn.Linear = model.head[1]  # type: ignore[assignment]
    relu: nn.Module = model.head[2]
    linear2: nn.Linear = model.head[4]  # type: ignore[assignment]
    feature_dim = linear1.in_features - 1  # -1 for the concatenated sex scalar
    hidden_dim = linear1.out_features

    head_part1 = nn.Sequential(linear1, relu)
    dummy_combined = torch.rand(1, feature_dim + 1)
    torch.onnx.export(
        head_part1,
        (dummy_combined,),
        str(paths.head_part1),
        input_names=["masked_combined"],
        output_names=["hidden"],
        dynamic_axes={"masked_combined": {0: "batch"}},
        opset_version=_OPSET_VERSION,
        dynamo=False,
    )

    dummy_hidden = torch.rand(1, hidden_dim)
    torch.onnx.export(
        linear2,
        (dummy_hidden,),
        str(paths.head_part2),
        input_names=["masked_hidden"],
        output_names=["bone_age"],
        dynamic_axes={"masked_hidden": {0: "batch"}},
        opset_version=_OPSET_VERSION,
        dynamo=False,
    )

    metadata = {
        "image_size": image_size,
        "normalize_mean": pipeline_config.preprocessing.normalize_mean,
        "normalize_std": pipeline_config.preprocessing.normalize_std,
        "backbone": model.config.backbone,
        "feature_dim": feature_dim,
        "hidden_dim": hidden_dim,
        "dropout": model.config.dropout,
        "mc_dropout_passes": pipeline_config.inference.mc_dropout_passes,
        "score_cam_top_k": pipeline_config.inference.score_cam_top_k,
    }
    paths.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return paths
