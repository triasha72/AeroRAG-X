# AeroRAG-X Roadmap

AeroRAG-X is a production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

The project follows a retrieval-first and evaluation-first development strategy:

```text
Reliable corpus
→ verified processing
→ lexical + semantic retrieval
→ pooled relevance evaluation
→ hybrid retrieval
→ cross-encoder reranking
→ grounded generation
→ evidence-sufficiency gating
→ generation evaluation
→ provider hardening
→ API + vector infrastructure
→ deployment
→ multimodal retrieval
```

---

## Current project status

Implemented:

- NASA NTRS metadata ingestion
- reproducible corpus manifests
- PDF acquisition and checksum validation
- page-level PDF extraction
- citation-preserving overlapping chunks
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- exact cosine search over 3,233 chunks
- generic retrieval interfaces and evaluation
- reciprocal-rank-fusion hybrid retrieval
- cross-encoder reranking
- reranker latency measurement
- deterministic BM25+dense candidate pooling
- blinded annotation records
- pooled v0.2 relevance judgments
- retrieval metrics
- provider-agnostic grounded-generation core
- deterministic local generation provider
- structured claims and authoritative citations
- source-document summaries
- generation evaluation
- deterministic evidence-sufficiency gating
- unsupported-query refusal
- generation baseline v0.1 and sufficiency-gated v0.2

Current generation results:

| Metric | v0.1 | v0.2 |
|---|---:|---:|
| Answerability accuracy | 0.8000 | 1.0000 |
| Answerable completion | 1.0000 | 1.0000 |
| Unsupported refusal | 0.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation-reference validity | 1.0000 | 1.0000 |
| Source-document coverage | 1.0000 | 1.0000 |
| Expected-term recall | 0.9130 | 0.9130 |
| Structural validity | 1.0000 | 1.0000 |

The immediate priority is a real structured-output generation provider plus prompt/response hardening and a larger generation benchmark.

---

## Phase 1 — Repository foundation

- [x] Create Python package with `src/` layout
- [x] Add `pyproject.toml`
- [x] Add editable installation
- [x] Add Typer CLI
- [x] Add YAML configuration
- [x] Add Ruff
- [x] Add pytest
- [x] Add coverage reporting
- [x] Add strict mypy checking
- [x] Add GitHub Actions
- [x] Establish feature-branch and pull-request workflow
- [x] Add MIT license
- [ ] Protect `main`
- [ ] Require passing CI before merge
- [ ] Prevent force pushes to `main`
- [ ] Add enforced coverage threshold
- [ ] Add pre-commit hooks

---

## Phase 2 — Reproducible NASA corpus acquisition

- [x] Define initial aerospace corpus
- [x] Implement NASA NTRS metadata search
- [x] Normalize NTRS records
- [x] Add versioned corpus configuration
- [x] Build document manifests
- [x] Resolve PDF links
- [x] Stream PDF downloads
- [x] Use temporary `.part` files
- [x] Validate downloads
- [x] Calculate checksums
- [x] Record acquisition receipts
- [x] Preserve NASA citation and source URLs
- [ ] Add formal dataset card
- [ ] Document corpus inclusion/exclusion criteria
- [ ] Add corpus-version comparison tooling
- [ ] Add ASRS ingestion
- [ ] Document ASRS-specific limitations and attribution

---

## Phase 3 — Processing and provenance

- [x] Verify source checksums before extraction
- [x] Extract PDF text
- [x] Preserve page boundaries
- [x] Preserve empty pages
- [x] Generate page-level records
- [x] Generate extraction receipts
- [x] Add deterministic overlapping chunks
- [x] Preserve document identifiers
- [x] Preserve page identifiers
- [x] Preserve page ranges
- [x] Preserve citation URLs
- [x] Preserve source URLs
- [x] Preserve source-document checksums
- [x] Generate chunking receipts
- [ ] Add document title to every chunk
- [ ] Add publication date to every chunk
- [ ] Add semantic chunking experiment
- [ ] Compare fixed and semantic chunking
- [ ] Detect tables
- [ ] Extract structured tables
- [ ] Detect figures
- [ ] Extract figure images/captions
- [ ] Add OCR only when native extraction is unavailable

---

## Phase 4 — Retrieval baselines

### BM25

- [x] Tokenization
- [x] Inverted index
- [x] Configurable `k1`
- [x] Configurable `b`
- [x] Deterministic tie-breaking
- [x] Full chunk provenance
- [x] Search CLI
- [x] Unit tests
- [x] Real NASA corpus search

