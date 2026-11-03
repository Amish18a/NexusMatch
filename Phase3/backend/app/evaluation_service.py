from __future__ import annotations

from statistics import mean
from typing import Any, Callable


SKILL_ONLY_WEIGHTS = {"skill": 1.0, "ping": 0.0, "trust": 0.0, "waiting": 0.0}
TRUST_AWARE_WEIGHTS = {"skill": 0.50, "ping": 0.20, "trust": 0.20, "waiting": 0.10}
# Renormalise the non-wait factors proportionally, so this comparison isolates
# the effect of the 10% waiting component instead of changing the other ratios.
TRUST_AWARE_NO_WAIT_WEIGHTS = {
    "skill": 0.50 / 0.90,
    "ping": 0.20 / 0.90,
    "trust": 0.20 / 0.90,
    "waiting": 0.0,
}
SKILL_TOLERANCE = 100
SUPPORTED_MATCH_SIZES = (3, 4, 5)
WAITING_SCORE_CAP_SECONDS = 100


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _skill_score(anchor: dict[str, Any], candidate: dict[str, Any]) -> float:
    difference = abs(int(anchor["skill_rating"]) - int(candidate["skill_rating"]))
    return _clamp_score(100.0 - difference / 5.0)


def _ping_score(anchor: dict[str, Any], candidate: dict[str, Any]) -> float:
    difference = abs(float(anchor["profile_ping_ms"]) - float(candidate["profile_ping_ms"]))
    return _clamp_score(100.0 - difference)


def _trust_score(anchor: dict[str, Any], candidate: dict[str, Any]) -> float:
    return _clamp_score((float(anchor["trust_score"]) + float(candidate["trust_score"])) / 2.0)


def _waiting_score(anchor: dict[str, Any], candidate: dict[str, Any]) -> float:
    anchor_wait = min(max(0.0, float(anchor.get("queue_wait_seconds", 0.0))), WAITING_SCORE_CAP_SECONDS)
    candidate_wait = min(max(0.0, float(candidate.get("queue_wait_seconds", 0.0))), WAITING_SCORE_CAP_SECONDS)
    return (anchor_wait + candidate_wait) / 2.0


def _candidate_score(
    anchor: dict[str, Any],
    candidate: dict[str, Any],
    weights: dict[str, float],
) -> float:
    return (
        _skill_score(anchor, candidate) * weights["skill"]
        + _ping_score(anchor, candidate) * weights["ping"]
        + _trust_score(anchor, candidate) * weights["trust"]
        + _waiting_score(anchor, candidate) * weights["waiting"]
    )


