# NexusMatch - Project-Specific Behaviour Dataset

This module creates a controlled NexusMatch behavioural dataset so the Trust
model can eventually be trained on events that directly match the application.

## Why this exists

The Dota 2 experiments were useful for feature and NLP research, but the Dota
dataset does not contain NexusMatch-specific matchmaking events such as queue
abandonment and join failures.

This simulation therefore provides a development bridge until the real server
and Docker clients can generate actual telemetry.

## Simulated events

The raw event file contains:

- join attempts
- successful and failed joins
- queue entries and queue abandonment
- match starts and completions
- disconnects and reconnects
- ping
- waiting time
- chat activity count

The hidden reliability profile used to generate the events is NOT exported as
a model feature or target.

## Files

Run:

    python simulation/generate_nexusmatch_data.py

This creates:

    data/nexusmatch_simulation/nexusmatch_behavior_events.csv

Then:

    python ml/prepare_nexusmatch_trust_dataset.py

This creates:

    data/ml/nexusmatch_future_trust_dataset.csv

The target is:

    future_unreliable_3 = 1

when at least one of the player's next three sessions contains an unreliable
event.

## Important research limitation

This is synthetic data. It is suitable for pipeline validation, software
integration and controlled experiments, but any ML performance obtained on it
must be labelled as simulation performance. It must not be presented as
evidence from real players.

The final Phase 2 system should replace the simulated event stream with
telemetry produced by the NexusMatch server/Docker players.
