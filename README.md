# AeroRAG-X

[![CI](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml/badge.svg)](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml)

A production-oriented retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is being developed as a traceable research assistant for aerospace reports. The project currently focuses on reliable NASA Technical Reports Server ingestion, citation-preserving document processing, lexical and semantic retrieval, and reproducible retrieval evaluation.

Every retrieved result preserves its source document, page range, NASA citation URL, source URL, and document checksum.

---

## Current status

AeroRAG-X currently implements an end-to-end text-retrieval baseline over a curated NASA NTRS corpus:

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
       Retrieval evaluation and analysis
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
- human chunk-level relevance judgments
- Recall@5 and Recall@10
- MRR@10 and NDCG@10
- Typer command-line interface
- Ruff, pytest, mypy, coverage, and GitHub Actions

The next major milestone is a pooled `v0.2` relevance dataset built from both BM25 and dense candidates, followed by hybrid retrieval.

---

## Retrieval benchmark v0.1

The current benchmark contains eight aerospace queries and human-selected relevant chunks.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

### Important limitation

The `v0.1` relevance judgments were created from a BM25-generated candidate pool. This may favor BM25 because relevant chunks retrieved only by the dense model were not included in the original annotation pool.

The next evaluation version will:

1. retrieve top candidates from BM25 and dense search;
2. combine and deduplicate the candidates;
3. hide retriever identity during annotation;
4. create pooled relevance judgments;
5. re-evaluate BM25, dense, and hybrid retrieval fairly.

Benchmark artifacts are stored in:

```text
artifacts/evaluation/bm25_v0_1.json
artifacts/evaluation/dense_v0_1.json
```

Evaluation data is stored in:

```text
data/evaluation/queries_v0_1.jsonl
data/evaluation/candidates_v0_1.jsonl
data/evaluation/qrels_v0_1.jsonl
```

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
│       └── dense_v0_1.json
├── configs/
│   ├── base.yaml
│   ├── bm25_v0_1.yaml
│   ├── chunking_v0_1.yaml
│   ├── corpus_v0_1.yaml
│   └── dense_v0_1.yaml
├── data/
│   ├── evaluation/
│   ├── manifests/
│   └── sample/
├── docs/
│   └── architecture.md
├── src/
│   └── aeroragx/
│       ├── evaluation/
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

### Conda setup

```bash
conda create -n aeroragx-py312 python=3.12 -y
conda activate aeroragx-py312

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Verify the installation

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

The GitHub Actions workflow runs the same formatting, linting, testing, coverage, and type-checking pipeline for pull requests and pushes to `main`.

---

## Core workflow

### 1. Search NASA NTRS metadata

```bash
aeroragx ntrs-search \
  --title "thermal management electric aircraft" \
  --limit 5
```

Save results:

```bash
aeroragx ntrs-search \
  --title "solid rocket motor" \
  --limit 10 \
  --output data/sample/ntrs_srm_records.json
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

## Retrieval evaluation

### Build BM25 annotation candidates

```bash
aeroragx ntrs-build-evaluation-candidates \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --top-k 20 \
  --output data/evaluation/candidates_v0_1.jsonl
```

### Evaluate BM25

```bash
aeroragx ntrs-evaluate-bm25 \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_1.jsonl \
  --chunks-input data/processed/ntrs/v0_1/chunks.jsonl \
  --bm25-config configs/bm25_v0_1.yaml \
  --top-k 10 \
  --report-output artifacts/evaluation/bm25_v0_1.json
```

### Evaluate dense retrieval

```bash
aeroragx ntrs-evaluate-dense \
  --queries-input data/evaluation/queries_v0_1.jsonl \
  --qrels-input data/evaluation/qrels_v0_1.jsonl \
  --dense-config configs/dense_v0_1.yaml \
  --embeddings-input artifacts/embeddings/ntrs_v0_1.npy \
  --metadata-input artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  --manifest-input artifacts/embeddings/ntrs_v0_1_manifest.json \
  --top-k 10 \
  --report-output artifacts/evaluation/dense_v0_1.json
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

Corpus definitions, download receipts, extraction receipts, chunking receipts, configurations, relevance judgments, and evaluation reports are versioned separately.

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

- pooled BM25 and dense relevance judgments
- fair `v0.2` retrieval benchmark
- reciprocal-rank-fusion hybrid retrieval
- cross-encoder reranking
- grounded answer generation
- citation verification
- table and figure extraction
- multimodal retrieval
- FastAPI service
- interactive demonstration interface
- Docker packaging and deployment

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

---

## Data attribution and limitations

Metadata and documents retrieved from the NASA Scientific and Technical Information Program should be attributed to NASA STI.

AeroRAG-X does not claim ownership of NASA source documents. Repository manifests, processing code, retrieval code, annotations, and evaluation artifacts are provided for research and development purposes.

The current corpus is a narrow aerospace research collection and should not be interpreted as a complete representation of NASA technical literature.

Future ASRS support will require separate documentation because ASRS narratives are voluntary and de-identified and should not be treated as independently verified factual reports.

---

## License

The AeroRAG-X source code is released under the MIT License. Source documents and external datasets remain subject to their respective terms and attribution requirements.