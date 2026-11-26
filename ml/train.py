#!/usr/bin/env python
"""Train the BoneAge AI bone age regression model.

See docs/model.md#training-plan. All hyperparameters come from the config
file — nothing here is hard-coded (see boneage.config.TrainingConfig).

Usage:
    python ml/train.py --config ml/config/config.yaml
    python ml/train.py --config ml/config/config.yaml --epochs 1   # quick smoke run
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from boneage.config import load_config  # noqa: E402
from boneage.training import train_model  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config" / "config.yaml",
        help="Path to the ML pipeline config (default: ml/config/config.yaml)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override config.training.epochs (e.g. --epochs 1 for a smoke run)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    logger.info(
        "Starting training: backbone=%s epochs=%s device_amp=%s checkpoint_dir=%s",
        config.model.backbone,
        args.epochs or config.training.epochs,
        config.training.mixed_precision,
        config.training.checkpoint_dir,
    )

    summary = train_model(config, max_epochs=args.epochs)

    logger.info(
        "Training finished. best_epoch=%d best_val_mae=%.3f stopped_early=%s checkpoint=%s",
        summary.best_epoch,
        summary.best_val_mae,
        summary.stopped_early,
        summary.checkpoint_path,
    )


if __name__ == "__main__":
    main()
