"""Evaluation metrics: MAE overall/by sex/by age band, % within a threshold.

See docs/model.md#evaluation-metrics — this module only computes numbers from
whatever predictions/targets it's given; it never invents or hard-codes a
result itself.
"""
from __future__ import annotations

import numpy as np


def mean_absolute_error(preds: np.ndarray, targets: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(preds) - np.asarray(targets))))


def percent_within_threshold(preds: np.ndarray, targets: np.ndarray, threshold: float) -> float:
    preds = np.asarray(preds)
    targets = np.asarray(targets)
    return float(np.mean(np.abs(preds - targets) <= threshold) * 100.0)


def mae_by_group(preds: np.ndarray, targets: np.ndarray, groups: list) -> dict[str, float | None]:
    """`groups`: a label per sample (e.g. "male"/"female", or an age-band label).

    Returns `{label: mae}`; a group with zero samples maps to `None` rather
    than being omitted, so callers can see every expected bucket.
    """
    preds = np.asarray(preds)
    targets = np.asarray(targets)
    groups_arr = np.asarray(groups)

    out: dict[str, float | None] = {}
    for label in sorted(set(groups_arr.tolist()), key=str):
        mask = groups_arr == label
        out[str(label)] = mean_absolute_error(preds[mask], targets[mask]) if mask.any() else None
    return out


def age_band_labels(ages_months: np.ndarray, edges_months: list[float]) -> list[str]:
    """Bucket ages into bands defined by consecutive `edges_months`.

    Ages below the first edge get `"<{edge}"`; ages at/above the last edge
    fall into the final (open-ended) bucket. These bucket boundaries are a
    placeholder for grouping evaluation output, not a clinical claim — the
    real boundaries are `[TBD]`, see docs/model.md#evaluation-metrics.
    """
    edges = sorted(float(e) for e in edges_months)
    if len(edges) < 2:
        raise ValueError("edges_months must have at least 2 values")

    labels = []
    for age in ages_months:
        age = float(age)
        if age < edges[0]:
            labels.append(f"<{int(edges[0])}")
            continue
        label = f"{int(edges[-1])}+"
        for lo, hi in zip(edges[:-1], edges[1:]):
            if lo <= age < hi:
                label = f"{int(lo)}-{int(hi)}"
                break
        labels.append(label)
    return labels
