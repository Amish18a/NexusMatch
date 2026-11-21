from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.evaluation_service import (
    WAITING_SCORE_CAP_SECONDS,
    _waiting_score,
    run_policy_replay,
)


class EvaluationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seed_path = Path(__file__).resolve().parents[1] / "data" / "player_profiles.json"
        cls.profiles = json.loads(seed_path.read_text(encoding="utf-8"))

    @staticmethod
    def fake_trust(features: dict[str, float]) -> dict[str, float | str]:
        # Deterministic test double. This formula is not the production ML model.
        score = 100.0 * (
            0.35 * features["join_success_rate"]
            + 0.30 * features["completion_rate"]
            + 0.20 * (1.0 - features["disconnect_rate"])
            + 0.15 * (1.0 - features["queue_abandon_rate"])
        )
        score = max(0.0, min(100.0, score))
        return {
            "trust_score": score,
            "trust_label": "reliable" if score >= 70 else "unreliable",
        }

    def test_ten_profiles_produce_thirty_anchor_size_trials_for_each_policy(self) -> None:
        result = run_policy_replay(self.profiles, self.fake_trust)
        self.assertEqual(result["registry_size"], 10)
        self.assertEqual(result["attempted_trials"], 30)
        self.assertEqual(len(result["trials"]["skill_only"]), 30)
        self.assertEqual(len(result["trials"]["trust_aware"]), 30)
        self.assertEqual(len(result["trials"]["trust_aware_without_wait"]), 30)

    def test_each_successful_group_has_requested_size_and_unique_players(self) -> None:
        result = run_policy_replay(self.profiles, self.fake_trust)
        for policy_trials in result["trials"].values():
            for trial in policy_trials:
                selected = trial["selected_player_ids"]
                if selected:
                    self.assertEqual(len(selected), trial["match_size"])
                    self.assertEqual(len(selected), len(set(selected)))
                    self.assertEqual(selected[0], trial["anchor_player_id"])

    def test_eligibility_rules_are_respected(self) -> None:
        result = run_policy_replay(self.profiles, self.fake_trust)
        by_id = {int(p["player_id"]): p for p in self.profiles}
        for policy_trials in result["trials"].values():
            for trial in policy_trials:
                anchor = by_id[trial["anchor_player_id"]]
                for player_id in trial["selected_player_ids"][1:]:
                    candidate = by_id[player_id]
                    self.assertEqual(candidate["region"], anchor["region"])
                    self.assertEqual(candidate["game_mode"], anchor["game_mode"])
                    self.assertLessEqual(abs(candidate["skill_rating"] - anchor["skill_rating"]), 100)

    def test_pair_wait_score_uses_both_players_and_caps_each_at_100(self) -> None:
        anchor = {"queue_wait_seconds": 20}
        candidate = {"queue_wait_seconds": 140}
        self.assertEqual(_waiting_score(anchor, candidate), 60)
        self.assertEqual(WAITING_SCORE_CAP_SECONDS, 100)

    def test_waiting_component_isolated_from_other_policy_weights(self) -> None:
        result = run_policy_replay(self.profiles, self.fake_trust)
        waiting = result["comparison"]["waiting_time_effect"]
        self.assertEqual(waiting["comparable_trials"], 27)
        self.assertGreater(waiting["different_group_trials"], 0)
        self.assertIsNotNone(waiting["candidate_wait_delta_seconds"])

    def test_methodology_discloses_synthetic_queue_age_scenario(self) -> None:
        result = run_policy_replay(self.profiles, self.fake_trust)
        note = result["methodology"]["waiting_time_note"].lower()
        self.assertIn("synchronised", note)
        self.assertIn("synthetic", note)
        self.assertIn("not observed player waits", note)


if __name__ == "__main__":
    unittest.main()
