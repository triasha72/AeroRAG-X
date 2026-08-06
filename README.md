# AeroRAG-X

[![CI](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml/badge.svg)](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml)

A production-oriented retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is being developed as a traceable research assistant for aerospace reports. The project currently focuses on reliable NASA Technical Reports Server ingestion, citation-preserving document processing, lexical and semantic retrieval, pooled relevance assessment, and reproducible retrieval evaluation.

Every retrieved result preserves its source document, page range, NASA citation URL, source URL, and document checksum.

---

## Current status

AeroRAG-X currently implements an end-to-end text-retrieval and pooled-evaluation pipeline over a curated NASA NTRS corpus:

```text
NASA NTRS metadata
        |
        v
Corpus manifest
        |
        v
PDF acquisition and checksum validation
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
        Deduplicated pooled candidates
                     |
                     v
       Blinded relevance annotation
                     |
                     v
          Retrieval benchmark v0.2
```

Implemented capabilities include:

- NASA NTRS metadata search
- reproducible corpus definitions
- document manifests and checksums
- streamed PDF acquisition
- page-level PDF extraction
- extraction and chunking receipts
- citation-preserving overlapping chunks
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- persistent NumPy embedding indexes
- curated aerospace evaluation queries
- deterministic BM25+dense candidate pooling
- deduplication by `chunk_id`
- blinded annotation records
- carried-forward `v0.1` relevance judgments
- candidate-level binary relevance labels
- Recall@5 and Recall@10
- MRR@10 and NDCG@10
- Typer command-line interface
- Ruff, pytest, mypy, coverage, and GitHub Actions

The next major milestone is a shared retrieval-evaluation interface, followed by reciprocal-rank-fusion hybrid retrieval.

---

## Retrieval benchmarks

### Benchmark v0.1

The original benchmark contains eight aerospace queries and chunk-level relevance judgments selected from a BM25-generated candidate pool.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

#### Limitation

The `v0.1` relevance judgments were created from BM25 candidates only. This can favor BM25 because relevant chunks retrieved only by dense search were absent from the annotation pool.

### Pooled benchmark v0.2

The `v0.2` benchmark pools results from both retrievers before relevance assessment.

| Property | Value |
|---|---:|
| Evaluation queries | 8 |
| BM25 depth per query | 20 |
| Dense depth per query | 20 |
| Pooled candidates after deduplication | 278 |
| Relevant labels | 101 |
| Non-relevant labels | 177 |
| Annotation shuffle seed | 42 |
| Corpus size | 3,233 chunks |

The protocol:

1. retrieve the top 20 BM25 candidates for every query;
2. retrieve the top 20 dense candidates for every query;
3. combine and deduplicate candidates by `chunk_id`;
4. preserve retriever identity, rank, and score only in an internal record;
5. carry forward relevant `v0.1` chunks for re-review;
6. assign deterministic blinded order using SHA-256 and seed `42`;
7. label each blinded candidate as relevant or non-relevant;
8. generate `qrels_v0_2.jsonl`;
9. re-evaluate BM25 and dense retrieval against the same pooled judgments.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |

Benchmark artifacts:

```text
artifacts/evaluation/bm25_v0_1.json
artifacts/evaluation/dense_v0_1.json
artifacts/evaluation/bm25_v0_2.json
artifacts/evaluation/dense_v0_2.json
```

Evaluation data:

```text
data/evaluation/queries_v0_1.jsonl
data/evaluation/candidates_v0_1.jsonl
data/evaluation/qrels_v0_1.jsonl
data/evaluation/candidates_v0_2_internal.jsonl
data/evaluation/candidates_v0_2_annotation.jsonl
data/evaluation/qrels_v0_2.jsonl
```

### Annotation-quality note

The initial `v0.2` labels were assigned through a conservative assistant-supported review of the stored text previews. Ambiguous candidates were generally marked non-relevant unless the preview contained substantive evidence for the query. The dataset should receive an independent second-pass audit, preferably with full-page or full-document context, before it is presented as a publication-grade benchmark.

