# C++ Trust Model Bridge

This bridge lets the C++ NexusMatch side call the Python Trust inference
module without adding a Python ML runtime to C++.

## Build

From `Phase2/TrustSystem`:

    g++ cpp/TrustModelBridge.cpp cpp/trust_bridge_demo.cpp -o cpp/trust_bridge_demo

## Run

From `Phase2/TrustSystem`:

    .\cpp\trust_bridge_demo.exe

Expected output is approximately:

    Reliable example -> Risk: 0.02 | Trust: 98.47 | Label: reliable
    Unreliable example -> Risk: 1.00 | Trust: 0.02 | Label: unreliable

## Architecture

    C++ / server
         |
         v
    TrustModelBridge
         |
         v
    Python trust_inference.py
         |
         v
    final_trust_model.joblib
         |
         v
    Risk + Trust Score

This subprocess bridge is a Phase 2 integration step. For larger-scale
deployment, the trust model can later be served by a persistent Python
service so the C++ server does not start a Python process for every request.

The current model is trained and validated on synthetic NexusMatch data.
