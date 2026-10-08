# NexusMatch - Final Phase 2 Trust ML

This folder contains the finalized Phase 2 Trust-model pipeline.

## Final data design

The final model is trained on controlled synthetic NexusMatch session
telemetry so that the features and target match the intended deployment use
case.

The prepared dataset contains 90,454 examples from 5,000 simulated players.
Each example uses behavioural history to predict whether at least one of the
player's next three sessions will be unreliable.

## Final feature vector

The model uses 14 features:

```text
history_sessions
join_success_rate
queue_abandon_rate
completion_rate
disconnect_rate
reconnect_success_rate
recent_3_join_success_rate
recent_3_queue_abandon_rate
recent_3_completion_rate
recent_3_disconnect_rate
recent_3_reconnect_success_rate
avg_wait_time_sec
avg_ping_ms
avg_chat_messages
```

## Model selection

Experiments compared behavioural baseline and several supervised models using
chronological validation. Logistic Regression was selected for the final
pipeline based on the validation comparison and then calibrated before unseen
test evaluation.

Validation comparison also included an ablation/trend study. The differences
between feature variants were small, so the current 14-feature set was frozen
rather than continuing to chase marginal improvements.

## Final unseen-test metrics

```text
Accuracy                0.5837
Balanced Accuracy       0.6141
Precision (unreliable)  0.4573
Recall (unreliable)     0.7277
F1 (unreliable)         0.5617
ROC-AUC                 0.6918
Average Precision       0.6098
Brier Score             0.2023
```

The model is intended to identify elevated unreliability risk, so recall of
the unreliable class is an important operating metric.

## Dota 2 experiments

Dota 2 preprocessing, behavioural analysis and NLP experiments are retained as
research work. Those experiments did not provide sufficiently strong
deployment-aligned predictive performance, so Dota 2 is not used as the final
Trust training source.

## Inference

The runtime inference entry point is:

    inference/trust_inference.py

It accepts the 14 features and returns risk, trust, label, and threshold.

The C++ TrustModelBridge invokes this interface and writes the resulting Trust
Score into the C++ Player object.

## Important limitation

The final model uses synthetic NexusMatch telemetry. Its successful Docker
demonstration validates the software pipeline and integration, not real-world
generalization or predictive accuracy.