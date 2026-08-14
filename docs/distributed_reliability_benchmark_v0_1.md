# Phase 44 — Distributed reliability benchmark

The benchmark sends bounded concurrent requests to the distributed Agent API
and records per-request latency, timeout, safe-refusal, and unsafe-answer
behavior.

Fault scenarios must be created explicitly in the deployment/test environment;
the harness does not pretend a scenario occurred merely because its name was
passed on the command line.

Run each scenario separately and preserve the resulting JSON artifacts.
