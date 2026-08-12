# Semantic Quality Evaluation v0.1

## Method

Four frozen systems were evaluated over 20 answerable queries and 76 expected concept instances per system.

Ten concept instances were accepted through deterministic canonical/alias matching. The remaining 294 were adjudicated using the frozen review protocol.

PRESENT counts toward conservative coverage. AMBIGUOUS is retained and included only in the upper bound.

## Four-way semantic coverage

| System | Present | Absent | Ambiguous | Micro lower | Micro upper | Macro lower | Macro upper |
|---|---:|---:|---:|---:|---:|---:|---:|
| base_closed_book | 13 | 50 | 13 | 0.1711 | 0.3421 | 0.1667 | 0.3475 |
| lora_closed_book | 14 | 49 | 13 | 0.1842 | 0.3553 | 0.1792 | 0.3600 |
| base_rag | 29 | 35 | 12 | 0.3816 | 0.5395 | 0.3867 | 0.5425 |
| lora_rag | 39 | 26 | 11 | 0.5132 | 0.6579 | 0.5150 | 0.6542 |

## Guardrails

- No generation or retrieval was rerun for this evaluation.
- No cosine or NLI threshold was frozen after failed calibration.
- AMBIGUOUS labels remain explicit instead of being forced binary.
- These metrics measure expected-concept coverage, not universal factual correctness.
