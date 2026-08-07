# Evaluation

AeroRAG-X treats evaluation as a first-class architecture component.

This document summarizes the current retrieval and generation benchmarks, the v0.3 failure-analysis loop, and the final frozen generation results.

---

## Retrieval evaluation

### Benchmark v0.1

Eight aerospace queries were judged from a BM25-created candidate pool.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

This benchmark can favor BM25 because the judged candidates originated from BM25.

### Pooled benchmark v0.2

Candidate pooling combines BM25 and dense results before annotation.

```text
Queries: 8
BM25 depth: 20
Dense depth: 20
Candidates after deduplication: 278
Relevant: 101
Non-relevant: 177
```

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |
| Reranker top-10 | 0.2087 | 0.3024 | 0.7188 | 0.4614 |
| Reranker top-20 | 0.2068 | 0.3375 | 0.8375 | 0.5080 |

The current fixed reranker baseline improves ranking quality at the top while BM25 still has higher recall on this small set.

---

## Generation evaluation metrics

The generation evaluator records:

```text
answerability_accuracy
answerable_completion_rate
unsupported_refusal_rate
claim_citation_coverage_rate
citation_reference_validity_rate
source_document_coverage_rate
expected_term_recall
structural_validity_rate
```

The telemetry evaluator additionally records:

```text
provider_call_count
provider_bypass_count
provider_call_policy_accuracy
provider attempts
provider retries
latency
input/output/total tokens
estimated cost
```

---

## Generation v0.3 benchmark

Dataset:

```text
data/evaluation/generation_queries_v0_3.jsonl
```

Composition:

```text
20 answerable
12 unsupported
32 total
```

The dataset includes:

- direct factual questions;
- paraphrases;
- synthesis questions;
- unsupported exact-value questions;
- overclaim/regulatory controls;
- fictional named-entity controls.

---

## Baseline remote-provider result

The initial remote-provider v0.3 run produced:

| Metric | Baseline |
|---|---:|
| Answerability accuracy | 0.9375 |
| Answerable completion | 0.9000 |
| Unsupported refusal | 1.0000 |
| Claim citation coverage | 1.0000 |
| Citation-reference validity | 1.0000 |
| Expected-term recall | 0.9138 |
| Structural validity | 1.0000 |

Provider telemetry:

```text
Provider calls: 22
Provider bypasses: 10
Provider call-policy accuracy: 0.8750
Total tokens: 63,638
Estimated cost: $0.105733
```

---

## Sufficiency v0.2 intermediate result

A stricter sufficiency gate improved provider-call policy but over-blocked legitimate queries.

| Metric | v0.2 |
|---|---:|
| Answerability accuracy | 0.90625 |
| Answerable completion | 0.8500 |
| Unsupported refusal | 1.0000 |
| Expected-term recall | 0.87931 |
| Provider call-policy accuracy | 0.9375 |

Observed false pre-provider blocks:

```text
para_008
Why do power-electronics components require thermal management in electrified aircraft?

synth_003
What safety and thermal-management issues should designers consider across electrified aircraft propulsion systems?
```

The failure analysis showed:

- lowercase technical compounds were over-classified as named anchors;
- `issues` was over-normalized into an authority-style `issue` qualifier.

Those were corrected in Sufficiency v0.2.1.

---

## Multi-facet synthesis failure

After the sufficiency calibration, one synthesis case remained:

```text
synth_001
What thermal-management challenges are shared by
battery-electric and fuel-cell aircraft?
```

The gate considered the retrieved evidence sufficient, but the provider correctly refused because the top evidence lacked adequate fuel-cell-specific material.

Corpus diagnostics showed that fuel-cell thermal evidence existed, but ordinary single-query top-five selection did not assemble both facets.

A deterministic facet-aware retrieval layer was introduced to:

- retrieve each explicit facet;
- verify semantic facet identity;
- balance evidence;
- deduplicate chunks;
- preserve a bounded context.

The isolated live test then returned a supported answer with:

```text
Insufficient evidence: false
Claims: 3
Citations: 5
Source documents: 4
```

---

## Final v0.3 result

Final configuration:

```text
Sufficiency v0.2.1
Facet Retrieval v0.1
OpenAI Responses API provider
candidate_top_k = 20
evidence_top_k = 5
```

| Metric | Baseline | Final | Delta |
|---|---:|---:|---:|
| Answerability accuracy | 0.9375 | **1.0000** | +0.0625 |
| Answerable completion | 0.9000 | **1.0000** | +0.1000 |
| Unsupported refusal | 1.0000 | **1.0000** | 0.0000 |
| Claim citation coverage | 1.0000 | **1.0000** | 0.0000 |
| Citation-reference validity | 1.0000 | **1.0000** | 0.0000 |
| Expected-term recall | 0.9138 | **0.9310** | +0.0172 |
| Structural validity | 1.0000 | **1.0000** | 0.0000 |

Provider telemetry:

| Metric | Baseline | Final |
|---|---:|---:|
| Provider calls | 22 | **20** |
| Provider bypasses | 10 | **12** |
| Provider call-policy accuracy | 0.8750 | **1.0000** |
| Total tokens | 63,638 | **58,915** |
| Estimated cost | $0.105733 | **$0.103745** |

Final latency:

```text
P50: 5.6394 s
P95: 7.6947 s
Retry rate: 0.0
```

Final answerability failure count:

```text
0
```

---

## Frozen artifacts

```text
artifacts/evaluation/generation_deterministic_v0_3.json
artifacts/evaluation/generation_deterministic_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3.json
artifacts/evaluation/generation_openai_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3_final.json
artifacts/evaluation/generation_openai_v0_3_final_telemetry.json
artifacts/evaluation/generation_v0_3_final_comparison.json
```

---

## Interpretation

The final run shows that the current architecture corrected the specific labeled failure modes in this benchmark while preserving unsupported-query refusal and citation structure.

It does **not** establish:

- universal answer faithfulness;
- universal citation entailment;
- robustness to arbitrary prompt injection;
- general multi-hop reasoning quality;
- production-scale latency or cost;
- correctness outside the current NASA corpus.

Those require larger, independently reviewed evaluation.

---

## Next evaluation work

After serving/deployment:

- add API-level regression tests;
- evaluate end-to-end request latency;
- add semantic claim/citation support scoring;
- add larger generation and retrieval sets;
- add human review;
- add conflicting-evidence cases;
- add partial-evidence cases;
- add broader prompt-injection cases;
- define CI regression thresholds;
- separate development and held-out test sets.
