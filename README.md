# AeroRAG-X

[![CI](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml/badge.svg)](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml)

A production-oriented retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is a traceable research assistant for NASA technical reports. It combines reproducible document acquisition, citation-preserving processing, lexical and semantic retrieval, reciprocal-rank fusion, cross-encoder reranking, deterministic evidence-sufficiency checks, grounded answer generation, and benchmarked evaluation.

Every answer is built from retrieved evidence whose document ID, page range, NASA citation URL, source URL, and source-document checksum are preserved through the pipeline.

---

## Current status

AeroRAG-X now implements an end-to-end text RAG pipeline over a curated NASA Technical Reports Server corpus:

```text
NASA NTRS metadata
        |
        v
Versioned corpus manifest
        |
        v
PDF acquisition + checksum validation
        |
        v
Page-level text extraction
        |
        v
Citation-preserving overlapping chunks
        |
        +-------------------------+
        |                         |
        v                         v
BM25 lexical retrieval     Dense semantic retrieval
        |                         |
        +------------+------------+
                     |
                     v
           Reciprocal Rank Fusion
                     |
                     v
            Hybrid candidates
                     |
                     v
         Cross-encoder reranking
                     |
                     v
        Evidence-sufficiency gate
                     |
          +----------+----------+
          |                     |
          v                     v
   sufficient evidence    insufficient evidence
          |                     |
          v                     v
 Grounded generation       grounded refusal
          |
          v
 Claim-level citation resolution
          |
          v
 Source-document summaries
          |
          v
 Generation evaluation
```

The current text corpus contains **3,233 citation-preserving NASA report chunks**.

### Implemented capabilities

- NASA NTRS metadata search
- reproducible corpus configuration
- document manifests and checksums
- streamed PDF acquisition
- page-level PDF extraction
- extraction and chunking receipts
- citation-preserving overlapping chunks
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- persistent NumPy embedding indexes
- exact cosine-similarity dense search
- reciprocal-rank-fusion hybrid retrieval
- cross-encoder reranking
- preserved BM25, dense, hybrid, and reranker provenance
- generic retrieval evaluation
- deterministic BM25+dense candidate pooling
- blinded relevance annotation
- pooled relevance judgments
- Recall@5, Recall@10, MRR@10, and NDCG@10
- provider-agnostic grounded-generation interface
- deterministic local generation provider
- bounded generation context
- structured answer, claim, citation, and source-document schemas
- authoritative citation resolution from retrieved evidence
- deterministic evidence-sufficiency assessment
- numeric-support checks
- named-anchor support checks
- query-term coverage checks
- evidence-concentration checks
- insufficient-evidence refusal
- generation evaluation
- answerability and refusal metrics
- claim citation coverage
- citation-reference validity
- source-document coverage
- expected-term lexical recall
- structural answer validation
- Typer command-line interface
- Ruff, pytest, strict mypy, coverage, and GitHub Actions

---

## What is not implemented yet

The current generation provider is a **deterministic local extractive baseline**, not a production hosted LLM.

The project does not yet claim semantic answer faithfulness. Current generation evaluation verifies structural grounding, citation integrity, answer/refusal behavior, and a lightweight expected-term heuristic.

Planned next work includes:

- structured hosted or local LLM provider support
- prompt construction and versioning
- prompt-injection defenses
- malformed-provider-response handling
- retry, timeout, latency, token, and cost telemetry
- larger generation benchmarks
- semantic citation-support evaluation
- answer-faithfulness evaluation
- vector-database integration
- FastAPI serving
- Docker and cloud deployment
- multimodal table and figure retrieval

---

## Retrieval benchmarks

### Retrieval benchmark v0.1

The original benchmark contains eight aerospace queries and relevance judgments selected from a BM25-generated candidate pool.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

Because the v0.1 judgments were created from BM25 candidates only, the comparison can favor BM25.

### Pooled retrieval benchmark v0.2

The v0.2 benchmark pools BM25 and dense candidates before relevance assessment.

| Property | Value |
|---|---:|
| Evaluation queries | 8 |
| BM25 depth per query | 20 |
| Dense depth per query | 20 |
| Candidates after deduplication | 278 |
| Relevant labels | 101 |
| Non-relevant labels | 177 |
| Shuffle seed | 42 |
| Corpus size | 3,233 chunks |

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |
| Reranker top-10 | 0.2087 | 0.3024 | 0.7188 | 0.4614 |
| Reranker top-20 | 0.2068 | 0.3375 | 0.8375 | 0.5080 |

The fixed top-20 cross-encoder baseline achieves the highest MRR@10 and NDCG@10 among the current retrieval stages. BM25 retains the highest Recall@5 and Recall@10 on this small benchmark.

The reranker uses:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Current scoring-only CPU latency baseline:

| Field | Value |
|---|---:|
| Queries | 8 |
| Query–chunk pairs | 160 |
| Total scoring seconds | 3.170787 |
| Milliseconds per pair | 19.817420 |
| Hardware | MacBook Air, CPU baseline |

