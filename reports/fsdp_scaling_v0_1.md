# FSDP scaling study v0.1

## Problem

Determine what FSDP changes in memory, throughput, checkpointing, restart behavior, and reproducibility versus a matched one-GPU non-sharded baseline.

## Hypothesis

Full parameter, gradient, and optimizer sharding should reduce peak memory per rank enough to train a larger Qwen workload, while communication and small-batch synchronization prevent ideal 2× throughput scaling.

## Experimental setup

- Identical model revision, frozen train/dev splits, seed, assistant-only objective, global batch, sequence budget, optimizer, and step count.
- Baseline: one GPU, `--no-fsdp`. Treatment: two GPUs via `torchrun`, full sharding, bf16, size-based transformer wrapping, gradient checkpointing, and distributed samplers.
- Resume test: interrupt after a saved step, resume, and compare the remaining loss trajectory and final protected evaluation with an uninterrupted control.
- Three repetitions. Record CUDA/PyTorch/Transformers versions and GPU model.

## Metrics and results

No CUDA experiment was run in this workspace; pending values are not evidence.

| Configuration | GPUs | Train loss | Val loss | Peak memory/GPU | Tokens/s | Samples/s | Step time | Checkpoint size | Save time | Resume | Final parity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Baseline | 1 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| FSDP full shard | 2 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |

## Ablations

Gradient checkpointing on/off; bf16 versus fp32 where feasible; wrapping granularity; and sharded versus full-state checkpoint export. Change one factor at a time.

## Failure analysis

Sublinear scaling is expected from parameter all-gathers, gradient reduce-scatter, synchronization at accumulation boundaries, duplicated activations, checkpoint I/O, and an underfilled workload. FSDP primarily solves memory capacity; it does not promise 2× speed.

## Limitations

Exact floating-point identity is not expected across sharding orders. Parity means bounded loss/metric deltas under a preregistered tolerance, not matching bytes. A two-GPU, single-node result does not establish multi-node scaling.

## Next experiment

Run the preregistered matrix, validate a mid-run restart, export a rank-0 full state for protected evaluation, and attach raw metrics plus uncertainty before drawing conclusions.
