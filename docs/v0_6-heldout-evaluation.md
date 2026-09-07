# v0.6 held-out evaluation protocol

The v0.6 development gate passed, but it is not a protected or independently
reviewed result. Before changing the default, create a new query JSONL file
with frozen source references and labels. It must be disjoint from both the
50-case development set and every protected generation set.

Two reviewers must independently complete the same frozen response contract.
Their raw JSONL files must be retained unchanged. Run:

```bash
PYTHONPATH=.:src python scripts/check_v06_heldout_readiness.py \
  --heldout data/evaluation/generation_queries_compression_heldout_v0_1.jsonl \
  --development data/evaluation/generation_queries_context_dev_v0_2.jsonl \
  --protected data/evaluation/generation_queries_v0_4_heldout.jsonl \
  --review-a data/evaluation/generation_compression_review_a_v0_1.jsonl \
  --review-b data/evaluation/generation_compression_review_b_v0_1.jsonl \
  --manifest artifacts/evaluation/generation_lora_compressed5_heldout_readiness_v0_1.json
```

The command is intentionally fail-closed. Missing data, overlap, incomplete
review coverage, or reuse of one response file blocks model evaluation. No
synthetic reviewer rows may be added to satisfy the gate.
