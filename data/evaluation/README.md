# AeroRAG-X Evaluation Datasets

AeroRAG-X maintains separate but related retrieval and grounded-generation evaluation datasets.

The evaluation artifacts are versioned so that changes to relevance judgments, retrieval methods, generation behavior, or answerability policy do not silently overwrite prior baselines.

---

## Dataset families

### Retrieval evaluation

```text
queries_v0_1.jsonl
candidates_v0_1.jsonl
qrels_v0_1.jsonl

candidates_v0_2_internal.jsonl
candidates_v0_2_annotation.jsonl
qrels_v0_2.jsonl
```

### Grounded-generation evaluation

```text
generation_queries_v0_1.jsonl
```

Tracked reports:

```text
artifacts/evaluation/generation_v0_1.json
artifacts/evaluation/generation_v0_2.json
```

---

# Part I — Retrieval evaluation

## Purpose

The retrieval benchmark evaluates retrieval systems over the AeroRAG-X NASA technical-report corpus while preserving chunk-level source and page provenance.

## Corpus

- Source: NASA Technical Reports Server
- Retrieval unit: citation-preserving text chunk
- Corpus size at benchmark creation: 3,233 chunks
- Chunking configuration: `configs/chunking_v0_1.yaml`

## Retrieval queries

The benchmark contains eight aerospace queries covering:

- battery thermal runaway propagation
- fuel-cell aircraft thermal management
- hybrid-electric propulsion safety
- distributed electric propulsion
- cryogenic hydrogen storage
- aircraft battery cooling
- power-electronics thermal management
- lithium-ion battery fire detection

Because the benchmark has only eight queries, aggregate metrics are sensitive to individual relevance decisions.

---

## Retrieval v0.1

Files:

```text
queries_v0_1.jsonl
candidates_v0_1.jsonl
qrels_v0_1.jsonl
```

Protocol:

1. retrieve BM25 candidates;
2. inspect available candidate evidence;
3. label useful chunks as relevant;
4. evaluate BM25 and dense retrieval against the same v0.1 qrels.

Limitation:

The original relevance pool was generated from BM25 candidates only. Relevant dense-only chunks could therefore be absent from the judgment set.

Results:

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

---

## Retrieval v0.2 pooled protocol

Files:

```text
candidates_v0_2_internal.jsonl
candidates_v0_2_annotation.jsonl
qrels_v0_2.jsonl
```

For every retrieval query:

1. retrieve top-20 BM25 candidates;
2. retrieve top-20 dense candidates;
3. combine candidate lists;
4. deduplicate by `chunk_id`;
5. carry forward relevant v0.1 chunks;
6. preserve retriever identity/rank/score internally;
7. remove retriever identity/rank/score from annotation records;
8. order blinded candidates deterministically using SHA-256 and seed 42;
9. assign binary relevance to every candidate;
10. build v0.2 qrels;
11. evaluate all retrieval stages against the same relevance set.

Counts:

| Property | Value |
|---|---:|
| Queries | 8 |
| Pooled candidates | 278 |
| Relevant | 101 |
| Non-relevant | 177 |
| Corpus chunks | 3,233 |
| BM25 candidate depth | 20 |
| Dense candidate depth | 20 |
| Shuffle seed | 42 |

### Relevance definition

Relevant evidence should:

- directly address the query;
- explain the requested system, mechanism, hazard, method, or result;
- contain substantive technical content useful for answering the query;
- preserve valid source/page provenance.

Non-relevant evidence includes:

- loose keyword overlap;
- a different subsystem/problem;
- bibliography or boilerplate;
- evidence too fragmented to answer the query;
- topic mentions without substantive support.

### Retrieval v0.2 results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |
| Reranker top-10 | 0.2087 | 0.3024 | 0.7188 | 0.4614 |
| Reranker top-20 | 0.2068 | 0.3375 | 0.8375 | 0.5080 |

Hybrid RRF uses fixed parameters:

```text
rrf_k = 60
BM25 depth = 50
dense depth = 50
```

