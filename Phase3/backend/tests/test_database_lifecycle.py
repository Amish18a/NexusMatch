from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import database


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = PROJECT_ROOT / "backend" / "data" / "player_profiles.json"


class DatabaseLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "phase3_test.db"
        self.db_path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.seed_path_patch = patch.object(database, "PROFILE_SEED_PATH", SEED_PATH)
        self.db_path_patch.start()
        self.seed_path_patch.start()
        self.addCleanup(self.db_path_patch.stop)
        self.addCleanup(self.seed_path_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        database.init_db()
        self.profiles = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    def _connect_players(self, player_ids: list[int]) -> None:
        by_id = {int(profile["player_id"]): profile for profile in self.profiles}
        for player_id in player_ids:
            profile = by_id[player_id]
            database.add_session_player(
                profile,
                server_rtt_ms=12.5,
                player_ping_ms=float(profile["features"].get("avg_ping_ms", 0.0)),
                trust={
                    "trust_score": 82.0,
                    "unreliable_risk": 0.18,
                    "trust_label": "reliable",
                },
            )
            database.set_queue_state(player_id, True)

    def test_match_lifecycle_releases_players_and_keeps_history(self) -> None:
        player_ids = [101, 102, 103]
        self._connect_players(player_ids)

        first = database.save_match(
            cpp_match_id=1,
            anchor_id=101,
            match_size=3,
            player_ids=player_ids,
            response="MATCH 1 CREATED players=101,102,103",
            cpp_latency_ms=4.2,
        )
        first_api_id = first["match_id"]
        self.assertEqual(first["cpp_match_id"], 1)
        self.assertEqual(database.get_active_match_for_player(101), first_api_id)
        self.assertEqual(database.get_session_player(101)["in_queue"], 0)
        self.assertIsNone(database.get_session_player(101)["queue_entered_at"])

        self.assertTrue(database.set_match_status(first_api_id, "COMPLETED"))
        self.assertIsNone(database.get_active_match_for_player(101))
        self.assertFalse(database.set_match_status(first_api_id, "CANCELLED"))

        # The C++ process-local match counter starts from 1 again after restart.
        # The persistent API/history identifier must not overwrite the first row.
        for player_id in player_ids:
            database.set_queue_state(player_id, True)
        second = database.save_match(
            cpp_match_id=1,
            anchor_id=101,
            match_size=3,
            player_ids=player_ids,
            response="MATCH 1 CREATED players=101,102,103",
            cpp_latency_ms=3.9,
        )
        second_api_id = second["match_id"]

        self.assertGreater(second_api_id, first_api_id)
        self.assertEqual(second["cpp_match_id"], 1)
        matches = database.get_matches(10)
        self.assertEqual(len(matches), 2)
        by_api_id = {match["match_id"]: match for match in matches}
        self.assertEqual(by_api_id[first_api_id]["status"], "COMPLETED")
        self.assertEqual(by_api_id[first_api_id]["cpp_match_id"], 1)
        self.assertEqual(by_api_id[second_api_id]["status"], "ACTIVE")
        self.assertEqual(database.get_active_match_for_player(102), second_api_id)

    def test_legacy_match_rows_are_migrated_without_losing_their_id(self) -> None:
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("DROP TABLE IF EXISTS matches")
            connection.execute(
                """CREATE TABLE matches (
                    match_id INTEGER PRIMARY KEY,
                    anchor_player_id INTEGER NOT NULL,
                    match_size INTEGER NOT NULL,
                    player_ids_json TEXT NOT NULL,
                    server_response TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """INSERT INTO matches
                   (match_id, anchor_player_id, match_size, player_ids_json, server_response, created_at)
                   VALUES (7, 101, 3, '[101,102,103]', 'MATCH 7 CREATED', '2026-11-01T00:00:00+00:00')"""
            )
            connection.commit()
        finally:
            connection.close()

        database.init_db()
        migrated = database.get_matches(10)
        self.assertEqual(len(migrated), 1)
        self.assertEqual(migrated[0]["match_id"], 7)
        self.assertEqual(migrated[0]["cpp_match_id"], 7)
        self.assertEqual(migrated[0]["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
