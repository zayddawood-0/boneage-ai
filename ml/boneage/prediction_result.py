"""The single-image prediction result shape, shared by both inference paths
(the real PyTorch path in `inference.py`, and the torch-free ONNX path in
`onnx_inference.py`) — kept in its own module, rather than defined in
either of those, so importing it never pulls in torch (see
`onnx_inference.py`'s module docstring for why that matters).
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass
class PredictionResult:
    bone_age_months: float
    uncertainty_months: float
    mc_dropout_samples: list[float]
    heatmap_image: Image.Image  # pre-blended X-ray + heatmap (PDF report)
    plain_image: Image.Image  # the preprocessed X-ray alone (RGB), no heatmap
    heatmap_layer: Image.Image  # the attention heatmap alone (RGBA), same size as plain_image
