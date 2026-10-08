"""
NexusMatch - Build a temporal reliability dataset.

This is the next, more realistic experiment after the retrospective baseline.

For each identified player, matches are ordered by match start time. Features for
a target match use ONLY information from the player's previous matches.

Target:
    leaver_next_match = 1 -> the player is recorded as a leaver in the target match
    leaver_next_match = 0 -> the player is not recorded as a leaver in the target match

This avoids using the target match's performance/chat data to predict its own
leaver outcome.

A minimum historical window is required before creating a training example.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PLAYER_FILE = (
    BASE_DIR / "data" / "dota2_processed" / "player_behavior_features.csv"
)
MATCH_FILE = (
    BASE_DIR / "data" / "dota2_processed" / "match_processed.csv"
)
OUTPUT_DIR = BASE_DIR / "data" / "ml"
OUTPUT_FILE = OUTPUT_DIR / "temporal_trust_dataset.csv"

MIN_HISTORY = 3

HISTORY_SOURCE_FEATURES = [
    "leaver_flag",
    "kda_ratio",
    "gold_per_min",
    "xp_per_min",
    "chat_message_count",
    "avg_message_length",
]


def cumulative_previous_mean(
    group: pd.Series,
) -> pd.Series:
    """Mean of previous observations only, avoiding current-row leakage."""
    return group.shift(1).expanding().mean()


def main() -> None:
    print("NexusMatch - Temporal Trust Dataset")
    print("=" * 52)

    if not PLAYER_FILE.exists():
        raise FileNotFoundError(f"Missing: {PLAYER_FILE}")

    if not MATCH_FILE.exists():
        raise FileNotFoundError(f"Missing: {MATCH_FILE}")

    players = pd.read_csv(PLAYER_FILE)
    matches = pd.read_csv(MATCH_FILE)

    required_player = {
        "account_id",
        "match_id",
        "leaver_flag",
        "kda_ratio",
        "gold_per_min",
        "xp_per_min",
        "chat_message_count",
        "avg_message_length",
    }
    missing_player = sorted(required_player.difference(players.columns))
    if missing_player:
        raise ValueError(f"Missing player columns: {missing_player}")

    required_match = {"match_id", "start_datetime"}
    missing_match = sorted(required_match.difference(matches.columns))
    if missing_match:
        raise ValueError(f"Missing match columns: {missing_match}")

    df = players.copy()

    # Anonymous account IDs cannot be tracked across matches, so exclude them
    # from the temporal player-history experiment.
    df = df[df["account_id"].fillna(0).ne(0)].copy()

    df = df.merge(
        matches[["match_id", "start_datetime"]],
        on="match_id",
        how="left",
        validate="many_to_one",
    )

    df["start_datetime"] = pd.to_datetime(
        df["start_datetime"],
        errors="coerce",
        utc=True,
    )

    df = df.dropna(
        subset=["account_id", "match_id", "start_datetime"]
    )

    # One player record per match.
    df = df.sort_values(
        ["account_id", "start_datetime", "match_id"]
    )
    df = df.drop_duplicates(
        subset=["account_id", "match_id"],
        keep="first",
    )

    # Fill per-match feature gaps before building historical averages.
    numeric_features = [
        "leaver_flag",
        "kda_ratio",
        "gold_per_min",
        "xp_per_min",
        "chat_message_count",
        "avg_message_length",
    ]

    for column in numeric_features:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        df[column] = df[column].fillna(0)

    grouped = df.groupby("account_id", sort=False)

    df["history_matches"] = grouped.cumcount()

    # Shifted values ensure that every predictor is based on matches that
    # happened before the target match.
    df["prior_leaver_rate"] = (
        grouped["leaver_flag"]
        .transform(lambda s: s.shift(1).expanding().mean())
    )

    for source in [
        "kda_ratio",
        "gold_per_min",
        "xp_per_min",
        "chat_message_count",
        "avg_message_length",
    ]:
        output = f"prior_avg_{source}"
        df[output] = grouped[source].transform(
            lambda s: s.shift(1).expanding().mean()
        )

    df["leaver_next_match"] = df["leaver_flag"].astype(int)

    temporal_features = [
        "history_matches",
        "prior_leaver_rate",
        "prior_avg_kda_ratio",
        "prior_avg_gold_per_min",
        "prior_avg_xp_per_min",
        "prior_avg_chat_message_count",
        "prior_avg_avg_message_length",
    ]

    result = df[
        [
            "account_id",
            "match_id",
            "start_datetime",
            *temporal_features,
            "leaver_next_match",
        ]
    ].copy()

    result = result[
        result["history_matches"] >= MIN_HISTORY
    ].copy()

    # Replace any missing historical means (should only occur at the earliest
    # rows that survive filtering) and keep the dataset numeric.
    result = result.dropna(subset=temporal_features)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    print(f"Identified player-match rows : {len(df):,}")
    print(
        f"Temporal examples with >= {MIN_HISTORY} previous matches: "
        f"{len(result):,}"
    )
    print(
        f"Leaver target = 1           : "
        f"{int(result['leaver_next_match'].sum()):,}"
    )
    print(
        f"Non-leaver target = 0       : "
        f"{int((result['leaver_next_match'] == 0).sum()):,}"
    )
    print(f"Saved: {OUTPUT_FILE}")

    print("\nTemporal features:")
    for feature in temporal_features:
        print(f"  - {feature}")


if __name__ == "__main__":
    main()