The reranker uses:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
batch_size = 16
device = cpu
```

Neither stage has been tuned against this eight-query benchmark.

---

## Retrieval annotation limitations

The initial v0.2 labels were created through conservative assistant-supported review of candidate text previews.

Limitations:

- some judgments did not use full-page/full-document context;
- previews can omit qualifiers;
- ambiguous candidates were generally labeled non-relevant;
- no independent second assessor has completed a full audit;
- inter-annotator agreement has not been measured.

Before publication-grade claims:

1. conduct independent second-pass review;
2. inspect full source context for uncertain candidates;
3. version any changed labels;
4. add a second assessor;
5. calculate agreement;
6. expand the query set.

---

# Part II — Grounded-generation evaluation

## Purpose

The generation benchmark evaluates whether the system:

- answers questions that should be answerable from the corpus;
- refuses deliberately unsupported questions;
- produces claims with citation references;
- resolves those references to authoritative citation records;
- represents citations in source-document summaries;
- preserves a structurally valid supported/refusal state.

It is currently a deterministic engineering benchmark, not a full semantic-faithfulness benchmark.

---

## Generation query file

```text
generation_queries_v0_1.jsonl
```

Current composition:

| Query class | Count |
|---|---:|
| Expected answerable | 8 |
| Expected unsupported | 2 |
| Total | 10 |

The answerable questions cover aerospace topics aligned with the retrieval corpus.

The two unsupported controls include deliberately unsupported/fictitious details designed to test refusal behavior.

---

## Generation-query schema

Each JSONL row contains:

```text
query_id
query
expected_answerable
expected_terms
```

`expected_terms` is used only as a lightweight lexical diagnostic. It is not a semantic correctness label.

Unanswerable queries do not define expected terms.

---

## Generation metrics

### Answerability accuracy

```text
correct answer/refusal decisions
/
all generation queries
```

### Answerable completion rate

```text
expected-answerable queries that received answers
/
all expected-answerable queries
```

### Unsupported refusal rate

```text
expected-unsupported queries that were refused
/
all expected-unsupported queries
```

### Claim citation coverage rate

```text
generated claims containing citation IDs
/
all generated claims
```

### Citation-reference validity rate

```text
claim citation references resolving to final citation records
/
all claim citation references
```

### Source-document coverage rate

```text
citations represented by source-document records
/
all citations
```

### Expected-term recall

```text
expected lexical terms found in answer text
/
all expected lexical terms
```

This is a heuristic only.

### Structural validity rate

A supported answer is structurally valid when:

- it contains claims;
- every claim is cited;
- citation references resolve;
- citations are represented in source-document records.

A refusal is structurally valid when it contains no claims, citations, or source documents.

---

## Generation v0.1 baseline

Configuration:

```text
configs/generation_v0_1.yaml
```

Provider:

```text
deterministic-grounded-v0
```

Report:

```text
artifacts/evaluation/generation_v0_1.json
```

Results:

| Metric | Value |
|---|---:|
| Queries | 10 |
| Answerability accuracy | 0.8000 |
| Answerable completion | 1.0000 |
| Unsupported refusal | 0.0000 |
| Claim citation coverage | 1.0000 |
| Citation-reference validity | 1.0000 |
| Source-document coverage | 1.0000 |
| Expected-term recall | 0.9130 |
| Structural validity | 1.0000 |

Interpretation:

The original generator preserved citation and answer structure but did not independently assess whether retrieved evidence was semantically sufficient. Both unsupported controls therefore received answers.

---

## Generation v0.2 sufficiency-gated baseline

Additional configuration:

```text
configs/sufficiency_v0_1.yaml
```

Report:

```text
artifacts/evaluation/generation_v0_2.json
```

Results:

| Metric | v0.1 | v0.2 | Delta |
|---|---:|---:|---:|
| Answerability accuracy | 0.8000 | 1.0000 | +0.2000 |
| Answerable completion | 1.0000 | 1.0000 | +0.0000 |
| Unsupported refusal | 0.0000 | 1.0000 | +1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 | +0.0000 |
| Citation-reference validity | 1.0000 | 1.0000 | +0.0000 |
| Source-document coverage | 1.0000 | 1.0000 | +0.0000 |
| Expected-term recall | 0.9130 | 0.9130 | +0.0000 |
| Structural validity | 1.0000 | 1.0000 | +0.0000 |

The deterministic sufficiency gate corrected both unsupported-control failures on the current benchmark without rejecting the eight expected-answerable queries.

This result must not be interpreted as general-purpose answerability accuracy. The benchmark contains only ten queries.

---

## Sufficiency decision data

The v0.2 pipeline records:

```text
retrieval_metadata
└── evidence_sufficiency
    ├── sufficient
    ├── evidence_count
    ├── query_terms
    ├── supported_terms
    ├── unsupported_terms
    ├── query_term_coverage
    ├── single_evidence_coverage
    ├── required_numeric_terms
    ├── supported_numeric_terms
    ├── required_named_anchors
    ├── supported_named_anchors
    └── reasons
