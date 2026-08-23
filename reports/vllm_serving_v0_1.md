# vLLM serving study v0.1

## Problem

Measure whether changing only AeroRAG-X's generation backend from Transformers to vLLM improves production serving, and whether repeated moderation-policy prefixes benefit from prefix caching.

## Hypothesis

Continuous batching should improve throughput as concurrency grows. Shared prefixes should reduce TTFT after cache warm-up. Neither result is assumed until measured.

## Experimental setup

- Same model revision, prompts, retrieval results, reranking, evidence gate, decoding parameters, and output budget.
- Concurrency: 1, 8, 16, 32; normal and shared-policy-prefix conditions.
- Cold warm-up excluded; three measured repetitions in randomized condition order.
- vLLM server launched with `--enable-prefix-caching`; GPU and software versions recorded with results.

## Metrics

Request throughput, output tokens/s, p50/p95 end-to-end latency, TTFT, TPOT, failure rate, and peak GPU memory. Failures remain in the denominator.

## Results

Not yet run on the required CUDA host. The benchmark intentionally does not contain invented measurements.

| Backend | Prefix | Concurrency | Requests/s | Output tok/s | p50 latency | p95 latency | p50 TTFT | TPOT | Failures | GPU memory |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Transformers | normal | 1 | pending | pending | pending | pending | pending | pending | pending | pending |
| vLLM | normal | 1/8/16/32 | pending | pending | pending | pending | pending | pending | pending | pending |
| vLLM | shared | 1/8/16/32 | pending | pending | pending | pending | pending | pending | pending | pending |

## Ablations and failure analysis

Disable prefix caching while retaining identical request ordering; compare short versus long policy prefixes. Explain sublinear scaling in terms of scheduler overhead, memory pressure, KV-cache capacity, output-length variance, and synchronization—not just headline throughput.

## Limitations

The OpenAI-compatible transport validates backend interchangeability but does not prove semantic parity; protected-generation evaluation must pass separately. One GPU/model/context mix does not establish universal serving superiority.

## Next experiment

Run three repetitions, attach raw JSON, report confidence intervals, and investigate any semantic regression before increasing tensor parallelism.