---

## Grounded-generation benchmarks

Generation evaluation currently contains:

```text
8 expected-answerable aerospace questions
2 deliberately unsupported control questions
10 total queries
```

### Generation baseline v0.1

The initial deterministic generator had complete citation structure but answered both unsupported control questions.

| Metric | v0.1 |
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

### Sufficiency-gated baseline v0.2

A deterministic evidence-sufficiency gate was added before provider invocation.

| Metric | v0.1 | v0.2 | Delta |
|---|---:|---:|---:|
| Answerability accuracy | 0.8000 | **1.0000** | +0.2000 |
| Answerable completion | 1.0000 | **1.0000** | +0.0000 |
| Unsupported refusal | 0.0000 | **1.0000** | +1.0000 |
| Claim citation coverage | 1.0000 | **1.0000** | +0.0000 |
| Citation-reference validity | 1.0000 | **1.0000** | +0.0000 |
| Source-document coverage | 1.0000 | **1.0000** | +0.0000 |
| Expected-term recall | 0.9130 | **0.9130** | +0.0000 |
| Structural validity | 1.0000 | **1.0000** | +0.0000 |

On the current ten-query benchmark, the sufficiency gate corrected both unsupported-question failures without rejecting any of the eight expected-answerable queries.

This is an exploratory engineering benchmark, not evidence of general-purpose answerability detection. The query set is small and must be expanded before broader claims are made.

Tracked reports:

```text
artifacts/evaluation/generation_v0_1.json
artifacts/evaluation/generation_v0_2.json
```

---

## Evidence-sufficiency gate

The current deterministic gate evaluates retrieved evidence before generation.

It checks:

- minimum evidence count
- informative query-term coverage
- minimum supported query terms
- concentration of query coverage inside at least one evidence chunk
- exact numeric support for numeric query tokens
- support for acronyms and mixed-case/hyphenated named anchors
- stricter coverage for questions requesting an exact value

Configuration:

```text
configs/sufficiency_v0_1.yaml
```

Example rejection reasons:

```text
insufficient_evidence_count
no_informative_query_terms
insufficient_supported_terms
low_query_term_coverage
low_single_evidence_coverage
missing_numeric_support
missing_named_anchor_support
```

The complete sufficiency decision is preserved in `retrieval_metadata.evidence_sufficiency` so refusals remain auditable.

---

## Grounded answer schema

A grounded answer contains:

```text
query
answer
claims
citations
source_documents
insufficient_evidence
retrieval_metadata
```

A supported claim references one or more citation IDs. Those citation IDs are resolved from authoritative retrieved evidence rather than trusted from free-form provider text.

Each citation preserves:

```text
citation_id
evidence_id
chunk_id
document_id
page_start
page_end
citation_url
source_url
document_sha256
reranker_rank
```

An insufficient-evidence response contains no claims, citations, or source documents.

---

## Dense retrieval baseline

| Setting | Value |
|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Corpus size | 3,233 chunks |
| Embedding dimension | 384 |
| Normalization | Enabled |
| Search method | Exact cosine similarity |
| Stored array format | NumPy `.npy` |

Large generated embedding arrays and duplicated metadata are intentionally excluded from Git. The compact manifest is tracked:

```text
artifacts/embeddings/ntrs_v0_1_manifest.json
```

---

## Installation

AeroRAG-X requires Python 3.12 or newer.

```bash
git clone https://github.com/triasha72/AeroRAG-X.git
cd AeroRAG-X

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Conda is also supported:

```bash
conda create -n aeroragx-py312 python=3.12
conda activate aeroragx-py312
python -m pip install -e ".[dev]"
```

Check the CLI:

```bash
aeroragx --help
```

---

## Important CLI workflows

### Search NASA NTRS metadata

```bash
aeroragx ntrs-search \
  --query "battery thermal runaway"
```

### BM25 search

```bash
aeroragx ntrs-bm25-search \
  --query "battery thermal runaway" \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml
```

### Dense search

```bash
aeroragx ntrs-dense-search \
  --query "battery thermal runaway" \
  --dense-config configs/dense_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json
```

### Hybrid search

```bash
aeroragx ntrs-hybrid-search \
  --query "battery thermal runaway" \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --dense-config configs/dense_v0_1.yaml \
  --hybrid-config configs/hybrid_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json
```

### Cross-encoder reranking

```bash
aeroragx ntrs-reranker-search \
  --query "battery thermal runaway" \
  --candidate-top-k 20 \
  --top-k 10
```

### Generate a grounded answer

```bash
aeroragx ntrs-grounded-answer \
  --query "How can battery thermal runaway propagate in electric aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml
```

### Save a grounded answer as JSON

```bash
aeroragx ntrs-grounded-answer \
  --query "How can battery thermal runaway propagate in electric aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --output /tmp/aeroragx_answer.json
