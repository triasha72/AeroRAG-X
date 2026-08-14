# Phase 40 — Agent trajectory benchmark harness

This phase adds a frozen-case schema and deterministic metrics for tool
selection, terminal-state correctness, budget compliance, safe refusal, tool
efficiency, and latency.

The checked-in JSONL is deliberately a **synthetic contract template**, not a
NASA-domain benchmark. Do not report agent performance from it. Before closing
the evaluation gap, curate and freeze roughly 40–60 real cases spanning
supported, unsupported, multi-source, ambiguous, conflict, retry, failure,
budget, and human-review behavior.

Record actual `AgentTrajectoryObservation` rows, then run:

```bash
python scripts/run_agent_trajectory_eval_v0_1.py path/to/observations.jsonl
```

Compare deterministic, bounded-adaptive, and stateful-agent baselines without
assuming the agent is superior.
