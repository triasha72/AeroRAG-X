# Base vs LoRA/SFT vs GRPO held-out ablation v0.1

## Problem

The GRPO smoke path executed, but a zero reward did not show that the model
learned. More trainer plumbing would not answer the useful question: does GRPO
improve grounded tool use over the existing Base and LoRA/SFT models on cases
that were kept out of training?

## Hypothesis

GRPO may improve tool selection and supported answers because those behaviors
are named in the reward. It may also learn shortcuts, make extra tool calls, or
lose structured-output reliability. No direction is assumed in advance.

## Experimental setup

All three variants must receive the same held-out case IDs, retrieval snapshot,
tool budget, decoding settings, and response validator. Training cases and
held-out cases must be disjoint. The aggregator rejects incomplete variant sets
and any mismatch in case identity.

```bash
python scripts/train_grpo_grounded_agent_v0_1.py \
  --cases data/training/grpo_grounded_agent_v0_1.jsonl --execute

python scripts/run_grpo_agent_ablation_v0_1.py \
  artifacts/evaluation/grpo_agent_observations_v0_1.jsonl
```

## Metrics and results

| Metric | Base | LoRA/SFT | GRPO |
|---|---:|---:|---:|
| Task success | pending | pending | pending |
| Refusal accuracy | pending | pending | pending |
| Citation validity | pending | pending | pending |
| Evidence support | pending | pending | pending |
| Tool-selection accuracy | pending | pending | pending |
| Structured-output validity | pending | pending | pending |
| Mean tool calls | pending | pending | pending |
| p50 latency | pending | pending | pending |
| p95 latency | pending | pending | pending |

There is no completed GRPO learning result yet. The existing zero-reward smoke
run is retained as an execution result, not promoted into an improvement claim.

## Ablations and failure analysis

The first ablation removes each reward term in turn. A second compares the full
reward with and without the unnecessary-tool penalty. Reward rises must be
checked against protected task metrics to catch formatting-only reward gains,
gratuitous retrieval, citation copying, and refusal overuse.

## Limitations and next experiment

A small Qwen model and a narrow tool environment may not produce a stable GRPO
signal. Run three seeds, retain failed runs, and report uncertainty. If GRPO
loses to LoRA/SFT, keep LoRA/SFT as the serving candidate and document where the
reward failed.