---

## Dense retrieval baseline

The dense retrieval baseline uses:

| Setting | Value |
|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Corpus size | 3,233 chunks |
| Embedding dimension | 384 |
| Normalization | Enabled |
| Search method | Exact cosine similarity |
| Stored array format | NumPy `.npy` |

The generated embedding matrix and duplicated chunk metadata are intentionally excluded from Git. The small index manifest is tracked for reproducibility:

```text
artifacts/embeddings/ntrs_v0_1_manifest.json
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
│       └── dense_v0_2.json
├── configs/
│   ├── base.yaml
│   ├── bm25_v0_1.yaml
│   ├── chunking_v0_1.yaml
│   ├── corpus_v0_1.yaml
│   └── dense_v0_1.yaml
├── data/
│   ├── evaluation/
│   │   ├── README.md
│   │   ├── queries_v0_1.jsonl
│   │   ├── candidates_v0_1.jsonl
│   │   ├── qrels_v0_1.jsonl
│   │   ├── candidates_v0_2_internal.jsonl
│   │   ├── candidates_v0_2_annotation.jsonl
│   │   └── qrels_v0_2.jsonl
│   ├── manifests/
│   └── sample/
├── docs/
│   └── architecture.md
├── src/
│   └── aeroragx/
│       ├── evaluation/
│       │   ├── pooling.py
│       │   └── retrieval.py
│       ├── ingestion/
│       │   ├── acquisition.py
│       │   ├── corpus.py
│       │   └── ntrs.py
│       ├── processing/
│       │   ├── chunking.py
│       │   └── pdf.py
│       ├── retrieval/
│       │   ├── bm25.py
│       │   └── dense.py
│       ├── cli.py
│       └── config.py
├── tests/
├── pyproject.toml
├── README.md
└── ROADMAP.md
```

---

## Local setup

AeroRAG-X requires Python 3.12 or later.

```bash
conda create -n aeroragx-py312 python=3.12 -y
conda activate aeroragx-py312

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the installation:

```bash
aeroragx info
aeroragx validate-config
aeroragx --help
```

---

## Quality checks

Run all project checks before committing:

```bash
python -m ruff format .
python -m ruff check .
python -m pytest --cov=aeroragx --cov-report=term-missing
python -m mypy src/aeroragx
```

The GitHub Actions workflow runs formatting, linting, testing, coverage, and type-checking checks for pull requests and pushes to `main`.

---

## Core corpus workflow

### 1. Search NASA NTRS metadata

```bash
aeroragx ntrs-search \
  --title "thermal management electric aircraft" \
  --limit 5
```

### 2. Build the corpus manifest

```bash
aeroragx ntrs-build-manifest \
  --corpus-config configs/corpus_v0_1.yaml \
  --output data/manifests/ntrs_v0_1.jsonl
```

### 3. Download source documents

```bash
aeroragx ntrs-download-documents \
  --manifest-input data/manifests/ntrs_v0_1.jsonl \
  --output-directory data/raw/ntrs/v0_1 \
  --receipts-output data/manifests/ntrs_v0_1_downloads.jsonl
```

### 4. Extract page-level text

```bash
aeroragx ntrs-extract-pages \
  --downloads-input data/manifests/ntrs_v0_1_downloads.jsonl \
  --pages-output data/processed/ntrs/v0_1/pages.jsonl \
  --receipts-output data/manifests/ntrs_v0_1_extraction.jsonl
```

### 5. Build citation-preserving chunks

```bash
aeroragx ntrs-build-chunks \
  --pages-input data/processed/ntrs/v0_1/pages.jsonl \
  --chunking-config configs/chunking_v0_1.yaml \
  --chunks-output data/processed/ntrs/v0_1/chunks.jsonl \
  --receipts-output data/manifests/ntrs_v0_1_chunking.jsonl
```

---

## Search examples

### BM25 lexical search

```bash
aeroragx ntrs-bm25-search \
  --query "aircraft battery cooling system" \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --top-k 5
