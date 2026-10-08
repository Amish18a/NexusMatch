"""
NexusMatch - Synthetic behavioural event generator.

Purpose
-------
Generate a controlled NexusMatch-specific behavioural dataset for Phase 2.
This is NOT a replacement for real player telemetry. It is a simulation used
to test the Trust pipeline before the real server/Docker layer is available.

Each row represents one player session/match cycle.

Events recorded:
    - join attempt
    - join success/failure
    - queue entry/abandonment
    - match start/completion
    - disconnect/reconnect
    - wait time and ping
    - chat activity count

The generator uses hidden player reliability profiles only to create realistic
correlations between events. The hidden profile is deliberately NOT written
to the exported dataset.

Outputs:
    data/nexusmatch_simulation/nexusmatch_behavior_events.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "nexusmatch_simulation"
OUTPUT_FILE = OUTPUT_DIR / "nexusmatch_behavior_events.csv"

SEED = 42
NUM_PLAYERS = 5000
MIN_SESSIONS = 15
MAX_SESSIONS = 35
START_DATE = pd.Timestamp("2026-01-01", tz="UTC")

PLAYER_TYPES = {
    "highly_reliable": {
        "weight": 0.30,
        "join_failure": 0.01,
        "queue_abandon": 0.02,
        "disconnect": 0.02,
        "reconnect": 0.95,
    },
    "reliable": {
        "weight": 0.45,
        "join_failure": 0.03,
        "queue_abandon": 0.05,
        "disconnect": 0.04,
        "reconnect": 0.90,
    },
    "unstable": {
        "weight": 0.20,
        "join_failure": 0.08,
        "queue_abandon": 0.12,
        "disconnect": 0.12,
        "reconnect": 0.75,
    },
    "unreliable": {
        "weight": 0.05,
        "join_failure": 0.18,
        "queue_abandon": 0.25,
        "disconnect": 0.25,
        "reconnect": 0.55,
    },
}


def choose_player_type(rng: np.random.Generator) -> str:
    names = list(PLAYER_TYPES)
    probabilities = [
        PLAYER_TYPES[name]["weight"]
        for name in names
    ]
    return str(rng.choice(names, p=probabilities))


def bounded_probability(
    base: float,
    session_number: int,
    rng: np.random.Generator,
) -> float:
    """
    Add small session-to-session variation while keeping the probability valid.
    """
    drift = 0.004 * np.sin(session_number / 3.0)
    noise = rng.normal(0.0, 0.005)
    return float(np.clip(base + drift + noise, 0.001, 0.95))


def generate_events() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []

    for player_id in range(1, NUM_PLAYERS + 1):
        profile_name = choose_player_type(rng)
        profile = PLAYER_TYPES[profile_name]

        sessions = int(
            rng.integers(
                MIN_SESSIONS,
                MAX_SESSIONS + 1,
            )
        )

        player_start = START_DATE + pd.Timedelta(
            minutes=int(rng.integers(0, 60 * 24 * 30))
        )

        for session_number in range(1, sessions + 1):
            session_id = f"P{player_id:05d}-S{session_number:03d}"

            timestamp = (
                player_start
                + pd.Timedelta(
                    hours=int(rng.integers(2, 30))
                    * (session_number - 1)
                )
                + pd.Timedelta(
                    minutes=int(rng.integers(0, 45))
                )
            )

            join_attempt = 1

            join_failure_probability = bounded_probability(
                profile["join_failure"],
                session_number,
                rng,
            )

            join_failure = int(
                rng.random() < join_failure_probability
            )
            join_success = int(join_failure == 0)

            queue_entry = int(join_success == 1)

            queue_abandon = 0
            if queue_entry:
                queue_abandon_probability = bounded_probability(
                    profile["queue_abandon"],
                    session_number,
                    rng,
                )
                queue_abandon = int(
                    rng.random() < queue_abandon_probability
                )

            match_started = int(
                queue_entry == 1 and queue_abandon == 0
            )

            disconnect_probability = bounded_probability(
                profile["disconnect"],
                session_number,
                rng,
            )

            disconnects = 0
            reconnects = 0
            match_completed = 0

            if match_started:
                disconnects = int(
                    rng.random() < disconnect_probability
                )

                if disconnects:
                    reconnects = int(
                        rng.random() < profile["reconnect"]
                    )

                match_completed = int(
                    rng.random()
                    < (
                        0.995
                        - 0.40 * disconnects
                        + 0.10 * reconnects
                    )
                )

            ping_ms = int(
                np.clip(
                    rng.normal(65, 25),
                    20,
                    220,
                )
            )

            wait_seconds = int(
                np.clip(
                    rng.normal(45, 20),
                    5,
                    180,
                )
            )

            if queue_abandon:
                wait_seconds = max(
                    wait_seconds,
                    int(
                        rng.normal(90, 25)
                    ),
                )

            chat_messages = int(
                rng.poisson(
                    2.0
                    + 2.0 * match_started
                    + 1.0 * disconnects
                )
            )

            rows.append(
                {
                    "player_id": player_id,
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "session_number": session_number,
                    "join_attempts": join_attempt,
                    "successful_joins": join_success,
                    "failed_joins": join_failure,
                    "queue_entries": queue_entry,
                    "queue_abandons": queue_abandon,
                    "matches_started": match_started,
                    "matches_completed": match_completed,
                    "disconnects": disconnects,
                    "reconnects": reconnects,
                    "ping_ms": ping_ms,
                    "wait_time_sec": wait_seconds,
                    "chat_messages": chat_messages,
                }
            )

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["player_id", "timestamp", "session_number"]
        )
        .reset_index(drop=True)
    )


def add_session_level_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add a behavioural bad-session indicator for analysis only."""
    df = df.copy()

    df["unreliable_session"] = (
        (df["failed_joins"] > 0)
        | (df["queue_abandons"] > 0)
        | (df["disconnects"] > 0)
        | (
            (df["matches_started"] > 0)
            & (df["matches_completed"] == 0)
        )
    ).astype(int)

    return df


def main() -> None:
    print("NexusMatch - Behaviour Event Generator")
    print("=" * 52)

    data = generate_events()
    data = add_session_level_labels(data)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    data.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(f"Players generated       : {data['player_id'].nunique():,}")
    print(f"Sessions generated      : {len(data):,}")
    print(
        "Unreliable sessions     : "
        f"{data['unreliable_session'].sum():,}"
    )
    print(
        "Unreliable rate         : "
        f"{data['unreliable_session'].mean() * 100:.2f}%"
    )
    print(f"Saved                   : {OUTPUT_FILE}")

    print("\nEvent columns:")
    print(", ".join(data.columns))


if __name__ == "__main__":
    main()
