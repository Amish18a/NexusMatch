from __future__ import annotations

import unittest
from unittest.mock import patch

from app import main


class WaitingTimeSyncTests(unittest.TestCase):
    def test_live_queue_age_is_sent_to_cpp_and_returned_in_status(self) -> None:
        first_players = [
            {
                "player_id": 101,
                "name": "Amish",
                "in_queue": 1,
                "queue_wait_seconds": 39.8,
                "trust_score": 91.0,
            }
        ]
        refreshed_players = [
            {
                "player_id": 101,
                "name": "Amish",
                "in_queue": 1,
                "queue_wait_seconds": 39.9,
                "trust_score": 91.0,
            }
        ]
        status = {
            "players": [
                {"id": "101", "connected": "yes", "waiting": "yes", "wait_sec": "0"}
            ],
            "queue_size": 1,
        }
        updated_status = {
            "players": [
                {"id": "101", "connected": "yes", "waiting": "yes", "wait_sec": "39"}
            ],
            "queue_size": 1,
        }

        with (
            patch.object(main.database, "get_session_players", side_effect=[first_players, refreshed_players]),
            patch.object(main.database, "get_active_match_for_player", return_value=None),
            patch.object(main, "cpp_command", side_effect=["STATUS players=1 queue=1 last_match=0", "OK WAIT_SET 39", "STATUS players=1 queue=1 last_match=0"] ) as cpp,
            patch.object(main, "parse_status", side_effect=[status, updated_status]),
            patch.object(main, "write_log"),
        ):
            actual_status, actual_session = main.synchronize_live_queue_wait_times()

        self.assertEqual(cpp.call_args_list[1].args[0], "SET_WAIT 101 39")
        self.assertEqual(actual_status["players"][0]["wait_sec"], "39")
        self.assertEqual(actual_session[0]["cpp_waiting_time_seconds"], "39")

    def test_wait_sync_does_not_send_commands_for_nonwaiting_players(self) -> None:
        with (
            patch.object(main.database, "get_session_players", return_value=[
                {"player_id": 101, "in_queue": 0, "queue_wait_seconds": 0}
            ]),
            patch.object(main, "cpp_command", return_value="STATUS players=0 queue=0 last_match=0") as cpp,
            patch.object(main, "parse_status", return_value={"players": [], "queue_size": 0}),
        ):
            main.synchronize_live_queue_wait_times()

        self.assertEqual(cpp.call_count, 1)
        self.assertEqual(cpp.call_args.args[0], "SHOW_ALL")


if __name__ == "__main__":
    unittest.main()
