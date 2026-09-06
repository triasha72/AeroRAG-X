# Context compaction v0.4 — first development gate passed

## Decision

Reducing the final evidence budget from five passages to three passed the
eight-case development gate. This is a real local-model result, but it is not a
protected-set result and is not yet a general quality claim.

## Why this experiment followed the rejected concise prompt

The v0.3.2 prompt attempted to save output tokens by asking the model to say
less. It saved only 6.18% of paired output tokens, reduced total tokens by only
2.96%, and introduced one malformed response. The failure suggested that the
larger cost was upstream: evidence placed in the prompt.

v0.4 therefore retained the reliable v0.3.1 prompt, the reproduced epoch-2
LoRA adapter, the retrieval candidate pool, generation settings, and queries.
It changed one variable: `evidence_top_k` from 5 to 3.

## Measured result

| Metric | Five passages | Three passages | Change |
|---|---:|---:|---:|
| Completed queries | 8/8 | 8/8 | parity |
| Generation failures | 0 | 0 | parity |
| Mean input tokens, provider calls | 2,133.14 | 1,380.86 | -35.27% |
| Mean output tokens, provider calls | 166.14 | 163.43 | -1.63% |
| Mean total tokens, provider calls | 2,299.29 | 1,544.29 | **-32.84%** |

Answerability, answerable completion, unsupported refusal, citation coverage,
citation validity, source-document coverage, expected-term recall, and
structural validity were all 1.000 for both conditions. Seven calls formed the
paired token sample; the eighth query bypassed the provider under both policies.

The result passed the frozen development rule: at least 15% paired total-token
reduction, no quality-rate regression, no additional failures, and all expected
queries present.

## Integrity and limitation

Treatment report SHA-256:
`ad0aeb4c4d62e8fb2283ecb676ad9bc7b8e50e39a3ef4393f44025672a785351`

Treatment telemetry SHA-256:
`3e9ee6e6707b5022f0543bca6ac721793ab2af638d7de70603c226e7472a3505`

Eight cases are too few to justify protected promotion. The next engineering
gate uses 50 disjoint development cases: curated compact questions, unsupported
scope challenges, and deterministic source-grounded stress cases. The automatic
source cases are not human-validated. They test robustness and token behavior;
they do not convert this experiment into independent quality evidence.
