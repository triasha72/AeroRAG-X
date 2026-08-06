# AeroRAG-X Roadmap

AeroRAG-X is being developed as a production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

The project follows a retrieval-first development strategy:

```text
Reliable corpus
→ verified document processing
→ retrieval baselines
→ pooled evaluation
→ shared evaluation interfaces
→ hybrid retrieval
→ grounded generation
→ multimodal retrieval
→ deployment
```

---

## Current project status

The repository currently includes:

- NASA NTRS metadata ingestion
- reproducible corpus manifests
- PDF acquisition and checksum validation
- page-level PDF extraction
- citation-preserving overlapping chunks
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- exact dense-vector search over 3,233 chunks
- shared retrieval interfaces and generic evaluation
- reciprocal-rank-fusion hybrid retrieval
- deterministic BM25+dense candidate pooling
- blinded annotation records
- pooled `v0.2` relevance judgments
- Recall@5, Recall@10, MRR@10, and NDCG@10
- command-line workflows
- automated tests, formatting, linting, type checking, and CI

Shared retrieval evaluation and reciprocal-rank-fusion hybrid retrieval are complete. The immediate priority is cross-encoder reranking over hybrid candidates, followed by grounded answer generation.

---

## Phase 1 — Repository foundation

- [x] Create Python package with `src/` layout
- [x] Add `pyproject.toml`
- [x] Add editable installation
- [x] Add Typer command-line interface
- [x] Add YAML configuration support
- [x] Add Ruff formatting and linting
- [x] Add pytest
- [x] Add coverage reporting
- [x] Add strict mypy checking
- [x] Add GitHub Actions
- [x] Establish feature-branch and pull-request workflow
- [x] Add MIT license
- [ ] Enable branch protection for `main`
- [ ] Require passing CI before merge
- [ ] Add an enforced coverage threshold

---

## Phase 2 — Reproducible NASA corpus acquisition

- [x] Define a narrow initial aerospace corpus
- [x] Implement NASA NTRS metadata search
- [x] Normalize NTRS records
- [x] Create a versioned corpus configuration
- [x] Build document manifests
- [x] Resolve public PDF links
- [x] Stream PDF downloads
- [x] Use temporary `.part` files during acquisition
- [x] Validate downloads
- [x] Calculate document checksums
- [x] Record acquisition receipts
- [x] Preserve NASA citation and source URLs
- [ ] Add a formal dataset card
- [ ] Document corpus inclusion and exclusion criteria
- [ ] Add corpus version comparison tooling
- [ ] Add ASRS CSV ingestion
- [ ] Document ASRS-specific limitations and attribution

---

## Phase 3 — Document processing and provenance

- [x] Validate source checksums before processing
- [x] Extract PDF text
- [x] Preserve page boundaries
- [x] Preserve empty pages
- [x] Generate page-level records
- [x] Generate extraction receipts
- [x] Add deterministic overlapping word chunks
- [x] Preserve document identifiers
- [x] Preserve page identifiers
- [x] Preserve page ranges
- [x] Preserve citation URLs
- [x] Preserve source URLs
- [x] Preserve source-document checksums
- [x] Generate chunking receipts
- [ ] Add document-title and publication-date metadata to every chunk
- [ ] Add semantic chunking experiment
- [ ] Compare fixed and semantic chunking
- [ ] Detect tables
- [ ] Extract structured tables
- [ ] Detect figures
- [ ] Extract figure images and captions
- [ ] Add OCR only for pages where native extraction is unavailable

---

## Phase 4 — Retrieval baselines

### BM25 lexical retrieval

- [x] Implement tokenization
- [x] Implement an inverted index
- [x] Implement configurable BM25 `k1`
- [x] Implement configurable BM25 `b`
- [x] Add deterministic tie-breaking
- [x] Preserve complete chunk provenance in results
- [x] Add BM25 search CLI
- [x] Add BM25 unit tests
- [x] Run searches against the NASA corpus

### Dense semantic retrieval

- [x] Add Sentence Transformers
- [x] Add dense retrieval configuration
- [x] Encode corpus chunks
- [x] Encode queries separately from documents
- [x] Normalize embeddings
- [x] Persist embeddings as a NumPy matrix
- [x] Persist aligned chunk metadata
- [x] Add a versioned index manifest
- [x] Implement exact cosine-similarity search
- [x] Add dense index construction CLI
- [x] Add dense search CLI
- [x] Add deterministic dense unit tests
- [x] Build an index over 3,233 chunks
- [x] Run real semantic searches
- [ ] Evaluate alternative embedding models
- [ ] Add embedding-batch performance measurements
- [ ] Add approximate nearest-neighbor indexing when corpus scale requires it
- [ ] Add optional vector-database integration