def _eligible(anchor: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if int(anchor["player_id"]) == int(candidate["player_id"]):
        return False
    if anchor["region"] != candidate["region"]:
        return False
    if anchor["game_mode"] != candidate["game_mode"]:
        return False
    return abs(int(anchor["skill_rating"]) - int(candidate["skill_rating"])) <= SKILL_TOLERANCE


def _select_group(
    profiles: list[dict[str, Any]],
    anchor: dict[str, Any],
    match_size: int,
    weights: dict[str, float],
) -> list[dict[str, Any]] | None:
    candidates = [p for p in profiles if _eligible(anchor, p)]
    if len(candidates) < match_size - 1:
        return None

    # The waiting term is pair-based: both the anchor and each candidate
    # contribute their capped live/simulated queue age. Candidate age therefore
    # changes ranking instead of adding the same constant to every candidate.
    ranked = sorted(
        candidates,
        key=lambda p: (
            -_candidate_score(anchor, p, weights),
            # Do not leak disabled factors into tie-breaking. Player ID is the
            # only deterministic tie-break shared by all policies.
            int(p["player_id"]),
        ),
    )
    return [anchor, *ranked[: match_size - 1]]


def _group_metrics(group: list[dict[str, Any]], anchor: dict[str, Any]) -> dict[str, float | int]:
    skills = [int(p["skill_rating"]) for p in group]
    pings = [float(p["profile_ping_ms"]) for p in group]
    trusts = [float(p["trust_score"]) for p in group]
    waits = [max(0.0, float(p.get("queue_wait_seconds", 0.0))) for p in group]
    candidate_waits = [
        max(0.0, float(p.get("queue_wait_seconds", 0.0)))
        for p in group if int(p["player_id"]) != int(anchor["player_id"])
    ]
    anchor_skill = int(anchor["skill_rating"])
    anchor_gaps = [abs(int(p["skill_rating"]) - anchor_skill) for p in group if p["player_id"] != anchor["player_id"]]
    pairwise_gaps = [
        abs(skills[i] - skills[j])
        for i in range(len(skills))
        for j in range(i + 1, len(skills))
    ]
    return {
        "group_skill_spread": max(skills) - min(skills),
        "mean_anchor_skill_gap": round(mean(anchor_gaps), 3) if anchor_gaps else 0.0,
        "mean_pairwise_skill_gap": round(mean(pairwise_gaps), 3) if pairwise_gaps else 0.0,
        "mean_profile_ping_ms": round(mean(pings), 3),
        "profile_ping_spread_ms": round(max(pings) - min(pings), 3),
        "mean_trust_score": round(mean(trusts), 3),
        "low_trust_players": sum(1 for value in trusts if value < 60.0),
        "mean_queue_wait_seconds": round(mean(waits), 3),
        "mean_candidate_wait_seconds": round(mean(candidate_waits), 3) if candidate_waits else 0.0,
        "max_queue_wait_seconds": round(max(waits), 3),
    }


def _aggregate(trials: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [t for t in trials if t["selected_player_ids"]]
    metric_keys = (
        "group_skill_spread",
        "mean_anchor_skill_gap",
        "mean_pairwise_skill_gap",
        "mean_profile_ping_ms",
        "profile_ping_spread_ms",
        "mean_trust_score",
        "mean_queue_wait_seconds",
        "mean_candidate_wait_seconds",
        "max_queue_wait_seconds",
    )
    result: dict[str, Any] = {
        "trials_attempted": len(trials),
        "trials_succeeded": len(successful),
        "success_rate_percent": round(100.0 * len(successful) / len(trials), 2) if trials else 0.0,
    }
    for key in metric_keys:
        values = [float(t["metrics"][key]) for t in successful]
        result[key] = round(mean(values), 3) if values else None
    total_members = sum(len(t["selected_player_ids"]) for t in successful)
    low_trust_members = sum(int(t["metrics"]["low_trust_players"]) for t in successful)
    result["low_trust_member_rate_percent"] = (
        round(100.0 * low_trust_members / total_members, 2) if total_members else None
    )
    breakdown: dict[str, Any] = {}
    for size in SUPPORTED_MATCH_SIZES:
        subset = [t for t in successful if t["match_size"] == size]
        breakdown[str(size)] = {
            "successful_trials": len(subset),
            "mean_skill_spread": round(mean([t["metrics"]["group_skill_spread"] for t in subset]), 3) if subset else None,
            "mean_ping_spread_ms": round(mean([t["metrics"]["profile_ping_spread_ms"] for t in subset]), 3) if subset else None,
            "mean_trust_score": round(mean([t["metrics"]["mean_trust_score"] for t in subset]), 3) if subset else None,
            "mean_queue_wait_seconds": round(mean([t["metrics"]["mean_queue_wait_seconds"] for t in subset]), 3) if subset else None,
        }
    result["match_size_breakdown"] = breakdown
    return result


def run_policy_replay(
    registry_profiles: list[dict[str, Any]],
    trust_predictor: Callable[[dict[str, float]], dict[str, Any]],
) -> dict[str, Any]:
    """Replay selection policies over fixed profiles and controlled queue ages.

    This is an offline dry run. It does not invoke C++, change the live queue,
    or create match-history records. Synthetic queue ages are assigned solely
    to verify the waiting component's effect on candidate ranking.
    """
    ordered_profiles = sorted(registry_profiles, key=lambda p: int(p["player_id"]))
    enriched: list[dict[str, Any]] = []
    for index, profile in enumerate(ordered_profiles):
        prediction = trust_predictor(profile["features"])
        enriched.append({
            "player_id": int(profile["player_id"]),
            "name": str(profile["name"]),
            "skill_rating": int(profile["skill_rating"]),
            "region": str(profile["region"]),
            "game_mode": str(profile["game_mode"]),
            "profile_ping_ms": float(profile["features"].get("avg_ping_ms", 0.0)),
            "trust_score": float(prediction["trust_score"]),
            "trust_label": str(prediction.get("trust_label", "unknown")),
            # Controlled test input; this is not the player's real/live queue age.
            "queue_wait_seconds": float(index * 15),
        })

    profiles = sorted(enriched, key=lambda p: (p["skill_rating"], p["player_id"]))
    policies = {
        "skill_only": SKILL_ONLY_WEIGHTS,
        "trust_aware": TRUST_AWARE_WEIGHTS,
        "trust_aware_without_wait": TRUST_AWARE_NO_WAIT_WEIGHTS,
    }
    policy_trials: dict[str, list[dict[str, Any]]] = {name: [] for name in policies}

    for match_size in SUPPORTED_MATCH_SIZES:
        for anchor in profiles:
            for policy_name, weights in policies.items():
                selected = _select_group(profiles, anchor, match_size, weights)
                ids = [int(p["player_id"]) for p in selected] if selected else []
                policy_trials[policy_name].append({
                    "anchor_player_id": int(anchor["player_id"]),
                    "anchor_name": anchor["name"],
                    "match_size": match_size,
                    "anchor_queue_wait_seconds": anchor["queue_wait_seconds"],
                    "selected_player_ids": ids,
                    "selected_names": [p["name"] for p in selected] if selected else [],
                    "selected_queue_wait_seconds": [p["queue_wait_seconds"] for p in selected] if selected else [],
                    "metrics": _group_metrics(selected, anchor) if selected else {},
                })

    def compare_policies(left_name: str, right_name: str) -> dict[str, Any]:
        left_by_key = {
            (t["anchor_player_id"], t["match_size"]): t
            for t in policy_trials[left_name]
        }
        right_by_key = {
            (t["anchor_player_id"], t["match_size"]): t
            for t in policy_trials[right_name]
        }
        comparable = 0
        changed = 0
        for key, left_trial in left_by_key.items():
            right_trial = right_by_key[key]
            if left_trial["selected_player_ids"] and right_trial["selected_player_ids"]:
                comparable += 1
                if left_trial["selected_player_ids"] != right_trial["selected_player_ids"]:
                    changed += 1
        return {
            "comparable_trials": comparable,
            "different_group_trials": changed,
            "different_group_rate_percent": round(100.0 * changed / comparable, 2) if comparable else None,
            "left_mean_candidate_wait_seconds": _aggregate(policy_trials[left_name])["mean_candidate_wait_seconds"],
            "right_mean_candidate_wait_seconds": _aggregate(policy_trials[right_name])["mean_candidate_wait_seconds"],
        }

    summaries = {name: _aggregate(trials) for name, trials in policy_trials.items()}
    skill_summary = summaries["skill_only"]
    trust_summary = summaries["trust_aware"]

    def delta(field: str) -> float | None:
        left, right = skill_summary.get(field), trust_summary.get(field)
        if left is None or right is None:
            return None
        return round(float(right) - float(left), 3)

    main_comparison = compare_policies("skill_only", "trust_aware")
    waiting_effect = compare_policies("trust_aware_without_wait", "trust_aware")
    waiting_effect["mean_candidate_wait_seconds_without_wait"] = waiting_effect.pop("left_mean_candidate_wait_seconds")
    waiting_effect["mean_candidate_wait_seconds_with_wait"] = waiting_effect.pop("right_mean_candidate_wait_seconds")
    waiting_effect["candidate_wait_delta_seconds"] = (
        round(
            float(waiting_effect["mean_candidate_wait_seconds_with_wait"])
            - float(waiting_effect["mean_candidate_wait_seconds_without_wait"]),
            3,
        )
        if waiting_effect["mean_candidate_wait_seconds_with_wait"] is not None
        and waiting_effect["mean_candidate_wait_seconds_without_wait"] is not None
        else None
    )

    return {
        "registry_size": len(profiles),
        "attempted_trials": len(SUPPORTED_MATCH_SIZES) * len(profiles),
        "comparison": {
            **main_comparison,
            "different_group_trials": main_comparison["different_group_trials"],
            "trust_aware_minus_skill_only": {
                "mean_group_skill_spread": delta("group_skill_spread"),
                "mean_profile_ping_spread_ms": delta("profile_ping_spread_ms"),
                "mean_trust_score": delta("mean_trust_score"),
                "mean_pairwise_skill_gap": delta("mean_pairwise_skill_gap"),
                "mean_queue_wait_seconds": delta("mean_queue_wait_seconds"),
            },
            "waiting_time_effect": waiting_effect,
        },
        "strategies": summaries,
        "trials": policy_trials,
        "methodology": {
            "type": "offline deterministic policy replay; no live matches are created",
            "eligibility": "same region, same game mode, and skill difference within +/-100 of the anchor",
            "skill_only_weights": SKILL_ONLY_WEIGHTS,
            "trust_aware_weights": TRUST_AWARE_WEIGHTS,
            "trust_aware_without_wait_weights": TRUST_AWARE_NO_WAIT_WEIGHTS,
            "trust_source": "the existing Phase 2 saved Logistic Regression model applied to each predefined profile feature vector",
            "ping_source": "predefined player profile average ping; not the gateway/server RTT",
            "waiting_time_note": (
                "Live queue age is now synchronised from Phase 3 queue_entered_at into the C++ Player, Queue, AVL Tree and Hash Table before matching. "
                "The C++ score uses the average of the anchor and candidate's waiting score, each capped at 100 seconds, with a 10% weight. "
                "This offline replay uses a controlled synthetic queue-age scenario (0–135 seconds in 15-second steps by profile ID) to test the ranking effect; these are not observed player waits."
            ),
            "replay_note": "Each anchor and match-size combination is an independent trial; the same profile can appear in multiple trials. Exact score ties are resolved by player ID for reproducibility; the production C++ AVL traversal may resolve exact ties differently.",
            "interpretation": "Metrics describe trade-offs in this fixed synthetic 10-profile registry. They do not prove real-world matchmaking quality or generalization.",
        },
        "profiles": [
            {
                "player_id": p["player_id"],
                "name": p["name"],
                "skill_rating": p["skill_rating"],
                "profile_ping_ms": p["profile_ping_ms"],
                "trust_score": round(p["trust_score"], 2),
                "trust_label": p["trust_label"],
                "synthetic_queue_wait_seconds": p["queue_wait_seconds"],
            }
            for p in profiles
        ],
    }
