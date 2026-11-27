#!/usr/bin/env python
"""Runs the real PyTorch Grad-CAM and the ONNX Score-CAM side by side on a
few sample images, so you can eyeball that they highlight similar regions
before trusting Score-CAM in a demo — see docs/model.md#explainability for
why ONNX Runtime needs a gradient-free stand-in for Grad-CAM in the first
place, and `boneage/score_cam.py` for the method itself.

Usage (from the repo root, with a trained checkpoint and its ONNX export already in place):
    python ml/compare_heatmaps.py \\
        --config ml/config/config.yaml \\
        --checkpoint ml/checkpoints/best_model.pt \\
        --onnx-dir ml/checkpoints/onnx \\
        --images path/to/xray1.png path/to/xray2.png \\
        --out-dir ml/results/heatmap_comparison

Omit `--images` to compare against a couple of auto-generated synthetic
grayscale images instead (useful for a quick sanity check without a real
X-ray on hand — these are NOT real hand X-rays, just noise, so don't expect
the heatmaps to land on anything anatomically meaningful).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

_ML_DIR = Path(__file__).resolve().parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from boneage.config import load_config  # noqa: E402
from boneage.inference import load_checkpoint, predict_single_image  # noqa: E402
from boneage.onnx_inference import predict_single_image_onnx  # noqa: E402

_CAPTION_HEIGHT = 20


def _make_synthetic_images(out_dir: Path, n: int = 2) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(n):
        rng = np.random.default_rng(i)
        arr = rng.integers(20, 220, size=(400, 320), dtype=np.uint8)
        path = out_dir / f"synthetic_{i}.png"
        Image.fromarray(arr, mode="L").save(path)
        paths.append(path)
    return paths


def _labelled(image: Image.Image, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (image.width, image.height + _CAPTION_HEIGHT), (255, 255, 255))
    canvas.paste(image.convert("RGB"), (0, 0))
    ImageDraw.Draw(canvas).text((4, image.height + 2), caption, fill=(0, 0, 0))
    return canvas


def _side_by_side(*panels: Image.Image) -> Image.Image:
    width = sum(p.width for p in panels)
    height = max(p.height for p in panels)
    combined = Image.new("RGB", (width, height), (255, 255, 255))
    x = 0
    for panel in panels:
        combined.paste(panel, (x, 0))
        x += panel.width
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--onnx-dir", required=True, type=Path)
    parser.add_argument("--images", nargs="*", type=Path, default=None)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--mc-dropout-passes", type=int, default=5)
    args = parser.parse_args()

    pipeline_config = load_config(args.config)
    model, _ = load_checkpoint(args.checkpoint, device="cpu")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    image_paths = args.images or _make_synthetic_images(args.out_dir / "_synthetic_inputs")

    for image_path in image_paths:
        torch_result = predict_single_image(
            model,
            image_path,
            sex_is_male=True,
            preprocessing_config=pipeline_config.preprocessing,
            mc_dropout_passes=args.mc_dropout_passes,
            device="cpu",
        )
        onnx_result = predict_single_image_onnx(
            args.onnx_dir,
            image_path,
            sex_is_male=True,
            mc_dropout_passes=args.mc_dropout_passes,
        )

        panels = [
            _labelled(torch_result.plain_image, "X-ray"),
            _labelled(torch_result.heatmap_image, f"Grad-CAM ({torch_result.bone_age_months:.1f}mo)"),
            _labelled(onnx_result.heatmap_image, f"Score-CAM ({onnx_result.bone_age_months:.1f}mo)"),
        ]
        composite = _side_by_side(*panels)

        out_path = args.out_dir / f"{Path(image_path).stem}_comparison.png"
        composite.save(out_path)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
