"""
NexusMatch - Convert simulated behaviour events into Trust training examples.

For every prediction point, features are calculated ONLY from prior sessions.

Target:
    future_unreliable_3 = 1 if at least one of the next three sessions is
    classified as unreliable.

A complete history and future window are required.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = (
    BASE_DIR
    / "data"
    / "nexusmatch_simulation"
    / "nexusmatch_behavior_events.csv"
)
OUTPUT_DIR = BASE_DIR / "data" / "ml"
OUTPUT_FILE = (
    OUTPUT_DIR
    / "nexusmatch_future_trust_dataset.csv"
)

MIN_HISTORY = 5
FUTURE_WINDOW = 3

FEATURES = [
    "history_sessions",
    "join_success_rate",
    "queue_abandon_rate",
    "completion_rate",
    "disconnect_rate",
    "reconnect_success_rate",
    "recent_3_join_success_rate",
    "recent_3_queue_abandon_rate",
    "recent_3_completion_rate",
    "recent_3_disconnect_rate",
    "recent_3_reconnect_success_rate",
    "avg_wait_time_sec",
    "avg_ping_ms",
    "avg_chat_messages",
]


def previous_expanding_mean(group: pd.Series) -> pd.Series:
    return group.shift(1).expanding().mean()


def previous_rolling_mean(
    group: pd.Series,
    window: int,
) -> pd.Series:
    return group.shift(1).rolling(
        window=window,
        min_periods=window,
    ).mean()


def future_window_max(
    group: pd.Series,
    window: int,
) -> pd.Series:
    return (
        group.iloc[::-1]
        .rolling(
            window=window,
            min_periods=window,
        )
        .max()
        .iloc[::-1]
    )


def main() -> None:
    print("NexusMatch - Prepare Simulated Trust Dataset")
    print("=" * 56)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing simulation data: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = {
        "player_id",
        "timestamp",
        "unreliable_session",
        "successful_joins",
        "join_attempts",
        "queue_entries",
        "queue_abandons",
        "matches_started",
        "matches_completed",
        "disconnects",
        "reconnects",
        "ping_ms",
        "wait_time_sec",
        "chat_messages",
    }

    missing = sorted(
        required.difference(df.columns)
    )
    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    df = (
        df.dropna(
            subset=["player_id", "timestamp"]
        )
        .sort_values(
            ["player_id", "timestamp"]
        )
        .reset_index(drop=True)
    )

    # Rates for a single session are represented as 0/1 because the generator
    # has one join attempt and one queue decision per session.
    df["join_success"] = df["successful_joins"]
    df["queue_abandon"] = df["queue_abandons"]

    df["completion"] = (
        (
            df["matches_started"] > 0
        )
        & (
            df["matches_completed"] > 0
        )
    ).astype(int)

    df["disconnect"] = (
        df["disconnects"] > 0
    ).astype(int)

    df["reconnect_success"] = (
        (
            df["disconnects"] > 0
        )
        & (
            df["reconnects"] > 0
        )
    ).astype(int)

    group = df.groupby(
        "player_id",
        sort=False,
    )

    df["history_sessions"] = group.cumcount()

    historical_columns = {
        "join_success": "join_success_rate",
        "queue_abandon": "queue_abandon_rate",
        "completion": "completion_rate",
        "disconnect": "disconnect_rate",
        "reconnect_success": "reconnect_success_rate",
        "wait_time_sec": "avg_wait_time_sec",
        "ping_ms": "avg_ping_ms",
        "chat_messages": "avg_chat_messages",
    }

    for source, destination in historical_columns.items():
        if source in {
            "wait_time_sec",
            "ping_ms",
            "chat_messages",
        }:
            df[destination] = group[source].transform(
                previous_expanding_mean
            )
        else:
            df[destination] = group[source].transform(
                previous_expanding_mean
            )

    recent_columns = {
        "join_success": "recent_3_join_success_rate",
        "queue_abandon": "recent_3_queue_abandon_rate",
        "completion": "recent_3_completion_rate",
        "disconnect": "recent_3_disconnect_rate",
        "reconnect_success": "recent_3_reconnect_success_rate",
    }

    for source, destination in recent_columns.items():
        df[destination] = group[source].transform(
            lambda s, window=3: previous_rolling_mean(
                s,
                window,
            )
        )

    df["future_unreliable_rate_3"] = group[
        "unreliable_session"
    ].transform(
        lambda s: future_window_max(
            s,
            FUTURE_WINDOW,
        )
    )

    df["future_unreliable_3"] = (
        df["future_unreliable_rate_3"]
        .gt(0)
        .astype("Int64")
    )

    df["future_window_end"] = group["timestamp"].transform(
        lambda s: s.shift(
            -(FUTURE_WINDOW - 1)
        )
    )

    df = df[
        (df["history_sessions"] >= MIN_HISTORY)
        & df["future_unreliable_rate_3"].notna()
        & df["future_window_end"].notna()
    ].copy()

    df = df.dropna(
        subset=FEATURES
    ).copy()

    output_columns = [
        "player_id",
        "timestamp",
        "future_window_end",
        *FEATURES,
        "future_unreliable_3",
    ]

    result = df[output_columns].copy()
    result["future_unreliable_3"] = (
        result["future_unreliable_3"]
        .astype(int)
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    positive = int(
        result["future_unreliable_3"].sum()
    )
    negative = len(result) - positive

    print(
        f"Prediction examples     : {len(result):,}"
    )
    print(
        f"Future unreliable        : {positive:,}"
    )
    print(
        f"Future reliable          : {negative:,}"
    )
    print(
        f"Positive rate            : "
        f"{positive / len(result) * 100:.2f}%"
    )
    print(
        f"Unique players           : "
        f"{result['player_id'].nunique():,}"
    )
    print(
        f"Saved                    : {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
