# Answer-to-claim completeness evaluation v0.1

## Scope

This evaluation measures whether the formal claim structure captures the material factual and technical propositions expressed in each grounded prose answer.

The benchmark contains 40 frozen grounded answer instances: 20 Base + RAG and 20 LoRA + RAG.

This stage evaluates representation/completeness only. Claim-evidence support was evaluated separately.

This is a single structured adjudication pass under a frozen policy, not an independent multi-assessor human annotation study.

## Results

| System | Answers | Fully captured | Partial | Material omission | Full capture | Full-or-partial |
|---|---:|---:|---:|---:|---:|---:|
| Base + RAG | 20 | 2 | 10 | 8 | 0.1000 | 0.6000 |
| LoRA + RAG | 20 | 9 | 10 | 1 | 0.4500 | 0.9500 |

## Comparison

LoRA - Base full-capture-rate difference: +0.3500

LoRA - Base full-or-partial-capture-rate difference: +0.3500

## Interpretation guardrails

- These metrics measure how completely formal claims represent the prose answer, not factual correctness.
- Claim-evidence support is reported separately and must not be inferred from completeness.
- Extra claims are not automatically beneficial; redundancy is evaluated separately.
- Higher completeness on this protected benchmark does not establish universal model superiority.
- No generation, retrieval, or training run was repeated for this adjudication stage.
