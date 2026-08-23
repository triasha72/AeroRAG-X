# Phase 47 — Base vs LoRA/SFT vs GRPO ablation

This phase defines a controlled held-out comparison. Every model variant must
run on exactly the same frozen case IDs.

The aggregator intentionally makes no assumption that GRPO is superior.
Task success, refusal, citations, evidence support, tool selection, structured
output, tool efficiency, and latency are all reported.

The checked-in report contains only `pending` placeholders. Replace them only
with measured results from frozen evaluation artifacts.

Use `scripts/freeze_grpo_evidence_v0_1.py` to produce the measured JSON and
Markdown report. It requires identical held-out IDs plus model revision, seed,
and adapter hashes, preventing a placeholder or incomplete observation file
from being presented as final evidence.