```

### Build the dense index

```bash
aeroragx ntrs-build-dense-index \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --dense-config configs/dense_v0_1.yaml \
  --embeddings-output artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-output artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-output artifacts/embeddings/ntrs_v0_1_manifest.json
```

### Dense semantic search

```bash
aeroragx ntrs-dense-search \
  --query "How can thermal runaway spread between aircraft battery cells?" \
  --top-k 5
```

---

## Retrieval evaluation workflow

### Build the pooled candidate files

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

### Create qrels from completed annotations

```bash
aeroragx ntrs-build-qrels-from-annotations \
  --annotations-input data/evaluation/candidates_v0_2_annotation.jsonl \
  --output data/evaluation/qrels_v0_2.jsonl
```

### Evaluate BM25 on v0.2

```bash
aeroragx ntrs-evaluate-bm25 \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_2.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --top-k 10 \
  --report-output artifacts/evaluation/bm25_v0_2.json
```

### Evaluate dense retrieval on v0.2

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

---

## Design principles

### Traceability

Every retrieved chunk preserves:

- NASA document identifier
- chunk identifier
- source page or page range
- NASA citation URL
- PDF source URL
- source-document checksum

### Retrieval before generation

Retrieval quality is evaluated independently before an LLM is added. This prevents answer-generation quality from hiding retrieval failures.

### Reproducibility

Corpus definitions, download receipts, extraction receipts, chunking receipts, configurations, candidate pools, relevance judgments, and evaluation reports are versioned separately.

### Blinded evaluation

Retriever identities, ranks, and scores are retained for reproducibility in the internal pool but removed from annotation records to reduce labeling bias.

### Evidence-grounded generation

The future generation system will be required to:

- answer only from retrieved evidence;
- attach citations to technical claims;
- identify insufficient evidence;
- avoid unsupported extrapolation;
- preserve links to original NASA reports.

---

## Planned capabilities

The next development milestones are:

- shared retrieval-index and retrieval-hit interfaces
- generic retrieval evaluation
- reciprocal-rank-fusion hybrid retrieval
- cross-encoder reranking
- grounded answer generation
- citation verification
- table and figure extraction
- multimodal retrieval
- FastAPI service
- interactive demonstration interface
- Docker packaging and deployment
- independent audit and expansion of the evaluation dataset

See [`ROADMAP.md`](ROADMAP.md) for the detailed project plan.

---

## Development rules

1. Work on a dedicated feature or fix branch.
2. Add or update tests for every behavior change.
3. Run Ruff, pytest, coverage, and mypy before committing.
4. Use pull requests for changes merged into `main`.
5. Do not commit raw PDFs, model weights, secrets, or generated embedding matrices.
6. Preserve document, page, checksum, and citation provenance.
7. Record benchmark limitations rather than presenting incomplete results as definitive.
8. Evaluate retrieval independently before adding answer generation.
9. Keep internal retriever metadata out of blinded annotation records.
10. Audit assistant-supported labels before making publication-grade claims.

---

## Data attribution and limitations

Metadata and documents retrieved from the NASA Scientific and Technical Information Program should be attributed to NASA STI.

AeroRAG-X does not claim ownership of NASA source documents. Repository manifests, processing code, retrieval code, annotations, and evaluation artifacts are provided for research and development purposes.

The current corpus is a narrow aerospace research collection and should not be interpreted as a complete representation of NASA technical literature.

The current benchmark contains only eight queries. Aggregate metrics are therefore sensitive to individual queries, candidate-pool depth, annotation decisions, and corpus composition.

Initial `v0.2` annotations were based on candidate text previews and should be independently audited with fuller source context.

Future ASRS support will require separate documentation because ASRS narratives are voluntary and de-identified and should not be treated as independently verified factual reports.

---

## License

The AeroRAG-X source code is released under the MIT License. Source documents and external datasets remain subject to their respective terms and attribution requirements.
