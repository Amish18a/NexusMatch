import csv
from pathlib import Path


DATA_FILE = Path(__file__).parent / "data" / "player_behavior.csv"


# Weights for the Phase 2 baseline Trust Score.
JOIN_WEIGHT = 0.35
COMPLETION_WEIGHT = 0.30
STABILITY_WEIGHT = 0.20
QUEUE_WEIGHT = 0.15


def safe_ratio(numerator, denominator):
    """Return a ratio safely when the denominator can be zero."""
    if denominator == 0:
        return 1.0
    return numerator / denominator


def calculate_trust_score(player):
    """Calculate a baseline reliability score between 0 and 100."""
    join_reliability = safe_ratio(
        int(player["successful_joins"]), int(player["join_attempts"])
    )

    completion_rate = safe_ratio(
        int(player["matches_completed"]), int(player["matches_started"])
    )

    connection_stability = 1 - safe_ratio(
        int(player["disconnects"]), int(player["matches_started"])
    )

    queue_reliability = 1 - safe_ratio(
        int(player["queue_abandons"]), int(player["queue_entries"])
    )

    score = (
        join_reliability * JOIN_WEIGHT
        + completion_rate * COMPLETION_WEIGHT
        + connection_stability * STABILITY_WEIGHT
        + queue_reliability * QUEUE_WEIGHT
    ) * 100

    return round(max(0, min(100, score)), 2)


def load_players():
    with DATA_FILE.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main():
    players = load_players()

    print("NexusMatch - Phase 2 Trust Score Prototype")
    print("=" * 48)

    for player in players:
        score = calculate_trust_score(player)
        print(f"{player['player_name']:<10} Trust Score: {score:>6.2f}")


if __name__ == "__main__":
    main()
