# Phase 46 — Grounded tool-using GRPO experiment

The training environment exposes only four bounded tools:

- `retrieve`
- `check_sufficiency`
- `submit_answer`
- `refuse`

The environment owns the observable rollout state and calculates reward through
the Phase 45 multi-objective reward harness.

The checked-in JSONL is a synthetic training-format template. It is not a real
aerospace training corpus and must not be used for a résumé performance claim.

Validate locally first. Actual GRPO training should run only on a suitable
training host after a real versioned training set is prepared and verified
disjoint from the protected evaluation benchmark.