### Dense retrieval

- [x] Sentence Transformers
- [x] Dense retrieval configuration
- [x] Corpus encoding
- [x] Separate query encoding
- [x] Normalized embeddings
- [x] NumPy persistence
- [x] Aligned JSONL metadata
- [x] Versioned index manifest
- [x] Exact cosine similarity
- [x] Dense-index CLI
- [x] Dense-search CLI
- [x] Unit tests
- [x] Build index over 3,233 chunks
- [x] Real semantic searches
- [ ] Evaluate alternative embedding models
- [ ] Measure embedding throughput
- [ ] Add ANN indexing when scale requires it
- [ ] Add vector database integration

---

## Phase 5 — Retrieval evaluation

### v0.1

- [x] Eight aerospace queries
- [x] BM25 annotation candidates
- [x] Chunk-level relevance judgments
- [x] Validate qrel IDs
- [x] Recall@5
- [x] Recall@10
- [x] MRR@10
- [x] NDCG@10
- [x] Aggregate reports
- [x] Per-query reports
- [x] BM25 evaluation CLI
- [x] Dense evaluation CLI
- [x] Evaluation tests
- [x] BM25 report
- [x] Dense report
- [x] Document BM25 candidate-pool bias

### Pooled v0.2

- [x] Top-20 BM25 candidate retrieval
- [x] Top-20 dense candidate retrieval
- [x] Candidate combination
- [x] Deduplication by `chunk_id`
- [x] Internal retriever provenance
- [x] Blinded annotation records
- [x] Deterministic SHA-256 ordering with seed 42
- [x] Carry-forward v0.1 positives
- [x] Review 278 candidates
- [x] Record 101 relevant / 177 non-relevant labels
- [x] Generate `qrels_v0_2.jsonl`
- [x] Re-evaluate BM25
- [x] Re-evaluate dense retrieval
- [x] Evaluate Hybrid RRF
- [x] Evaluate cross-encoder reranker
- [ ] Independent second-pass relevance audit
- [ ] Expand to 25–40 retrieval queries
- [ ] Add multiple assessors
- [ ] Measure inter-annotator agreement
- [ ] Add dedicated per-query error analysis

### Retrieval v0.2 results

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |
| Reranker top-10 | 0.2087 | 0.3024 | 0.7188 | 0.4614 |
| Reranker top-20 | 0.2068 | 0.3375 | 0.8375 | 0.5080 |

---

## Phase 6 — Evaluation refactoring

- [x] Shared retrieval-index protocol
- [x] Common retrieval-hit interface
- [x] Generic `evaluate_retriever`
- [x] Preserve BM25 compatibility wrapper
- [x] Preserve dense compatibility wrapper
- [x] Add Hybrid evaluation
- [x] Add reranker evaluation
- [ ] Add reusable report-comparison module
- [ ] Add benchmark-regression checks
- [ ] Add machine-readable summary index

---

## Phase 7 — Hybrid retrieval

- [x] `configs/hybrid_v0_1.yaml`
- [x] Reciprocal Rank Fusion
- [x] Independent BM25/dense candidate retrieval
- [x] Rank fusion rather than raw-score addition
- [x] Preserve contributing retrievers
- [x] Preserve source ranks and scores
- [x] Deterministic ranking
- [x] Hybrid CLI
- [x] Hybrid unit tests
- [x] Evaluate on v0.2 qrels
- [x] Store `hybrid_v0_2.json`
- [ ] Tune RRF parameters on a separate development set

Fixed configuration:

```yaml
version: "0.1"
rrf_k: 60
bm25_top_k: 50
dense_top_k: 50
default_top_k: 10
```

---

## Phase 8 — Cross-encoder reranking

- [x] Select cross-encoder
- [x] Rerank Hybrid RRF candidates
- [x] Preserve lexical/dense/hybrid provenance
- [x] Reranker configuration
- [x] Reranker CLI
- [x] Fake-scorer deterministic tests
- [x] Reranker latency measurement
- [x] Retrieval evaluation
- [x] Top-10 vs top-20 candidate-depth comparison
- [x] Record model/hardware settings
- [ ] Evaluate alternate rerankers on a separate development set
- [ ] Compare CPU/MPS/CUDA latency on documented hardware

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

---

## Phase 9 — Grounded answer generation