```

### Evaluate grounded generation

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

## Repository structure

```text
AeroRAG-X/
├── .github/
│   └── workflows/
│       └── ci.yml
├── artifacts/
│   ├── embeddings/
│   │   └── ntrs_v0_1_manifest.json
│   └── evaluation/
│       ├── bm25_v0_1.json
│       ├── dense_v0_1.json
│       ├── bm25_v0_2.json
│       ├── dense_v0_2.json
│       ├── hybrid_v0_2.json
│       ├── reranker_top10_v0_2.json
│       ├── reranker_top20_v0_2.json
│       ├── reranker_latency_v0_1.json
│       ├── generation_v0_1.json
│       └── generation_v0_2.json
├── configs/
│   ├── base.yaml
│   ├── bm25_v0_1.yaml
│   ├── chunking_v0_1.yaml
│   ├── corpus_v0_1.yaml
│   ├── dense_v0_1.yaml
│   ├── generation_v0_1.yaml
│   ├── hybrid_v0_1.yaml
│   ├── reranker_v0_1.yaml
│   └── sufficiency_v0_1.yaml
├── data/
│   ├── evaluation/
│   │   ├── README.md
│   │   ├── queries_v0_1.jsonl
│   │   ├── candidates_v0_1.jsonl
│   │   ├── qrels_v0_1.jsonl
│   │   ├── candidates_v0_2_internal.jsonl
│   │   ├── candidates_v0_2_annotation.jsonl
│   │   ├── qrels_v0_2.jsonl
│   │   └── generation_queries_v0_1.jsonl
│   ├── manifests/
│   └── sample/
├── docs/
│   └── architecture.md
├── src/
│   └── aeroragx/
│       ├── evaluation/
│       │   ├── pooling.py
│       │   └── retrieval.py
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── evaluation.py
│       │   ├── grounded.py
│       │   ├── provider.py
│       │   └── sufficiency.py
│       ├── ingestion/
│       │   ├── acquisition.py
│       │   ├── corpus.py
│       │   └── ntrs.py
│       ├── processing/
│       │   ├── chunking.py
│       │   └── pdf.py
│       ├── retrieval/
│       │   ├── bm25.py
│       │   ├── dense.py
│       │   ├── hybrid.py
│       │   └── reranker.py
│       ├── cli.py
│       └── config.py
├── tests/
└── pyproject.toml
```

---

## Evaluation data

Retrieval queries:

```text
data/evaluation/queries_v0_1.jsonl
```

Retrieval judgments:

```text
data/evaluation/qrels_v0_1.jsonl
data/evaluation/qrels_v0_2.jsonl
```

Generation queries:

```text
data/evaluation/generation_queries_v0_1.jsonl
```

Generation reports:

```text
artifacts/evaluation/generation_v0_1.json
artifacts/evaluation/generation_v0_2.json
```

See `data/evaluation/README.md` for protocols, limitations, and reproducibility commands.

---

## Reproducibility and quality checks

Format:

```bash
python -m ruff format .
```

Lint:

```bash
python -m ruff check .
```

Tests with coverage:

```bash
python -m pytest \
  --cov=aeroragx \
  --cov-report=term-missing
```

Strict type checking:

```bash
python -m mypy src/aeroragx
```

Git whitespace validation:

```bash
git diff --check
```

CI is defined in:

```text
.github/workflows/ci.yml
```

---

## Current limitations

### Retrieval benchmark size

The retrieval benchmark contains eight queries. Aggregate metrics are sensitive to individual relevance decisions.

### Retrieval annotation provenance

The pooled v0.2 relevance labels were created through conservative assistant-supported review of stored text previews. An independent audit with fuller source context and additional assessors is required before publication-grade claims.

### Generation benchmark size

Generation evaluation contains only ten queries. The perfect v0.2 answerability/refusal result should therefore be treated as an engineering checkpoint rather than a generalization claim.

### Generation provider

The current provider is deterministic and extractive. A production structured-output LLM provider is not yet integrated.

### Semantic faithfulness

Current citation verification ensures that claim citation IDs resolve to retrieved evidence and valid provenance. It does not yet prove that every cited passage semantically entails every claim.

### Vector search

Dense retrieval currently uses exact cosine similarity over a NumPy matrix. A production vector database is planned for larger corpora and deployed serving.

### Multimodality

Table and figure extraction/retrieval remain future milestones.

---

## Next milestone

The next engineering milestone is **LLM provider hardening**:

```text
structured provider configuration
        |
        v
prompt construction + prompt versioning
        |
        v
structured provider response validation
        |
        v
prompt-injection defenses
        |
        v
timeout + retry behavior
        |
        v
latency, token, and cost metadata
        |
        v
expanded generation evaluation
```

After provider hardening, the project will move to API serving, persistent vector infrastructure, Docker/cloud deployment, monitoring, and multimodal retrieval.

---

## License

MIT
