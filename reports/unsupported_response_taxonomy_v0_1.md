# Unsupported-response taxonomy evaluation v0.1

## Scope

This evaluation classifies the behavior of four frozen system conditions on the 12 benchmark queries marked `expected_answerable = false`.

The four conditions are Base closed-book, LoRA closed-book, Base + RAG, and LoRA + RAG, for 48 frozen responses total.

This taxonomy distinguishes explicit refusals, corrective denials, unsupported substantive assertions, and structural failures.

This is a single structured adjudication pass under a frozen policy, not an independent multi-assessor human annotation study.

## Results

| Condition | Unsupported queries | Explicit refusal | Corrective denial | Unsupported assertion | Structural failure | Safe non-assertion | Unsupported-assertion rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base closed-book | 12 | 5 | 2 | 5 | 0 | 0.5833 | 0.4167 |
| LoRA closed-book | 12 | 5 | 4 | 3 | 0 | 0.7500 | 0.2500 |
| Base + RAG | 12 | 12 | 0 | 0 | 0 | 1.0000 | 0.0000 |
| LoRA + RAG | 12 | 12 | 0 | 0 | 0 | 1.0000 | 0.0000 |

## Interpretation

- The original strict refusal metric does not distinguish corrective denials from unsupported substantive answers.
- Base closed-book is safe by this broader taxonomy on 7/12 unsupported queries (58.33%).
- LoRA closed-book is safe by this broader taxonomy on 9/12 unsupported queries (75.00%).
- Base + RAG and LoRA + RAG explicitly refuse all 12/12 unsupported queries.
- On this frozen benchmark, retrieval-grounded execution eliminates unsupported substantive answering in both grounded conditions.

## Interpretation guardrails

- `UNSUPPORTED_ASSERTION` is defined relative to the frozen benchmark contract; it is not a universal factuality judgment for every sentence.
- A failed strict-refusal metric is not automatically a hallucination; corrective denials are classified separately.
- The taxonomy does not establish universal superiority outside this protected benchmark.
- No generation, retrieval, or training run was repeated for this adjudication stage.