### Core

- [x] Define generation-provider protocol
- [x] Implement deterministic local provider
- [x] Define structured provider response
- [x] Define structured grounded-answer schema
- [x] Define structured claim schema
- [x] Define authoritative citation schema
- [x] Define source-document schema
- [x] Pass reranked chunks with provenance
- [x] Bound evidence depth
- [x] Bound total context characters
- [x] Bound per-chunk characters
- [x] Limit maximum claims
- [x] Preserve retrieval metadata
- [x] Require citation IDs for technical claims when configured
- [x] Resolve provider evidence IDs to authoritative citations
- [x] Reject unknown evidence IDs
- [x] Reject invalid answer states
- [x] Generate source-document summaries
- [x] Add page-aware citation metadata
- [x] Add grounded-answer JSON writer
- [x] Add grounded-answer CLI
- [x] Add deterministic fake-provider tests
- [x] Add deterministic extractive provider
- [ ] Add production API-based provider
- [ ] Add local neural LLM provider
- [ ] Add neighboring-chunk expansion
- [ ] Add explicit near-duplicate context removal

### Evidence sufficiency

- [x] Add deterministic sufficiency configuration
- [x] Add informative query-term coverage
- [x] Add minimum supported-term check
- [x] Add single-evidence concentration check
- [x] Add numeric-support check
- [x] Add named-anchor support check
- [x] Add exact-query stricter threshold
- [x] Add auditable rejection reasons
- [x] Store sufficiency result in retrieval metadata
- [x] Refuse before provider invocation
- [x] Preserve previous behavior when assessor is disabled
- [x] Add integration tests

---

## Phase 10 — Grounded-generation evaluation

### Implemented structural evaluation

- [x] Add answerability-labeled generation queries
- [x] Add expected-answerable cases
- [x] Add unsupported controls
- [x] Add answerability accuracy
- [x] Add answerable completion rate
- [x] Add unsupported refusal rate
- [x] Add claim citation coverage
- [x] Add citation-reference validity
- [x] Add source-document coverage
- [x] Add expected-term lexical recall
- [x] Add structural-validity checks
- [x] Preserve per-query results
- [x] Add evaluation CLI
- [x] Store v0.1 report
- [x] Store sufficiency-gated v0.2 report
- [x] Add deterministic evaluation tests

### v0.1 → v0.2 results

| Metric | v0.1 | v0.2 |
|---|---:|---:|
| Answerability accuracy | 0.8000 | 1.0000 |
| Answerable completion | 1.0000 | 1.0000 |
| Unsupported refusal | 0.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation-reference validity | 1.0000 | 1.0000 |
| Source-document coverage | 1.0000 | 1.0000 |
| Expected-term recall | 0.9130 | 0.9130 |
| Structural validity | 1.0000 | 1.0000 |

### Still required

- [ ] Expand generation benchmark to at least 30–40 questions
- [ ] Add multi-document synthesis cases
- [ ] Add conflicting-evidence cases
- [ ] Add partial-evidence cases
- [ ] Add prompt-injection cases
- [ ] Add malformed-provider-response cases
- [ ] Add timeout/retry cases
- [ ] Add semantic citation-support scoring
- [ ] Add answer-faithfulness evaluation
- [ ] Add semantic answer-relevance evaluation
- [ ] Add independent human review
- [ ] Add regression thresholds for generation metrics

---

## Phase 11 — Provider hardening and agent safety

### Provider infrastructure

- [ ] Add versioned provider configuration
- [ ] Add structured prompt builder
- [ ] Add prompt version identifier
- [ ] Add real structured-output API provider
- [ ] Add provider timeout handling
- [ ] Add bounded retries
- [ ] Add rate-limit handling
- [ ] Add malformed JSON/structured-output recovery policy
- [ ] Record provider latency
- [ ] Record input/output token usage
- [ ] Record estimated cost
- [ ] Redact secrets from logs

### Guardrails

- [ ] Treat retrieved documents as untrusted data
- [ ] Add prompt-injection detection heuristics
- [ ] Ensure retrieved text cannot override system instructions
- [ ] Add output-schema validation failures
- [ ] Add unsupported citation-ID rejection tests
- [ ] Add prompt-injection regression tests
- [ ] Add provider-error regression tests
- [ ] Add adversarial evaluation set

### Narrow research-agent tools

