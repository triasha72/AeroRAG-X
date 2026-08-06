# AeroRAG-X Architecture

AeroRAG-X is a retrieval-first, evidence-grounded system for aerospace technical knowledge.

The architecture separates corpus acquisition, document processing, retrieval, evaluation, and answer generation so that each layer can be tested independently.

---

## Current implemented pipeline

```text
NASA Technical Reports Server
               |
               v
      Metadata normalization
               |
               v
       Versioned corpus manifest
               |
               v
 PDF download + checksum validation
               |
               v
     Page-level PDF extraction
               |
               v
 Citation-preserving text chunks
               |
       +-------+-------+
       |               |
       v               v
 BM25 retrieval   Dense retrieval
       |               |
       +-------+-------+
               |
               v
 Reciprocal Rank Fusion
               |
               v
       Hybrid retrieval
               |
               v
 Cross-encoder reranking
               |
               v
 Generic retrieval evaluation
               |
               v
 Recall@5, Recall@10,
 MRR@10, and NDCG@10
```

The implemented pipeline currently operates over 3,233 citation-preserving NASA report chunks.

---

## Planned target pipeline

```text
NASA NTRS + future ASRS sources
                 |
                 v
      Acquisition and validation
                 |
                 v
 PDF, text, table, and figure extraction
                 |
                 v
 Chunking + metadata + document lineage
                 |
        +--------+--------+
        |                 |
        v                 v
 Dense embeddings    Sparse BM25 index
        |                 |
        +--------+--------+
                 |
                 v
       Hybrid rank fusion
                 |
                 v
      Cross-encoder reranking
                 |
                 v
     Grounded answer generation
                 |
                 v
 Citation and evidence verification
                 |
                 v
  Text, table, and figure presentation
                 |
                 v
 Evaluation, API, UI, and deployment
```

---

## Implemented components

### Ingestion

The ingestion layer provides:

- NASA NTRS metadata search
- record normalization
- versioned corpus definitions
- document manifest generation
- public PDF-link resolution
- streamed downloads
- temporary `.part` files
- checksum calculation
- acquisition receipts

Primary modules:

```text
src/aeroragx/ingestion/ntrs.py
src/aeroragx/ingestion/corpus.py
src/aeroragx/ingestion/acquisition.py
```

### Document processing

The processing layer provides:

- checksum verification before extraction
- page-level PDF text extraction
- preservation of empty and nonempty pages
- extraction receipts
- deterministic overlapping chunks
- page and document provenance
- source and citation URLs
- document checksums
- chunking receipts

Primary modules:

```text
src/aeroragx/processing/pdf.py
src/aeroragx/processing/chunking.py
```

### Lexical retrieval

The BM25 layer provides:

- tokenization
- in-memory inverted indexing
- configurable `k1`
- configurable `b`
- deterministic ranking
- citation-preserving results

Primary module:

```text
src/aeroragx/retrieval/bm25.py
```

### Dense retrieval

The dense layer provides:

- Sentence Transformer document embeddings
- separate query encoding
- normalized vectors
- persisted NumPy embedding matrices
- aligned JSONL chunk metadata
- versioned index manifests
- exact cosine-similarity search
- citation-preserving results

Primary module:

```text
src/aeroragx/retrieval/dense.py
```

Current dense index:

```text
Model: sentence-transformers/all-MiniLM-L6-v2
Chunks: 3,233
Embedding dimension: 384
Normalization: enabled
```

### Hybrid retrieval

The hybrid layer provides:

- independent BM25 and dense candidate retrieval
- reciprocal-rank-fusion scoring
- deterministic cross-retriever deduplication
- preservation of original source ranks and scores
- rank-based fusion without combining raw BM25 and cosine scores
- citation-preserving hybrid results

Primary module and configuration:

```text
src/aeroragx/retrieval/hybrid.py
configs/hybrid_v0_1.yaml
```

Fixed baseline:

```text
RRF constant: 60
BM25 depth: 50
Dense depth: 50
Default output depth: 10
```

### Cross-encoder reranking

The reranking layer provides:

- bounded reranking of Hybrid RRF candidates
- joint query–chunk cross-encoder scoring
- preservation of BM25, dense, and hybrid provenance
- support for finite positive and negative raw logits
- deterministic tie-breaking using Hybrid RRF rank and chunk ID
- scoring-only latency measurement
- generic evaluation compatibility

Primary module and configuration:

