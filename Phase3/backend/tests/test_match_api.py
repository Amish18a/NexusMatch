from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import database, main
from app.main import MatchRequest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = PROJECT_ROOT / "backend" / "data" / "player_profiles.json"


class MatchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "match_api_test.db"
        self.db_path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.seed_path_patch = patch.object(database, "PROFILE_SEED_PATH", SEED_PATH)
        self.db_path_patch.start()
        self.seed_path_patch.start()
        self.addCleanup(self.db_path_patch.stop)
        self.addCleanup(self.seed_path_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        database.init_db()
        self.profiles = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        by_id = {int(profile["player_id"]): profile for profile in self.profiles}
        for player_id in (101, 102, 103):
            profile = by_id[player_id]
            database.add_session_player(
                profile,
                server_rtt_ms=10.0,
                player_ping_ms=float(profile["features"].get("avg_ping_ms", 0.0)),
                trust={"trust_score": 85.0, "unreliable_risk": 0.15, "trust_label": "reliable"},
            )
            database.set_queue_state(player_id, True)

    def test_create_match_keeps_history_when_cpp_match_counter_restarts(self) -> None:
        with (
            patch.object(main, "synchronize_live_queue_wait_times", return_value=({}, [])),
            patch.object(main, "cpp_command", return_value="MATCH 1 CREATED players=101,102,103"),
            patch.object(main, "write_log"),
        ):
            first = main.create_match(MatchRequest(anchor_player_id=101, match_size=3))

        self.assertEqual(first["cpp_match_id"], 1)
        first_api_id = first["match_id"]
        self.assertGreater(first_api_id, 0)
        self.assertEqual(database.get_active_match_for_player(101), first_api_id)

        self.assertTrue(database.set_match_status(first_api_id, "COMPLETED"))
        for player_id in (101, 102, 103):
            database.set_queue_state(player_id, True)

        # Simulate a restarted C++ process returning its first local match ID again.
        with (
            patch.object(main, "synchronize_live_queue_wait_times", return_value=({}, [])),
            patch.object(main, "cpp_command", return_value="MATCH 1 CREATED players=101,102,103"),
            patch.object(main, "write_log"),
        ):
            second = main.create_match(MatchRequest(anchor_player_id=101, match_size=3))

        self.assertEqual(second["cpp_match_id"], 1)
        self.assertGreater(second["match_id"], first_api_id)
        history = database.get_matches(10)
        self.assertEqual(len(history), 2)
        by_id = {row["match_id"]: row for row in history}
        self.assertEqual(by_id[first_api_id]["status"], "COMPLETED")
        self.assertEqual(by_id[first_api_id]["cpp_match_id"], 1)
        self.assertEqual(by_id[second["match_id"]]["status"], "ACTIVE")


    def test_http_session_queue_match_and_history_flow(self) -> None:
        cpp_players: dict[int, dict[str, object]] = {}

        def fake_cpp_command(command: str) -> str:
            parts = command.split()
            operation = parts[0]
            if operation == "SHOW_ALL":
                player_rows = []
                for player_id, state in sorted(cpp_players.items()):
                    player_rows.append(
                        "player=" + str(player_id)
                        + f",name={state['name']},skill={state['skill']},region={state['region']},"
                        + f"mode={state['mode']},connected=yes,waiting={state['waiting']},"
                        + f"trust={state['trust']},wait_sec={state['wait_sec']}"
                    )
                queue_count = sum(1 for state in cpp_players.values() if state["waiting"] == "yes")
                return "STATUS players={} queue={} last_match=1 matched= | {}".format(
                    len(cpp_players), queue_count, " | ".join(player_rows)
                )
            if operation == "CONNECT":
                player_id = int(parts[1])
                cpp_players[player_id] = {
                    "name": parts[2], "skill": parts[3], "region": parts[4],
                    "mode": parts[5], "waiting": "no", "trust": "100", "wait_sec": "0",
                }
                return f"OK CONNECTED {player_id}"
            if operation == "SET_TRUST":
                cpp_players[int(parts[1])]["trust"] = parts[2]
                return f"OK TRUST_SET {parts[1]}"
            if operation == "SET_WAIT":
                cpp_players[int(parts[1])]["wait_sec"] = parts[2]
                return f"OK WAIT_SET {parts[2]}"
            if operation == "QUEUE":
                cpp_players[int(parts[1])]["waiting"] = "yes"
                return f"OK QUEUED {parts[1]}"
            if operation == "ABANDON":
                cpp_players[int(parts[1])]["waiting"] = "no"
                return f"OK ABANDONED {parts[1]}"
            if operation == "MATCHMAKE":
                anchor_id, group_size = int(parts[1]), int(parts[2])
                waiting = [pid for pid, state in sorted(cpp_players.items()) if state["waiting"] == "yes"]
                if anchor_id not in waiting or len(waiting) < group_size:
                    return "ERROR MATCHMAKE insufficient queued players"
                selected = [anchor_id] + [pid for pid in waiting if pid != anchor_id][:group_size - 1]
                for pid in selected:
                    cpp_players[pid]["waiting"] = "no"
                # Deliberately reuse local ID 1 to simulate a restarted server.
                return "MATCH 1 CREATED players=" + ",".join(map(str, selected))
            raise AssertionError(f"Unexpected fake C++ command: {command}")

        with (
            patch.object(main, "cpp_command", side_effect=fake_cpp_command),
            patch.object(main, "measure_rtt", return_value=11.5),
            patch.object(main, "predict_profile_trust", return_value={
                "trust_score": 88.0, "unreliable_risk": 0.12,
                "trust_label": "reliable", "threshold": 0.5,
            }),
        ):
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/api/health").status_code, 200)
                for player in self.profiles[:3]:
                    response = client.post(
                        "/api/session/players",
                        json={"player_id": player["player_id"], "name": player["name"]},
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    queue = client.post(f"/api/queue/{player['player_id']}/join")
                    self.assertEqual(queue.status_code, 200, queue.text)

                first = client.post("/api/matches", json={"anchor_player_id": 101, "match_size": 3})
                self.assertEqual(first.status_code, 200, first.text)
                first_body = first.json()
                self.assertEqual(first_body["cpp_match_id"], 1)
                self.assertEqual(first_body["player_ids"], [101, 102, 103])

                ended = client.post(f"/api/matches/{first_body['match_id']}/end")
                self.assertEqual(ended.status_code, 200, ended.text)
                for player_id in (101, 102, 103):
                    queue = client.post(f"/api/queue/{player_id}/join")
                    self.assertEqual(queue.status_code, 200, queue.text)

                second = client.post("/api/matches", json={"anchor_player_id": 101, "match_size": 3})
                self.assertEqual(second.status_code, 200, second.text)
                second_body = second.json()
                self.assertEqual(second_body["cpp_match_id"], 1)
                self.assertGreater(second_body["match_id"], first_body["match_id"])

                history = client.get("/api/matches").json()["matches"]
                self.assertEqual(len(history), 2)
                by_id = {item["match_id"]: item for item in history}
                self.assertEqual(by_id[first_body["match_id"]]["status"], "COMPLETED")
                self.assertEqual(by_id[second_body["match_id"]]["status"], "ACTIVE")

    def test_match_size_is_validated_before_contacting_cpp(self) -> None:
        with patch.object(main, "cpp_command") as cpp:
            with self.assertRaises(HTTPException) as raised:
                main.create_match(MatchRequest(anchor_player_id=101, match_size=2))
        self.assertEqual(raised.exception.status_code, 422)
        cpp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