- [ ] Define explicit tool protocol
- [ ] NASA NTRS metadata-search tool
- [ ] corpus-search tool
- [ ] report-comparison tool
- [ ] deterministic unit-conversion/calculator tool
- [ ] tool-call audit records
- [ ] human approval before expensive/destructive operations

---

## Phase 12 — Persistent vector infrastructure and serving

### Vector infrastructure

- [ ] Add PostgreSQL + pgvector development configuration
- [ ] Add vector-schema migrations
- [ ] Persist embeddings and provenance
- [ ] Add metadata filtering
- [ ] Add document upsert
- [ ] Add document deletion
- [ ] Add index/version metadata
- [ ] Add pgvector retrieval implementation
- [ ] Compare pgvector vs exact NumPy baseline
- [ ] Add retrieval latency benchmark
- [ ] Add backup/restore instructions

### FastAPI

- [ ] Add application factory
- [ ] Add health endpoint
- [ ] Add readiness endpoint
- [ ] Add lexical-search endpoint
- [ ] Add semantic-search endpoint
- [ ] Add hybrid-search endpoint
- [ ] Add grounded-answer endpoint
- [ ] Add request/response schemas
- [ ] Add structured error handling
- [ ] Add request IDs
- [ ] Add API tests
- [ ] Add OpenAPI documentation

---

## Phase 13 — Deployment and observability

- [ ] Add Dockerfile
- [ ] Add Docker Compose
- [ ] Add environment-variable documentation
- [ ] Add secrets-management guidance
- [ ] Add structured logging
- [ ] Add OpenTelemetry instrumentation
- [ ] Add latency histograms
- [ ] Add error counters
- [ ] Add retrieval/generation timing breakdown
- [ ] Add health/readiness checks
- [ ] Add load testing
- [ ] Measure P50/P95 latency
- [ ] Estimate deployment cost
- [ ] Add GitHub Actions deployment workflow
- [ ] Add Terraform
- [ ] Deploy to Cloud Run or AWS Fargate
- [ ] Add rollback procedure

---

## Phase 14 — Multimodal report processing

- [ ] Detect figure images
- [ ] Extract figure captions
- [ ] Link figures to source pages
- [ ] Detect tables
- [ ] Extract structured tables
- [ ] Preserve table row/column context
- [ ] Generate figure embeddings
- [ ] Generate table representations
- [ ] Add figure retrieval
- [ ] Add table retrieval
- [ ] Combine text/table/figure candidates
- [ ] Add multimodal citation metadata
- [ ] Add multimodal evaluation queries
- [ ] Add figure/table relevance judgments

---

## Phase 15 — Model adaptation

- [ ] Create train/dev/test split for retrieval/reranking adaptation
- [ ] Fine-tune an aerospace sentence retriever or reranker
- [ ] Use PyTorch + Hugging Face Transformers
- [ ] Add PEFT/LoRA when appropriate
- [ ] Track experiments
- [ ] Evaluate retrieval quality before/after adaptation
- [ ] Measure inference latency
- [ ] Measure memory
- [ ] Evaluate quantization
- [ ] Add model card

---

## Phase 16 — Release hardening

- [ ] Protect `main`
- [ ] Require pull requests
- [ ] Require CI checks
- [ ] Add coverage failure threshold
- [ ] Add dependency vulnerability scanning
- [ ] Add pre-commit configuration
- [ ] Add issue template
- [ ] Add PR template
- [ ] Add changelog
- [ ] Add release automation
- [ ] Add benchmark-regression checks
- [ ] Add dataset card
- [ ] Add final model card
- [ ] Add architecture diagram
- [ ] Add benchmark charts
- [ ] Record demo video
- [ ] Publish `v0.1.0`

---

## Immediate next milestone

Create a new feature branch after merging grounded generation:

```bash
git switch main
git pull --ff-only origin main

git switch -c feat/llm-provider-hardening
git push -u origin feat/llm-provider-hardening
```

Implement:

```text
provider_v0_1.yaml
prompting.py
guardrails.py
structured provider backend
provider telemetry
expanded generation benchmark
prompt-injection tests
provider-failure tests
```

Acceptance criteria:

- current deterministic provider remains supported;
- no secrets are committed;
- retrieved text is treated as untrusted data;
- provider outputs are schema validated;
- unsupported evidence IDs remain rejected;
- timeout and retry behavior are tested;
- prompt-injection cases are included in evaluation;
- all existing retrieval and generation benchmarks remain reproducible.
