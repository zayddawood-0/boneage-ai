from __future__ import annotations

import pandas as pd
import pytest

from boneage.splits import load_labels_csv, random_split_dataframe

COLUMN_ALIASES = {
    "id": ["id", "Case ID"],
    "boneage": ["boneage", "Bone Age"],
    "male": ["male", "Sex"],
}


def test_load_labels_csv_normalises_standard_columns(make_fake_split, column_aliases):
    _, labels_csv, df = make_fake_split("train", n=5)

    loaded = load_labels_csv(str(labels_csv), column_aliases)

    assert list(loaded.columns) == ["id", "boneage", "male"]
    assert len(loaded) == len(df)
    assert set(loaded["id"]) == set(df["id"])
    assert loaded["male"].isin([0, 1]).all()


def test_load_labels_csv_resolves_aliased_columns(tmp_path):
    # Mimics an RSNA test-CSV variant that uses "Case ID"/"Sex" headers.
    df = pd.DataFrame(
        {
            "Case ID": ["a1", "a2", "a3"],
            "Bone Age": [24.0, 60.0, 120.0],
            "Sex": ["M", "F", "M"],
        }
    )
    csv_path = tmp_path / "aliased.csv"
    df.to_csv(csv_path, index=False)

    loaded = load_labels_csv(str(csv_path), COLUMN_ALIASES)

    assert list(loaded["id"]) == ["a1", "a2", "a3"]
    assert list(loaded["boneage"]) == [24.0, 60.0, 120.0]
    assert list(loaded["male"]) == [1, 0, 1]


def test_load_labels_csv_missing_column_raises(tmp_path):
    df = pd.DataFrame({"id": ["a1"], "boneage": [24.0]})  # no sex column at all
    csv_path = tmp_path / "broken.csv"
    df.to_csv(csv_path, index=False)

    with pytest.raises(KeyError):
        load_labels_csv(str(csv_path), COLUMN_ALIASES)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (True, 1),
        (False, 0),
        (1, 1),
        (0, 0),
        ("M", 1),
        ("f", 0),
        ("male", 1),
        ("Female", 0),
        ("true", 1),
        ("0", 0),
    ],
)
def test_coerce_male_flag_variants(tmp_path, raw, expected):
    df = pd.DataFrame({"id": ["a1"], "boneage": [24.0], "male": [raw]})
    csv_path = tmp_path / "variant.csv"
    df.to_csv(csv_path, index=False)

    loaded = load_labels_csv(str(csv_path), COLUMN_ALIASES)

    assert loaded["male"].iloc[0] == expected


def test_random_split_dataframe_sizes_and_coverage():
    df = pd.DataFrame({"id": [f"id_{i}" for i in range(100)], "value": range(100)})

    train_df, val_df, test_df = random_split_dataframe(df, val_frac=0.2, test_frac=0.1, seed=42)

    assert len(train_df) + len(val_df) + len(test_df) == len(df)
    assert len(val_df) == 20
    assert len(test_df) == 10

    all_ids = set(train_df["id"]) | set(val_df["id"]) | set(test_df["id"])
    assert all_ids == set(df["id"])
    # No sample should appear in more than one split.
    assert len(train_df) + len(val_df) + len(test_df) == len(all_ids)


def test_random_split_dataframe_is_deterministic_for_same_seed():
    df = pd.DataFrame({"id": [f"id_{i}" for i in range(50)]})

    first = random_split_dataframe(df, val_frac=0.2, test_frac=0.1, seed=123)
    second = random_split_dataframe(df, val_frac=0.2, test_frac=0.1, seed=123)

    for part_a, part_b in zip(first, second):
        assert list(part_a["id"]) == list(part_b["id"])


def test_random_split_dataframe_rejects_invalid_fractions():
    df = pd.DataFrame({"id": ["a", "b", "c"]})
    with pytest.raises(ValueError):
        random_split_dataframe(df, val_frac=0.6, test_frac=0.6, seed=1)