---

## Phase 5 — Retrieval evaluation

### Evaluation framework v0.1

- [x] Create eight aerospace evaluation queries
- [x] Generate BM25 annotation candidates
- [x] Add chunk-level relevance judgments
- [x] Validate relevance IDs against the corpus
- [x] Implement Recall@5
- [x] Implement Recall@10
- [x] Implement MRR@10
- [x] Implement NDCG@10
- [x] Store aggregate metrics
- [x] Store per-query metrics
- [x] Add BM25 evaluation CLI
- [x] Add dense evaluation CLI
- [x] Add evaluation tests
- [x] Generate BM25 benchmark report
- [x] Generate dense benchmark report
- [x] Document BM25 candidate-pool bias

#### v0.1 results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

### Pooled evaluation framework v0.2

- [x] Retrieve top-20 BM25 candidates for every query
- [x] Retrieve top-20 dense candidates for every query
- [x] Combine candidate lists
- [x] Deduplicate candidates by `chunk_id`
- [x] Preserve internal retriever provenance
- [x] Produce a blinded annotation file
- [x] Randomize annotation order deterministically with seed `42`
- [x] Carry forward relevant `v0.1` chunks
- [x] Review and label 278 pooled candidates
- [x] Record 101 relevant and 177 non-relevant labels
- [x] Produce `qrels_v0_2.jsonl`
- [x] Re-evaluate BM25 against `v0.2`
- [x] Re-evaluate dense retrieval against `v0.2`
- [x] Store `bm25_v0_2.json`
- [x] Store `dense_v0_2.json`
- [ ] Independently audit preview-based relevance labels
- [ ] Compare per-query retrieval failures in a dedicated analysis
- [ ] Expand the benchmark to approximately 25–40 queries
- [ ] Add multiple assessors and inter-annotator agreement

#### v0.2 results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |

Annotation limitation: the initial labels were produced through conservative assistant-supported review of candidate text previews. An independent second-pass audit using fuller source context remains required before publication-grade claims.

---

## Phase 6 — Evaluation refactoring

- [x] Introduce a shared retrieval-index protocol
- [x] Introduce a common retrieval-hit interface
- [x] Replace duplicated BM25 and dense evaluation logic
- [x] Implement a generic `evaluate_retriever` function
- [x] Preserve compatibility wrappers for BM25 and dense retrieval
- [ ] Add reusable benchmark-comparison utilities
- [ ] Add `scripts/compare_retrieval_reports.py`
- [ ] Add machine-readable benchmark summaries
- [ ] Add regression checks for benchmark changes

---

## Phase 7 — Hybrid retrieval

- [x] Create `configs/hybrid_v0_1.yaml`
- [x] Implement reciprocal-rank fusion
- [x] Retrieve candidates independently from BM25 and dense search
- [x] Fuse rankings rather than raw scores
- [x] Preserve contributing retrievers and original ranks
- [x] Add deterministic hybrid ranking
- [x] Add hybrid search CLI
- [x] Add hybrid unit tests
- [x] Evaluate hybrid retrieval on `qrels_v0_2.jsonl`
- [x] Store `hybrid_v0_2.json`
- [x] Compare BM25, dense, and hybrid retrieval
- [ ] Tune RRF constant and candidate depths on a separate development set
- [x] Document initial query-level wins and failures

Initial configuration:

```yaml
version: "0.1"
rrf_k: 60
bm25_top_k: 50
dense_top_k: 50
default_top_k: 10
```

#### Initial Hybrid RRF results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |

The hybrid baseline produces the highest MRR@10 among the current
retrievers but lower recall than BM25. It performs strongly on `q001`
and `q002`, retrieves no relevant top-10 chunk for `q004`, and places
the first relevant `q008` chunk at rank 9. RRF parameters remain fixed;
they have not been tuned on the eight-query benchmark.


---

## Phase 8 — Cross-encoder reranking

- [ ] Select a cross-encoder reranking model
- [ ] Rerank the top hybrid candidates
- [ ] Preserve original BM25, dense, and hybrid ranks
- [ ] Add reranking configuration
- [ ] Add reranking CLI
- [ ] Add deterministic tests with a fake scorer
- [ ] Measure reranking latency
- [ ] Evaluate reranked Recall, MRR, and NDCG
- [ ] Compare top-10 and top-20 reranking depths
- [ ] Record model and hardware requirements

