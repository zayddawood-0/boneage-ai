"""Loading a labels CSV and (where needed) splitting it deterministically.

RSNA already ships as three pre-split pools — train/validation/test, as
provided by the challenge (see docs/data.md#splits) — so for RSNA this module
is mostly about normalising column names, not computing a split.

`random_split_dataframe` is a generic, seeded train/val/test splitter for
datasets that only come as a single pool (e.g. DHA/RHPE, or ad-hoc internal
splits — see docs/data.md: "Internal train/val split, if any is needed ...").
"""
from __future__ import annotations

import pandas as pd


def _resolve_column(df: pd.DataFrame, canonical: str, aliases: list[str]) -> str:
    for candidate in aliases:
        if candidate in df.columns:
            return candidate
    raise KeyError(
        f"None of the expected column names {aliases!r} for '{canonical}' "
        f"were found in CSV columns {list(df.columns)!r}."
    )


def load_labels_csv(
    csv_path: str,
    column_aliases: dict[str, list[str]],
) -> pd.DataFrame:
    """Load a labels CSV and normalise its columns to id/boneage/male.

    `male` is coerced to 0/1 (RSNA's Kaggle CSV already uses True/False;
    other sources may use "M"/"F" strings).
    """
    df = pd.read_csv(csv_path)

    id_col = _resolve_column(df, "id", column_aliases["id"])
    boneage_col = _resolve_column(df, "boneage", column_aliases["boneage"])
    male_col = _resolve_column(df, "male", column_aliases["male"])

    out = pd.DataFrame(
        {
            "id": df[id_col].astype(str),
            "boneage": df[boneage_col].astype(float),
            "male": df[male_col].apply(_coerce_male_flag),
        }
    )
    return out.reset_index(drop=True)


def _coerce_male_flag(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    if text in ("m", "male", "true", "1"):
        return 1
    if text in ("f", "female", "false", "0"):
        return 0
    raise ValueError(f"Could not interpret sex/male flag value: {value!r}")


def random_split_dataframe(
    df: pd.DataFrame,
    val_frac: float,
    test_frac: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Deterministically split a single-pool manifest into train/val/test.

    Same `seed` always produces the same partition for the same input
    DataFrame. Not used for RSNA (which has official pre-split pools) — see
    module docstring.
    """
    if not 0 <= val_frac < 1 or not 0 <= test_frac < 1 or val_frac + test_frac >= 1:
        raise ValueError("val_frac and test_frac must be in [0, 1) and sum to < 1")

    shuffled = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    n = len(shuffled)
    n_test = int(round(n * test_frac))
    n_val = int(round(n * val_frac))

    test_df = shuffled.iloc[:n_test].reset_index(drop=True)
    val_df = shuffled.iloc[n_test : n_test + n_val].reset_index(drop=True)
    train_df = shuffled.iloc[n_test + n_val :].reset_index(drop=True)
    return train_df, val_df, test_df
