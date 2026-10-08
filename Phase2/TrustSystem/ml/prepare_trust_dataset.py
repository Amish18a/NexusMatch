"""
NexusMatch - Prepare the first ML-ready Trust dataset.

This is a retrospective baseline experiment using the processed Dota 2 data.
It is NOT the final deployment-time Trust model.

Label:
    reliable = 1  -> no recorded leaver event
    reliable = 0  -> at least one recorded leaver event

Filtering:
    - keep players with at least 5 recorded matches
    - exclude the direct target columns from model features
    - exclude matches_played from the feature matrix
    - exclude avg_time_samples from the first baseline because it can be
      directly affected by a player leaving a match

Feature groups in the first baseline:
    - avg_kda
    - avg_gold_per_min
    - avg_xp_per_min
    - avg_chat_messages
    - avg_chat_length

The purpose is to establish a reproducible baseline before the project moves
to a temporal/next-match prediction setup.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = (
    BASE_DIR / "data" / "dota2_processed" / "player_reliability_summary.csv"
)
OUTPUT_DIR = BASE_DIR / "data" / "ml"
OUTPUT_FILE = OUTPUT_DIR / "trust_ml_dataset.csv"

MIN_MATCHES = 5

FEATURES = [
    "avg_kda",
    "avg_gold_per_min",
    "avg_xp_per_min",
    "avg_chat_messages",
    "avg_chat_length",
]


def main() -> None:
    print("NexusMatch - Preparing ML Trust Dataset")
    print("=" * 52)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Processed Dota file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = {"account_id", "matches_played", "leaver_rate", *FEATURES}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    before = len(df)

    df = df[df["matches_played"] >= MIN_MATCHES].copy()
    df = df.dropna(subset=FEATURES + ["leaver_rate"])
    df = df.drop_duplicates(subset=["account_id"])

    # Retrospective behavioural label for the first baseline experiment.
    df["reliable"] = (df["leaver_rate"] == 0).astype(int)

    result = df[
        [
            "account_id",
            "matches_played",
            *FEATURES,
            "leaver_rate",
            "reliable",
        ]
    ].copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    unreliable = int((result["reliable"] == 0).sum())
    reliable = int((result["reliable"] == 1).sum())

    print(f"Original player records : {before:,}")
    print(f"Players with >= {MIN_MATCHES} matches: {len(result):,}")
    print(f"Reliable (no leaver)     : {reliable:,}")
    print(f"Unreliable (has leaver)  : {unreliable:,}")
    print(
        f"Unreliable percentage    : "
        f"{(unreliable / len(result) * 100):.2f}%"
    )
    print(f"Saved ML dataset         : {OUTPUT_FILE}")

    print("\nFeature columns:")
    for feature in FEATURES:
        print(f"  - {feature}")

    print("\nTarget:")
    print("  reliable = 1 -> no recorded leaver event")
    print("  reliable = 0 -> at least one recorded leaver event")


if __name__ == "__main__":
    main()
