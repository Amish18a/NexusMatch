# Trust Model Inference

This folder contains the inference bridge for the final NexusMatch Trust model.

## Model

The inference script loads:

data/ml/nexusmatch_trust_results/final_trust_model.joblib

## Test from Phase2/TrustSystem

PowerShell:

    python inference/trust_inference.py `
      --history_sessions 20 `
      --join_success_rate 0.95 `
      --queue_abandon_rate 0.05 `
      --completion_rate 0.90 `
      --disconnect_rate 0.05 `
      --reconnect_success_rate 0.90 `
      --recent_3_join_success_rate 1.00 `
      --recent_3_queue_abandon_rate 0.00 `
      --recent_3_completion_rate 1.00 `
      --recent_3_disconnect_rate 0.00 `
      --recent_3_reconnect_success_rate 1.00 `
      --avg_wait_time_sec 25 `
      --avg_ping_ms 45 `
      --avg_chat_messages 3

The output is one machine-readable line:

    risk=... trust=... label=... threshold=...

The same module can be imported from Python with predict_trust().

## Integration purpose

The CLI is intentionally kept to one output line so the future C++ bridge can
call the Python model and read the Trust result without a C++ ML runtime dependency.

## Important

The current model is a Phase 2 development model validated on synthetic
NexusMatch simulation data. Real server or Docker telemetry is required before
making real-player predictive claims.
