# Phase 2 Research

This directory contains supporting Dota 2 behavioural and NLP research that informed the frozen Phase 2 design but is not part of the runtime deployment path.

## Dota 2 research

The scripts here preprocess and analyse the published Dota 2 Matches dataset. Raw and processed Dota data is generated under Phase2/data/ and is not committed.

The Dota experiments were useful for feature exploration, but they did not provide a deployment-aligned NexusMatch Trust target. The final Trust model therefore uses NexusMatch-specific synthetic telemetry.

## Related ML experiments

Alternative temporal, future-window, NLP and Trust feature-ablation studies are kept separately under Phase2/ml/experiments/ for model-selection traceability.
