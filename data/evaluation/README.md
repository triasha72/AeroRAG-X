# AeroRAG-X Retrieval Evaluation Dataset

## Dataset versions

- `v0.1`: BM25-only candidate-pool benchmark
- `v0.2`: pooled BM25+dense candidate benchmark

## Purpose

This dataset evaluates retrieval systems over the AeroRAG-X NASA technical-report corpus while preserving chunk-level source and page provenance.

## Corpus

- Source: NASA Technical Reports Server documents
- Retrieval unit: citation-preserving text chunk
- Corpus size at benchmark creation: 3,233 chunks
- Chunking configuration: `configs/chunking_v0_1.yaml`

## Queries

The benchmark currently contains eight aerospace retrieval queries covering:

- battery thermal runaway propagation
- fuel-cell-aircraft thermal management
- hybrid-electric propulsion safety
- distributed electric propulsion
- cryogenic hydrogen storage
- aircraft battery cooling
- power-electronics thermal management
- lithium-ion battery fire detection

The small query count makes aggregate scores sensitive to individual relevance decisions. Query expansion is planned.

---

## Files

### Shared query file

- `queries_v0_1.jsonl`: natural-language aerospace retrieval queries used by both benchmark versions

### Version v0.1

- `candidates_v0_1.jsonl`: top BM25 candidates reviewed during initial annotation
- `qrels_v0_1.jsonl`: relevant chunk IDs selected from the BM25 candidate pool

### Version v0.2

- `candidates_v0_2_internal.jsonl`: pooled candidates with retriever provenance, ranks, and scores
- `candidates_v0_2_annotation.jsonl`: blinded candidates with binary relevance labels
- `qrels_v0_2.jsonl`: relevant chunk IDs generated from completed `v0.2` annotations

### Evaluation reports

- `artifacts/evaluation/bm25_v0_1.json`
- `artifacts/evaluation/dense_v0_1.json`
- `artifacts/evaluation/bm25_v0_2.json`
- `artifacts/evaluation/dense_v0_2.json`
- `artifacts/evaluation/hybrid_v0_2.json`

---

## Evaluation metrics

- Recall@5
- Recall@10
- MRR@10
- NDCG@10

Metrics are stored both as aggregate values and per-query results.

---

## Version v0.1 protocol

For each query, the top BM25 candidates were reviewed. Chunks were considered relevant when their text directly addressed the query, contained useful evidence, and preserved valid document and page provenance.

### v0.1 limitation

Because only BM25 candidates were reviewed, relevant chunks retrieved exclusively by dense search could not enter the judgment set. The `v0.1` comparison can therefore favor BM25.

### v0.1 results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

---

## Version v0.2 pooled protocol

For every query:

1. retrieve the top 20 BM25 candidates;
2. retrieve the top 20 dense candidates;
3. combine candidate lists;
4. deduplicate by `chunk_id`;
5. carry forward all relevant `v0.1` chunks;
6. preserve retriever identity, rank, and score in the internal record;
7. remove retriever identity, rank, and score from the annotation record;
8. order blinded candidates deterministically using SHA-256 and shuffle seed `42`;
9. assign a binary relevance label to every candidate;
10. generate `qrels_v0_2.jsonl`;
11. evaluate BM25, dense retrieval, and Hybrid RRF against the same relevance set.

### v0.2 counts

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

A candidate is relevant when the available evidence:

- directly addresses the query;
- explains the requested system, mechanism, hazard, method, or result;
- contains substantive technical information useful for answering the query;
- preserves sufficient source and page provenance.

A candidate is non-relevant when it:

- contains only loose keyword overlap;
- addresses a different subsystem or technical problem;
- contains bibliography or boilerplate without substantive evidence;
- is too fragmented to support a grounded answer;
- mentions the topic without materially addressing the query.

### v0.2 results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |

Hybrid RRF uses fixed parameters (`rrf_k=60`, BM25 depth `50`, dense
depth `50`) and combines source ranks rather than raw retrieval scores.
It has not been tuned against this eight-query benchmark.

---

## Annotation limitations

The initial `v0.2` labels were assigned through a conservative assistant-supported review of candidate text previews.

This means:

- some candidates were judged without full-page or full-document context;
- truncated previews can omit relevant evidence or qualifying language;
- ambiguous candidates were generally labeled non-relevant;
- the labels do not yet represent independent multi-assessor judgments;
- inter-annotator agreement has not been measured.

Before using this dataset for publication-grade claims:

1. conduct an independent second-pass audit;
2. inspect full page context for uncertain candidates;
3. record label changes in a new dataset version;
4. add a second assessor;
5. calculate inter-annotator agreement;
6. expand the query set beyond eight queries.

---

## Internal and blinded records

The internal record may contain:

```text
retrieved_by
bm25_rank
bm25_score
dense_rank
dense_score
```

The blinded annotation record must not contain those fields.

Both records preserve:

```text
candidate_id
chunk_id
document_id
page_start
page_end
text_preview
citation_url
source_url
```

---

## Reproducibility commands

### Generate the pooled candidates

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

### Build qrels from completed annotations

```bash
aeroragx ntrs-build-qrels-from-annotations \
  --annotations-input data/evaluation/candidates_v0_2_annotation.jsonl \
  --output data/evaluation/qrels_v0_2.jsonl
```

### Evaluate BM25

```bash
aeroragx ntrs-evaluate-bm25 \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_2.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --top-k 10 \
  --report-output artifacts/evaluation/bm25_v0_2.json
```

### Evaluate dense retrieval

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

### Evaluate Hybrid RRF

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

---

## Versioning rules

- Do not overwrite prior qrels or evaluation reports.
- Store materially changed judgments under a new version.
- Preserve candidate-pool construction parameters.
- Record corpus size, query set, retrievers, candidate depth, and shuffle seed.
- Keep internal retriever metadata separate from blinded annotation data.
- Document annotation limitations and assessor provenance.
- Treat metric changes across qrels versions as benchmark changes, not automatically as model regressions.
