# Phase 2 - Trust Score Foundation

This module is the first step of the Phase 2 AI/ML work in NexusMatch.

## Purpose

In Phase 1, the matchmaking engine used basic compatibility factors such as skill, ping and waiting time. Phase 2 extends this idea by introducing player reliability as another factor.

The first step is to prepare behavioural player data and calculate a baseline Trust Score. This is a rule-based prototype, not the final machine learning model. The baseline gives us a clear starting point for later AI/ML experiments.

## Behavioural Features

The sample dataset contains:

- Join attempts and successful joins
- Queue entries and queue abandonments
- Matches started and completed
- Player disconnects

These features are related to reliability during the matchmaking and gaming process. They are intentionally different from a simple toxicity score.

## Baseline Trust Score

The current prototype combines four reliability components:

- Join reliability: 35%
- Match completion: 30%
- Connection stability: 20%
- Queue reliability: 15%

The final value is scaled to a score from 0 to 100.

## Phase 2 Next Steps

1. Collect or identify a more suitable behavioural dataset.
2. Explore additional player-behaviour features.
3. Test ML models for Trust Score prediction.
4. Explore suitable NLP features as suggested by the mentor.
5. Connect the Trust Score with the C++ matchmaking engine.
6. Display trust-related information in the monitoring GUI.

The current code is intentionally kept simple so that it can be tested independently before integration with the main matchmaking engine.
