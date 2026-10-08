# Phase 2 Research

This directory contains supporting research that informed the frozen Phase 2 design but is not part of the runtime deployment path.

## Dota 2 research

The Dota 2 scripts preprocess and analyse the published Dota 2 Matches dataset for behavioural and NLP-oriented investigation.

Raw and processed Dota data is generated under Phase2/data/ and is not committed.

The Dota experiments were useful for feature exploration, but they did not provide a deployment-aligned NexusMatch Trust target. The final Trust model therefore uses NexusMatch-specific synthetic telemetry.

## Other experiments

Alternative temporal, future-window, NLP and Trust feature-ablation experiments remain under Phase2/ml/ for research traceability.

These experiments support report/paper discussion but are separate from the frozen runtime inference path.