```text
src/aeroragx/retrieval/reranker.py
configs/reranker_v0_1.yaml
```

Fixed baseline:

```text
Model: cross-encoder/ms-marco-MiniLM-L6-v2
Candidate depth: 20
Returned depth: 10
Batch size: 16
Device: CPU
```

Measured scoring-only latency:

```text
Queries: 8
Pairs: 160
Total seconds: 3.170787
Milliseconds per pair: 19.817420
Hardware: MacBook Air, CPU baseline
```

### Retrieval evaluation

The evaluation layer provides:

- versioned natural-language queries
- chunk-level relevance judgments
- Recall@5
- Recall@10
- MRR@10
- NDCG@10
- aggregate reports
- per-query reports
- shared retrieval-hit and retrieval-index protocols
- generic retrieval evaluation
- BM25 evaluation
- dense evaluation
- Hybrid RRF evaluation
- cross-encoder reranker evaluation
- top-10 and top-20 candidate-depth comparison

Primary module:

```text
src/aeroragx/evaluation/retrieval.py
```

Tracked reports:

```text
artifacts/evaluation/bm25_v0_1.json
artifacts/evaluation/dense_v0_1.json
artifacts/evaluation/bm25_v0_2.json
artifacts/evaluation/dense_v0_2.json
artifacts/evaluation/hybrid_v0_2.json
artifacts/evaluation/reranker_top10_v0_2.json
artifacts/evaluation/reranker_top20_v0_2.json
artifacts/evaluation/reranker_latency_v0_1.json
```

---

## Provenance model

Each processed chunk preserves:

```text
chunk_id
document_id
chunk_index
page_start
page_end
page_ids
citation_url
source_url
document_sha256
text
word_count
character_count
token_estimate
```

This provenance allows a retrieved result to be traced back to:

1. its chunk;
2. its source page or page range;
3. its NASA document;
4. its source PDF;
5. the checksum of the processed source file.

---

## Retrieval-evaluation separation

Retrieval is evaluated before answer generation is added.

This design prevents a fluent language model response from hiding weak retrieval. The current system measures whether relevant source chunks are found and how highly they are ranked.

Answer-generation evaluation will be introduced separately and will include:

- claim faithfulness;
- citation coverage;
- citation correctness;
- answer relevance;
- insufficient-evidence behavior.

---

## Current benchmark state

The pooled `v0.2` benchmark contains eight queries, 278 reviewed
candidates, and 101 relevant chunk judgments. BM25, dense retrieval,
and Hybrid RRF are evaluated against the same qrels.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |
| Reranker top-10 | 0.2087 | 0.3024 | 0.7188 | 0.4614 |
| Reranker top-20 | 0.2068 | 0.3375 | 0.8375 | 0.5080 |

The top-20 reranker produces the highest MRR@10 and NDCG@10 among
the implemented retrieval stages and improves Recall@10 over Hybrid RRF.
BM25 retains the highest overall Recall@5 and Recall@10. The initial
labels were produced from candidate previews and require an independent
second-pass audit before publication-grade use.

## Design principles

### Traceability

Every technical result should preserve a path back to the original source material.

### Retrieval before generation

Retrieval quality is measured independently before adding an LLM.

### Reproducibility

Corpus manifests, checksums, extraction receipts, chunking receipts, configurations, relevance judgments, and benchmark reports are versioned independently.

### Separation of concerns

Acquisition, processing, retrieval, evaluation, generation, and presentation remain separate modules.

### Evidence-grounded generation

Future answers must:

- use retrieved source evidence;
- cite supporting chunks and pages;
- identify insufficient evidence;
- avoid unsupported technical claims.

---

## Next architectural milestone

The next component is grounded answer generation over the reranked,
citation-preserving evidence set:

```text
BM25 retrieval -------+
                      |
Dense retrieval ------+--> Reciprocal Rank Fusion
                                      |
                                      v
                             Hybrid candidates
                                      |
                                      v
                         Cross-encoder reranking
                                      |
                                      v
                             Reranked evidence
                                      |
                                      v
                         Grounded LLM generation
                                      |
                                      v
                     Claims + citations + refusal
```

The generation layer must preserve:

- chunk, document, page, checksum, and URL provenance;
- final reranker rank and score;
- original Hybrid RRF, BM25, and dense ranks and scores;
- explicit claim-to-evidence relationships;
- an insufficient-evidence state;
- deterministic tests through a fake provider.

Grounded generation will be evaluated separately from retrieval.
