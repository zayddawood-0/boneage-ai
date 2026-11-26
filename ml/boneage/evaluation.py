"""Evaluation for the bone age regression model.

See docs/model.md#evaluation-metrics. Computes metrics only from real
predictions produced by a trained checkpoint — nothing here is a
placeholder number. Don't run this against an untrained/randomly
initialised model and treat the output as real results.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .inference import load_checkpoint  # re-exported for convenience
from .metrics import (
    age_band_labels,
    mae_by_group,
    mean_absolute_error,
    percent_within_threshold,
)
from .model import BoneAgeModel

__all__ = [
    "EvaluationResult",
    "evaluate_model",
    "load_checkpoint",
    "save_results_json",
    "save_scatter_plot",
]


@dataclass
class EvaluationResult:
    split: str
    n_samples: int
    mae_overall: float
    mae_by_sex: dict
    mae_by_age_band: dict
    percent_within_threshold: float
    within_threshold_months: float
    predictions: list[float]
    targets: list[float]
    sexes: list[str]

    def to_json_dict(self) -> dict:
        return {
            "split": self.split,
            "n_samples": self.n_samples,
            "mae_overall_months": self.mae_overall,
            "mae_by_sex_months": self.mae_by_sex,
            "mae_by_age_band_months": self.mae_by_age_band,
            "percent_within_threshold": self.percent_within_threshold,
            "within_threshold_months": self.within_threshold_months,
        }


def _predict_loader(
    model: BoneAgeModel, loader: DataLoader, device: torch.device
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    preds, targets, sexes = [], [], []
    model.eval()
    with torch.no_grad():
        for images, sex, bone_age in loader:
            out = model(images.to(device), sex.to(device))
            preds.append(out.cpu().numpy())
            targets.append(bone_age.numpy())
            sexes.append(sex.squeeze(-1).numpy())
    return np.concatenate(preds), np.concatenate(targets), np.concatenate(sexes)


def evaluate_model(
    model: BoneAgeModel,
    loader: DataLoader,
    split: str,
    age_band_edges_months: list[float],
    within_months_threshold: float,
    device: torch.device | str | None = None,
) -> EvaluationResult:
    """MAE overall / by sex / by age band, and % within `within_months_threshold`."""
    device = torch.device(device) if device is not None else next(model.parameters()).device
    preds, targets, sexes = _predict_loader(model, loader, device)

    sex_labels = np.where(sexes >= 0.5, "male", "female")
    band_labels = age_band_labels(targets, age_band_edges_months)

    return EvaluationResult(
        split=split,
        n_samples=len(targets),
        mae_overall=mean_absolute_error(preds, targets),
        mae_by_sex=mae_by_group(preds, targets, sex_labels.tolist()),
        mae_by_age_band=mae_by_group(preds, targets, band_labels),
        percent_within_threshold=percent_within_threshold(
            preds, targets, within_months_threshold
        ),
        within_threshold_months=within_months_threshold,
        predictions=preds.tolist(),
        targets=targets.tolist(),
        sexes=sex_labels.tolist(),
    )


def save_results_json(result: EvaluationResult, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result.to_json_dict(), f, indent=2)


def save_scatter_plot(result: EvaluationResult, output_path: str | Path) -> None:
    """Predicted-vs-true scatter plot, for the Model performance screen (docs/design.md)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(result.targets, result.predictions, alpha=0.5, s=12)

    all_values = result.targets + result.predictions
    lims = [min(all_values), max(all_values)] if all_values else [0, 1]
    ax.plot(lims, lims, linestyle="--", color="gray", linewidth=1)

    ax.set_xlabel("True bone age (months)")
    ax.set_ylabel("Predicted bone age (months)")
    ax.set_title(f"Predicted vs. true bone age — {result.split}")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
