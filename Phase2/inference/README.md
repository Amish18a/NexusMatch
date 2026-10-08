# Trust Model Inference

This directory contains the runtime Python entry point for the frozen Phase 2 Trust model.

## Model

The inference script loads:

    ml/artifacts/final_trust_model.joblib

## Run

From the repository root:

~~~powershell
python Phase2\inference\trust_inference.py ^
  --history_sessions 20 ^
  --join_success_rate 0.95 ^
  --queue_abandon_rate 0.05 ^
  --completion_rate 0.90 ^
  --disconnect_rate 0.05 ^
  --reconnect_success_rate 0.90 ^
  --recent_3_join_success_rate 1.00 ^
  --recent_3_queue_abandon_rate 0.00 ^
  --recent_3_completion_rate 1.00 ^
  --recent_3_disconnect_rate 0.00 ^
  --recent_3_reconnect_success_rate 1.00 ^
  --avg_wait_time_sec 25 ^
  --avg_ping_ms 45 ^
  --avg_chat_messages 3
~~~

The command prints one machine-readable line:

~~~text
risk=... trust=... label=... threshold=...
~~~

The same module exposes predict_trust() for Python integration.

## Important

The current model is based on controlled synthetic NexusMatch telemetry. The interface validates the frozen 14-feature schema but does not establish real-player predictive performance.
