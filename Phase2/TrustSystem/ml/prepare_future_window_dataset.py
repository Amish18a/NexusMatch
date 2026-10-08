"""
NexusMatch - Future-window Trust dataset.

Research question:
    Can behaviour observed before a matchmaking decision predict whether a
    player will show an unreliable/leaver event in their NEXT THREE matches?

Each training example represents a player immediately before one target match.

Features use ONLY matches strictly before the target match.
Target uses the current target match + the following two matches.

Examples are retained only when:
    - at least 3 historical matches exist
    - a complete 3-match future window exists
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "dota2_processed"
    / "player_behavior_features.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "ml"
OUTPUT_FILE = OUTPUT_DIR / "future_window_trust_dataset.csv"

MIN_HISTORY = 3
FUTURE_WINDOW = 3

FEATURES = [
    "history_matches",
    "prior_leaver_rate",
    "recent_3_leaver_rate",
    "prior_avg_kda_ratio",
    "recent_3_avg_kda_ratio",
    "prior_avg_gold_per_min",
    "recent_3_avg_gold_per_min",
    "prior_avg_xp_per_min",
    "recent_3_avg_xp_per_min",
    "prior_avg_chat_message_count",
    "recent_3_avg_chat_message_count",
    "prior_avg_avg_message_length",
    "recent_3_avg_avg_message_length",
]


def reverse_rolling_max(series: pd.Series, window: int) -> pd.Series:
    """Maximum over current + next window-1 observations."""
    return (
        series.iloc[::-1]
        .rolling(window=window, min_periods=window)
        .max()
        .iloc[::-1]
    )


def previous_expanding_mean(series: pd.Series) -> pd.Series:
    """Mean of observations strictly before the current row."""
    return series.shift(1).expanding().mean()


def previous_rolling_mean(series: pd.Series, window: int) -> pd.Series:
    """Mean of the previous window observations only."""
    return series.shift(1).rolling(window=window, min_periods=window).mean()


def main() -> None:
    print("NexusMatch - Future-Window Trust Dataset")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing processed dataset: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    required = {
        "account_id",
        "match_id",
        "start_datetime",
        "leaver_flag",
        "kda_ratio",
        "gold_per_min",
        "xp_per_min",
        "chat_message_count",
        "avg_message_length",
    }

    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["account_id"] = pd.to_numeric(df["account_id"], errors="coerce")
    df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce")

    df = df[df["account_id"].fillna(0).ne(0)].copy()

    df["start_datetime"] = pd.to_datetime(
        df["start_datetime"],
        errors="coerce",
        utc=True,
    )

    df = df.dropna(
        subset=["account_id", "match_id", "start_datetime"]
    )

    numeric = [
        "leaver_flag",
        "kda_ratio",
        "gold_per_min",
        "xp_per_min",
        "chat_message_count",
        "avg_message_length",
    ]

    for column in numeric:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        ).fillna(0)

    df = (
        df.sort_values(
            ["account_id", "start_datetime", "match_id"]
        )
        .drop_duplicates(
            subset=["account_id", "match_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    grouped = df.groupby("account_id", sort=False)

    df["history_matches"] = grouped.cumcount()

    df["prior_leaver_rate"] = grouped["leaver_flag"].transform(
        previous_expanding_mean
    )

    df["recent_3_leaver_rate"] = grouped["leaver_flag"].transform(
        lambda s: previous_rolling_mean(s, 3)
    )

    for source, prefix in [
        ("kda_ratio", "kda_ratio"),
        ("gold_per_min", "gold_per_min"),
        ("xp_per_min", "xp_per_min"),
        ("chat_message_count", "chat_message_count"),
        ("avg_message_length", "avg_message_length"),
    ]:
        df[f"prior_avg_{prefix}"] = grouped[source].transform(
            previous_expanding_mean
        )
        df[f"recent_3_avg_{prefix}"] = grouped[source].transform(
            lambda s: previous_rolling_mean(s, 3)
        )

    df["future_leaver_rate_3"] = grouped["leaver_flag"].transform(
        lambda s: reverse_rolling_max(s, FUTURE_WINDOW)
    )

    df["future_window_end"] = grouped["start_datetime"].transform(
        lambda s: s.shift(-(FUTURE_WINDOW - 1))
    )

    df["future_leaver_3"] = (
        df["future_leaver_rate_3"].gt(0).astype("Int64")
    )

    df = df[
        (df["history_matches"] >= MIN_HISTORY)
        & df["future_leaver_rate_3"].notna()
        & df["future_window_end"].notna()
    ].copy()

    df = df.dropna(subset=FEATURES).copy()

    output_columns = [
        "account_id",
        "match_id",
        "start_datetime",
        "future_window_end",
        *FEATURES,
        "future_leaver_3",
    ]

    result = df[output_columns].copy()
    result["future_leaver_3"] = result[
        "future_leaver_3"
    ].astype(int)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    positives = int(result["future_leaver_3"].sum())
    negatives = len(result) - positives

    print(f"Source player-match rows: {len(df):,}")
    print(f"Training examples        : {len(result):,}")
    print(f"Positive future-leaver   : {positives:,}")
    print(f"Negative future-leaver   : {negatives:,}")
    print(
        f"Positive rate             : "
        f"{positives / len(result) * 100:.2f}%"
    )
    print(f"Saved dataset             : {OUTPUT_FILE}")

    print("\nFeatures:")
    for feature in FEATURES:
        print(f"  - {feature}")

    print("\nTarget:")
    print(
        "  future_leaver_3 = 1 if at least one of the next "
        "three matches has a recorded leaver event."
    )


if __name__ == "__main__":
    main()
