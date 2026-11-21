# Phase 3.4 — Matchmaking Policy Evaluation

## Purpose

This increment provides a repeatable, offline comparison between:

1. **Skill-only selection** — candidate ranking uses 100% of the skill compatibility score.
2. **Trust-aware selection** — Skill 50%, Ping 20%, Trust 20%, Waiting 10%.
3. **Trust-aware without waiting** — the Skill, Ping and Trust ratios are proportionally renormalised to 55.56%, 22.22% and 22.22%, so the waiting contribution can be isolated without changing the ratios of the other factors.

The evaluator does not connect to the live C++ server, change the live queue or create match-history records.

## Dataset and trial design

- Input: the ten enabled predefined player profiles.
- Trust: the saved Phase 2 Logistic Regression inference artifact.
- Ping: `avg_ping_ms` from the predefined profile feature vector. This is a simulated historical player ping, not the API-to-C++ server RTT.
- Eligibility: different player, same region, same game mode, and within 100 skill-rating points of the anchor.
- Group sizes: 3, 4 and 5.
- Trials: every profile is considered as an anchor for every group size, creating 30 independent trials per policy. A profile may appear in multiple independent trials; this is not a sequential queue simulation.
- Queue age: a controlled synthetic scenario assigns 0–135 seconds in 15-second steps by player ID. This is only to test the ranking effect; it is not observed queue telemetry.

## Compatibility formulas

Skill score:

```text
max(0, 100 - abs(anchor_skill - candidate_skill) / 5)
```

Ping score:

```text
max(0, 100 - abs(anchor_profile_ping - candidate_profile_ping))
```

Trust pair score:

```text
(anchor_trust + candidate_trust) / 2
```

Waiting score:

```text
player_waiting_score = min(queue_wait_seconds, 100)
pair_waiting_score = (anchor_waiting_score + candidate_waiting_score) / 2
```

Trust-aware policy:

```text
skill_score * 0.50
+ ping_score * 0.20
+ trust_pair_score * 0.20
+ pair_waiting_score * 0.10
```

For reproducibility, exact score ties are resolved by player ID in the offline evaluator. The live C++ implementation uses its AVL candidate traversal order and stable score sorting, so exact ties may be resolved differently.

## Live integration (Phase 3.5)

The live queue timer comes from the persisted `queue_entered_at` timestamp in SQLite. The API sends `SET_WAIT <playerId> <seconds>` to C++ when the displayed elapsed second changes and immediately before a match request.

C++ updates the canonical Player state and the copies stored in Queue, AVL Tree and Hash Table. The Queue update is in-place and preserves FIFO order. The AVL Tree copy is removed and reinserted using the same skill/ID key; the Hash Table copy is updated by player ID.

The C++ engine now includes each candidate's queue age in the 10% waiting component. Longer-waiting eligible candidates can therefore receive a higher compatibility contribution. The score is capped at 100 seconds, so queue age cannot grow without limit.

## Metrics

For selected groups, the evaluator records:

- group skill spread;
- mean anchor-to-candidate skill gap;
- mean pairwise skill gap;
- mean profile ping and ping spread;
- mean Trust Score and low-Trust member rate;
- mean selected queue age.

It also reports how often each policy selects a different group. The isolated waiting comparison reports selected candidate wait with the waiting factor enabled and disabled.

## Interpretation limits

- The registry contains only ten controlled synthetic profiles.
- The Trust model was trained on synthetic NexusMatch telemetry; outputs do not establish real-world generalisation.
- The benchmark uses controlled synthetic queue ages, not actual queue-entry timestamps from real players.
- The benchmark compares independent anchor/size trials; it does not simulate a queue being consumed over time.
- The evaluator is a deterministic Python replay, not a live C++ execution. Exact tie-breaking can differ from AVL traversal.
- Results are exploratory evidence for this fixed demonstration registry, not a statistically representative user study.

## How to run

Open **Policy Evaluation** in the Phase 3 website and select **Run benchmark**.

API routes:

- `POST /api/evaluation/run` — execute the comparison and write the result to System Logs.
- `GET /api/evaluation/latest` — retrieve the latest completed result.

The newest result is stored in the existing SQLite System Logs as `source=evaluation`, `event=benchmark-completed`. No new database table or volume reset is required.