---

## Phase 9 — Grounded answer generation

- [ ] Define an LLM-provider abstraction
- [ ] Support local or API-based generation backends
- [ ] Define a structured answer schema
- [ ] Pass retrieved chunks with provenance
- [ ] Require citations for technical claims
- [ ] Refuse when retrieved evidence is insufficient
- [ ] Prevent claims outside retrieved evidence
- [ ] Add source-list generation
- [ ] Add page-aware citation formatting
- [ ] Add answer-generation CLI
- [ ] Add deterministic generation tests using a fake provider
- [ ] Add token-budget management
- [ ] Add context deduplication
- [ ] Add neighboring-chunk expansion

Planned answer schema:

```text
answer
claims
citations
source_documents
insufficient_evidence
retrieval_metadata
```

---

## Phase 10 — Citation verification and answer evaluation

- [ ] Map generated claims to supporting chunks
- [ ] Validate cited chunk identifiers
- [ ] Validate cited page ranges
- [ ] Validate source URLs
- [ ] Detect citations that do not support a claim
- [ ] Detect uncited technical claims
- [ ] Add citation coverage
- [ ] Add citation correctness
- [ ] Add answer faithfulness evaluation
- [ ] Add answer relevance evaluation
- [ ] Add insufficient-evidence test cases
- [ ] Add adversarial unsupported-question tests
- [ ] Store generation-evaluation reports

---

## Phase 11 — Multimodal report processing

- [ ] Extract figure images
- [ ] Extract figure captions
- [ ] Link figures to source pages
- [ ] Extract table structures
- [ ] Preserve row and column context
- [ ] Generate figure embeddings
- [ ] Generate table representations
- [ ] Implement figure retrieval
- [ ] Implement table retrieval
- [ ] Combine text, table, and figure candidates
- [ ] Add multimodal citation metadata
- [ ] Add multimodal evaluation queries
- [ ] Add figure and table relevance judgments

---

## Phase 12 — API and interactive interface

### FastAPI service

- [ ] Add application factory
- [ ] Add health endpoint
- [ ] Add lexical search endpoint
- [ ] Add dense search endpoint
- [ ] Add hybrid search endpoint
- [ ] Add grounded-answer endpoint
- [ ] Add request and response schemas
- [ ] Add structured error handling
- [ ] Add API tests
- [ ] Add OpenAPI documentation

### User interface

- [ ] Add query input
- [ ] Add retriever selection
- [ ] Display answer with inline citations
- [ ] Display source chunks
- [ ] Display NASA report links
- [ ] Display page numbers
- [ ] Display retrieval scores and ranks
- [ ] Display figures and tables
- [ ] Add insufficient-evidence state
- [ ] Add benchmark demonstration mode

---

## Phase 13 — Deployment and release

- [ ] Add Dockerfile
- [ ] Add Docker Compose configuration
- [ ] Add environment-variable documentation
- [ ] Add reproducible index-building instructions
- [ ] Add deployment health checks
- [ ] Add structured logging
- [ ] Add performance measurements
- [ ] Add caching strategy
- [ ] Add security and dependency scanning
- [ ] Add release checklist
- [ ] Record a demonstration video
- [ ] Add architecture diagrams
- [ ] Add benchmark charts
- [ ] Publish release `v0.1.0`
- [ ] Create final model and dataset cards

---

## Project hardening

- [ ] Protect the `main` branch
- [ ] Require pull requests for merges
- [ ] Require CI status checks
- [ ] Prevent force pushes to `main`
- [ ] Add `--cov-fail-under`
- [ ] Add dependency vulnerability scanning
- [ ] Add pre-commit configuration
- [ ] Add issue and pull-request templates
- [ ] Add changelog
- [ ] Add release automation
- [ ] Add reproducibility test for tracked benchmark reports

---

## Immediate next milestone

The next milestone is cross-encoder reranking over the Hybrid RRF
candidate set:

```bash
git switch main
git pull --ff-only origin main

git switch -c feat/cross-encoder-reranking
git push -u origin feat/cross-encoder-reranking
```

The reranking milestone should preserve BM25, dense, and hybrid ranks,
score only a limited hybrid candidate set, measure latency, and evaluate
the reranked results against `qrels_v0_2.jsonl`.