```

Possible rejection reasons include:

```text
insufficient_evidence_count
no_informative_query_terms
insufficient_supported_terms
low_query_term_coverage
low_single_evidence_coverage
missing_numeric_support
missing_named_anchor_support
```

---

## Generation evaluation limitations

### Small benchmark

Ten queries are not enough for broad claims.

### Deterministic provider

The current generation provider is not a production LLM.

### Expected-term metric

Expected-term recall is lexical. It does not measure semantic correctness.

### Citation validity vs semantic support

A citation reference can be structurally valid while still failing to semantically entail a claim.

Current evaluation checks structural citation validity, not full semantic citation correctness.

### No independent answer review

The current benchmark does not yet include independent human answer-quality judgments.

---

## Required generation benchmark expansion

The next generation dataset should include at least 30–40 cases spanning:

- ordinary answerable questions
- unsupported questions
- exact-number/date questions
- fictitious entities
- multi-document synthesis
- conflicting evidence
- partial evidence
- prompt injection inside retrieved text
- malformed provider outputs
- unknown evidence IDs
- missing citations
- provider timeout behavior
- retry behavior

---

# Reproducibility commands

## Generate retrieval pooled candidates

```bash
aeroragx ntrs-build-pooled-candidates \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --previous-qrels-input data/evaluation/qrels_v0_1.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --dense-config configs/dense_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json \
  --top-k-per-retriever 20 \
  --shuffle-seed 42 \
  --internal-output data/evaluation/candidates_v0_2_internal.jsonl \
  --annotation-output data/evaluation/candidates_v0_2_annotation.jsonl
```

## Build retrieval qrels

```bash
aeroragx ntrs-build-qrels-from-annotations \
  --annotations-input data/evaluation/candidates_v0_2_annotation.jsonl \
  --output data/evaluation/qrels_v0_2.jsonl
```

## Evaluate BM25

```bash
aeroragx ntrs-evaluate-bm25 \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_2.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --top-k 10 \
  --report-output artifacts/evaluation/bm25_v0_2.json
```

## Evaluate dense retrieval

```bash
aeroragx ntrs-evaluate-dense \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_2.jsonl \
  --dense-config configs/dense_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json \
  --top-k 10 \
  --report-output artifacts/evaluation/dense_v0_2.json
```

## Evaluate Hybrid RRF

```bash
aeroragx ntrs-evaluate-hybrid \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_2.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --dense-config configs/dense_v0_1.yaml \
  --hybrid-config configs/hybrid_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json \
  --top-k 10 \
  --report-output artifacts/evaluation/hybrid_v0_2.json
```

## Evaluate reranking

```bash
aeroragx ntrs-evaluate-reranker \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_2.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --dense-config configs/dense_v0_1.yaml \
  --hybrid-config configs/hybrid_v0_1.yaml \
  --reranker-config configs/reranker_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json \
  --candidate-top-k 20 \
  --top-k 10 \
  --report-output artifacts/evaluation/reranker_top20_v0_2.json \
  --latency-output artifacts/evaluation/reranker_latency_v0_1.json \
  --hardware-note "MacBook Air, CPU baseline"
```

## Evaluate grounded generation v0.1 behavior

To reproduce the original ungated behavior, run the generation evaluator using a generator configuration without an active sufficiency assessor in code. The tracked report is preserved as:

```text
artifacts/evaluation/generation_v0_1.json
```

## Evaluate sufficiency-gated generation v0.2

```bash
aeroragx ntrs-evaluate-generation \
  --queries-input data/evaluation/generation_queries_v0_1.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --dense-config configs/dense_v0_1.yaml \
  --hybrid-config configs/hybrid_v0_1.yaml \
  --reranker-config configs/reranker_v0_1.yaml \
  --generation-config configs/generation_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_v0_2.json
```

---

# Versioning rules

- Do not overwrite prior qrels.
- Do not overwrite materially different benchmark reports.
- Store changed judgments under a new version.
- Preserve candidate-pool construction parameters.
- Record corpus size and query set.
- Record retriever/model/configuration versions.
- Keep internal retriever metadata separate from blinded annotation data.
- Document assessor provenance and annotation limitations.
- Treat metric changes across qrels versions as benchmark changes, not automatically as model regressions.
- Preserve the v0.1 generation report as the pre-sufficiency baseline.
- Preserve the v0.2 generation report as the sufficiency-gated baseline.
- Expand generation queries under a new dataset version rather than silently modifying the existing ten-query benchmark.
