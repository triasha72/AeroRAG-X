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

For a genuine experiment, validate and hash both splits with
`scripts/prepare_grpo_dataset_v0_1.py`, execute the Kaggle run, and follow
`docs/REAL_GRPO_RESULT.md`. The validator also rejects inconsistent
answer/evidence contracts and likely paraphrase leakage across the split.
