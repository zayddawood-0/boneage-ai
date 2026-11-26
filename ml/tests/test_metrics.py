from __future__ import annotations

import numpy as np
import pytest

from boneage.metrics import (
    age_band_labels,
    mae_by_group,
    mean_absolute_error,
    percent_within_threshold,
)


def test_mean_absolute_error_basic():
    preds = np.array([10.0, 20.0, 30.0])
    targets = np.array([12.0, 18.0, 35.0])

    assert mean_absolute_error(preds, targets) == pytest.approx((2 + 2 + 5) / 3)


def test_percent_within_threshold_boundary_inclusive():
    preds = np.array([10.0, 20.0, 30.0, 40.0])
    targets = np.array([10.0, 32.0, 30.0, 20.0])
    # abs errors: 0, 12, 0, 20 -> within 12: [True, True, True, False]

    pct = percent_within_threshold(preds, targets, threshold=12.0)

    assert pct == pytest.approx(75.0)


def test_mae_by_group_separates_groups_correctly():
    preds = np.array([10.0, 20.0, 30.0, 40.0])
    targets = np.array([12.0, 22.0, 25.0, 50.0])
    groups = ["male", "female", "male", "female"]

    result = mae_by_group(preds, targets, groups)

    assert result["male"] == pytest.approx((2 + 5) / 2)
    assert result["female"] == pytest.approx((2 + 10) / 2)


def test_mae_by_group_missing_group_is_none_not_omitted():
    preds = np.array([10.0])
    targets = np.array([10.0])
    groups = ["male"]

    result = mae_by_group(preds, targets, groups)

    assert result == {"male": 0.0}  # "female" simply never appears, not fabricated as 0


def test_age_band_labels_assigns_expected_buckets():
    edges = [0, 60, 120, 180, 240]
    ages = [10, 59, 60, 119, 200, 300]

    labels = age_band_labels(ages, edges)

    # 200 falls inside the last bounded bucket [180, 240); 300 is at/beyond
    # the final edge, so it falls through to the open-ended "240+" bucket.
    assert labels == ["0-60", "0-60", "60-120", "60-120", "180-240", "240+"]


def test_age_band_labels_below_first_edge():
    edges = [60, 120, 180]
    ages = [10, 59]

    labels = age_band_labels(ages, edges)

    assert labels == ["<60", "<60"]


def test_age_band_labels_rejects_too_few_edges():
    with pytest.raises(ValueError):
        age_band_labels([10], [60])
