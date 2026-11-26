#!/usr/bin/env python
"""Evaluate a trained checkpoint on the RSNA validation and/or test split.

See docs/model.md#evaluation-metrics. Saves MAE overall/by sex/by age band
and % within threshold to a JSON file, plus a predicted-vs-true scatter
plot, under config.evaluation.output_dir — these are the numbers that will
eventually fill the Model performance screen (docs/design.md#7-model-performance).

Only run this against a real trained checkpoint — its output is real
results, not a placeholder (docs/model.md says every metric stays [TBD]
until that's true).

Usage:
    python ml/evaluate.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt
    python ml/evaluate.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt --split test
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import torch  # noqa: E402

from boneage.config import load_config  # noqa: E402
from boneage.dataloaders import build_dataloaders_from_pipeline_config  # noqa: E402
from boneage.evaluation import (  # noqa: E402
    evaluate_model,
    load_checkpoint,
    save_results_json,
    save_scatter_plot,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).parent / "config" / "config.yaml"
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--split", choices=["val", "test", "both"], default="both")
    args = parser.parse_args()

    config = load_config(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, checkpoint_meta = load_checkpoint(args.checkpoint, device=device)
    logger.info(
        "Loaded checkpoint from epoch %s (val_mae=%.3f at save time)",
        checkpoint_meta.get("epoch"),
        checkpoint_meta.get("val_mae", float("nan")),
    )

    _, val_loader, test_loader = build_dataloaders_from_pipeline_config(config)
    loaders = {"val": val_loader, "test": test_loader}
    splits_to_run = ["val", "test"] if args.split == "both" else [args.split]

    output_dir = Path(config.evaluation.output_dir)

    for split in splits_to_run:
        result = evaluate_model(
            model,
            loaders[split],
            split=split,
            age_band_edges_months=config.evaluation.age_band_edges_months,
            within_months_threshold=config.evaluation.within_months_threshold,
            device=device,
        )
        save_results_json(result, output_dir / f"{split}_results.json")
        save_scatter_plot(result, output_dir / f"{split}_scatter.png")
        logger.info(
            "%s: n=%d MAE overall=%.3f months, %% within %.0f months=%.1f%%",
            split,
            result.n_samples,
            result.mae_overall,
            result.within_threshold_months,
            result.percent_within_threshold,
        )

    logger.info("Results saved to %s", output_dir)


if __name__ == "__main__":
    main()
