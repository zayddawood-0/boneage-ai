#!/usr/bin/env python
"""Exports a trained checkpoint to the ONNX graphs the backend's torch-free
inference path needs (see boneage/onnx_export.py, boneage/onnx_inference.py,
and docs/architecture.md#deployment-notes-hackathon-demo). The checkpoint
itself stays gitignored; so does the output directory by default — upload
its contents somewhere `CHECKPOINT_DOWNLOAD_URL` (backend/.env.example) can
fetch, or point `ML_ONNX_DIR` at it directly for local dev.

Usage (from the repo root):
    python ml/export_onnx.py \\
        --config ml/config/config.yaml \\
        --checkpoint ml/checkpoints/best_model.pt \\
        --out-dir ml/checkpoints/onnx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ML_DIR = Path(__file__).resolve().parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from boneage.config import load_config  # noqa: E402
from boneage.onnx_export import export_to_onnx  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="ml/config/config.yaml")
    parser.add_argument("--checkpoint", required=True, type=Path, help="trained .pt checkpoint")
    parser.add_argument("--out-dir", required=True, type=Path, help="directory to write the ONNX graphs + metadata.json into")
    args = parser.parse_args()

    pipeline_config = load_config(args.config)
    paths = export_to_onnx(args.checkpoint, pipeline_config, args.out_dir)

    print(f"Wrote {paths.backbone}")
    print(f"Wrote {paths.head_part1}")
    print(f"Wrote {paths.head_part2}")
    print(f"Wrote {paths.metadata}")


if __name__ == "__main__":
    main()
