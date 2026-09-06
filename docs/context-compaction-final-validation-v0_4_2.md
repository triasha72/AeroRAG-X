# Context-compaction v0.4.2 final-validation protocol

## Decision being tested

Does selecting three final evidence passages instead of five reduce paired
total model tokens by at least 15% without worsening a frozen quality rate by
more than one query out of 32?

## What is frozen

`configs/context_compaction_protected_protocol_v0_1.json` pins the 32 queries,
corpus, dense index, epoch-2 LoRA adapter, local Qwen checkpoint, reliable
v0.3.1 prompt/runtime, candidate top-k of 20, evidence budgets, gate thresholds,
and output paths by checksum or literal value.

The control and treatment differ only in final evidence top-k: five versus
three. Both arms run during the same invocation. Existing output at any frozen
path aborts the run, preventing accidental replacement of unfavorable evidence.

## Evidence boundary

The 32-query set is disjoint from LoRA training and has historically been called
protected in this project. It has also been used in earlier generation studies,
so v0.4.2 is a final validation of a development-selected intervention on a
historical protected benchmark—not an evaluation on a newly unseen question
set. An unseen-benchmark claim requires a newly collected and independently
reviewed dataset.

## Execution

Run once from normal macOS Terminal:

```bash
cd "/Users/triashasarkar/Documents/Codex/2026-08-26/can/work/repos/AeroRAG-X"
./scripts/run_context_compact_protected_v0_4_2.sh
```

The runner uses Apple MPS and refuses CPU substitution. It writes both raw
reports, telemetry, paired analysis, a decision, and a final hash manifest. A
nonzero exit after a rejected decision represents a completed negative result,
not permission to change thresholds or rerun selectively.
