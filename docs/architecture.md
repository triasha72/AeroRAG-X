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
    Independent evaluation
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
- BM25 evaluation
- dense evaluation

Primary module:

```text
src/aeroragx/evaluation/retrieval.py
```

Tracked reports:

```text
artifacts/evaluation/bm25_v0_1.json
artifacts/evaluation/dense_v0_1.json
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

## Current evaluation limitation

The `v0.1` relevance judgments were selected from a BM25-generated candidate pool.

This creates a possible lexical-retrieval bias because dense-only candidates were not available during the original annotation process.

The next evaluation version will:

```text
BM25 top-20 candidates
          +
Dense top-20 candidates
          |
          v
Deduplicated candidate pool
          |
          v
Blinded annotation
          |
          v
Pooled qrels v0.2
```

Hybrid retrieval will be evaluated only after the pooled benchmark is created.

---

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

The next component is pooled candidate generation:

```text
src/aeroragx/evaluation/pooling.py
```

It will combine BM25 and dense candidates while preserving internal retriever provenance and producing a blinded file for manual annotation.

The pooled relevance judgments will then support:

```text
fair BM25 evaluation
        |
fair dense evaluation
        |
hybrid reciprocal-rank fusion
        |
cross-encoder reranking
```