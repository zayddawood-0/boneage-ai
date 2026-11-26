"""Training loop for the bone age regression model.

See docs/model.md#training-plan and docs/model.md#loss. Every hyperparameter
comes from the `PipelineConfig` (never hard-coded) — see
`boneage.config.TrainingConfig`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from .config import PipelineConfig
from .dataloaders import build_dataloaders_from_pipeline_config
from .model import BoneAgeModel

logger = logging.getLogger(__name__)


@dataclass
class EpochMetrics:
    epoch: int
    train_mae: float
    val_mae: float


@dataclass
class TrainingSummary:
    history: list[EpochMetrics] = field(default_factory=list)
    best_epoch: int = -1
    best_val_mae: float = float("inf")
    checkpoint_path: Path | None = None
    stopped_early: bool = False


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    device: torch.device,
    scaler: torch.amp.GradScaler | None,
    use_amp: bool,
    train: bool,
) -> float:
    model.train() if train else model.eval()
    loss_fn = nn.L1Loss()
    total_abs_error = 0.0
    total_count = 0

    with torch.enable_grad() if train else torch.no_grad():
        for images, sexes, bone_ages in loader:
            images = images.to(device)
            sexes = sexes.to(device)
            bone_ages = bone_ages.to(device)

            if train:
                assert optimizer is not None
                optimizer.zero_grad()

            if use_amp:
                with torch.amp.autocast(device_type="cuda", enabled=True):
                    preds = model(images, sexes)
                    loss = loss_fn(preds, bone_ages)
            else:
                preds = model(images, sexes)
                loss = loss_fn(preds, bone_ages)

            if train:
                if scaler is not None:
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()

            total_abs_error += torch.sum(torch.abs(preds.detach() - bone_ages)).item()
            total_count += bone_ages.shape[0]

    return total_abs_error / max(total_count, 1)


def train_model(
    config: PipelineConfig,
    max_epochs: int | None = None,
    device: str | torch.device | None = None,
) -> TrainingSummary:
    """Train the bone age model per `config`, with early stopping on val MAE.

    - Loss: L1 (MAE) — see docs/model.md#loss.
    - Optimizer: AdamW.
    - LR schedule, early-stopping patience, checkpoint dir: all from
      `config.training`.
    - Mixed precision is only enabled when running on CUDA (irrelevant on
      CPU — see docs/model.md and docs/architecture.md).
    - Saves the best-val-MAE checkpoint to `config.training.checkpoint_dir`.

    `max_epochs`, if given, overrides `config.training.epochs` — used by the
    1-epoch smoke test; real runs should leave it unset.
    """
    from .seed import set_seed

    set_seed(config.seed)

    resolved_device = (
        torch.device(device)
        if device is not None
        else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )

    train_loader, val_loader, _ = build_dataloaders_from_pipeline_config(config)

    model = BoneAgeModel(config.model).to(resolved_device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )

    epochs = max_epochs if max_epochs is not None else config.training.epochs
    if epochs < 1:
        raise ValueError("epochs must be >= 1")

    if config.training.lr_scheduler == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(epochs, 1))
    elif config.training.lr_scheduler == "plateau":
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=1)
    else:
        raise ValueError(f"Unknown lr_scheduler: {config.training.lr_scheduler!r}")

    use_amp = bool(config.training.mixed_precision and resolved_device.type == "cuda")
    scaler = torch.amp.GradScaler(device="cuda", enabled=use_amp) if use_amp else None

    checkpoint_dir = Path(config.training.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "best_model.pt"

    summary = TrainingSummary(checkpoint_path=checkpoint_path)
    epochs_without_improvement = 0

    for epoch in range(1, epochs + 1):
        train_mae = _run_epoch(
            model, train_loader, optimizer, resolved_device, scaler, use_amp, train=True
        )
        val_mae = _run_epoch(
            model, val_loader, None, resolved_device, scaler, use_amp, train=False
        )

        if config.training.lr_scheduler == "plateau":
            scheduler.step(val_mae)
        else:
            scheduler.step()

        summary.history.append(EpochMetrics(epoch=epoch, train_mae=train_mae, val_mae=val_mae))
        if epoch % max(config.training.log_every_n_steps, 1) == 0 or epoch == epochs:
            logger.info("epoch %d: train_mae=%.3f val_mae=%.3f", epoch, train_mae, val_mae)

        improved = val_mae < summary.best_val_mae
        if improved:
            summary.best_val_mae = val_mae
            summary.best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "model_config": config.model,
                    "epoch": epoch,
                    "val_mae": val_mae,
                },
                checkpoint_path,
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.training.early_stopping_patience:
                summary.stopped_early = True
                break

    return summary
