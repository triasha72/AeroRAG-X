# AeroRAG-X Roadmap

AeroRAG-X is a production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

The project follows an evaluation-first development strategy:

```text
Reliable corpus
-> verified processing
-> lexical + semantic retrieval
-> pooled relevance evaluation
-> hybrid retrieval
-> cross-encoder reranking
-> grounded generation
-> evidence-sufficiency gating
-> hardened provider
-> facet-aware synthesis retrieval
-> generation v0.3 benchmark
-> API serving
-> containerization
-> deployment + observability
-> persistent vector infrastructure
-> multimodal retrieval
```

---

## Current project status

### Completed text-RAG milestone

- [x] NASA NTRS metadata ingestion
- [x] reproducible corpus manifests
- [x] PDF acquisition and checksum validation
- [x] page-level PDF extraction
- [x] citation-preserving overlapping chunks
- [x] BM25 lexical retrieval
- [x] Sentence Transformer dense retrieval
- [x] exact cosine search over 3,233 chunks
- [x] reciprocal-rank-fusion hybrid retrieval
- [x] cross-encoder reranking
- [x] pooled relevance evaluation
- [x] provider-agnostic grounded generation
- [x] deterministic local provider
- [x] OpenAI Responses API provider adapter
- [x] structured provider responses
- [x] prompt versioning
- [x] prompt-injection heuristics
- [x] timeout and bounded retry behavior
- [x] latency/token/cost telemetry
- [x] deterministic evidence-sufficiency gating
- [x] numeric support checks
- [x] named-anchor support checks
- [x] claim-qualifier support checks
- [x] Sufficiency v0.2.1 calibration
- [x] deterministic facet-aware evidence retrieval
- [x] semantic facet verification
- [x] generation v0.3 telemetry benchmark
- [x] 32-query final generation benchmark
- [x] zero answerability failures on the current benchmark
- [x] frozen final benchmark artifacts

### Final generation v0.3 results

| Metric | Baseline | Final |
|---|---:|---:|
| Answerability accuracy | 0.9375 | **1.0000** |
| Answerable completion | 0.9000 | **1.0000** |
| Unsupported refusal | 1.0000 | **1.0000** |
| Claim citation coverage | 1.0000 | **1.0000** |
| Citation-reference validity | 1.0000 | **1.0000** |
| Expected-term recall | 0.9138 | **0.9310** |
| Structural validity | 1.0000 | **1.0000** |
| Provider call-policy accuracy | 0.8750 | **1.0000** |

Final provider telemetry:

```text
Provider calls: 20
Provider bypasses: 12
Total tokens: 58,915
Estimated benchmark cost: $0.103745
P50 provider latency: 5.6394 s
P95 provider latency: 7.6947 s
Retry rate: 0.0
```

The immediate priority is now **FastAPI serving, API validation, Docker, and observability**.

---

## Phase 1 — Repository foundation

- [x] Python package with `src/` layout
- [x] `pyproject.toml`
- [x] editable installation
- [x] Typer CLI
- [x] YAML configuration
- [x] Ruff
- [x] pytest
- [x] coverage reporting
- [x] strict mypy
- [x] GitHub Actions
- [x] feature-branch and pull-request workflow
- [x] MIT license
- [ ] protect `main`
- [ ] require passing CI before merge
- [ ] prevent force pushes to `main`
- [ ] enforce coverage threshold
- [ ] add pre-commit hooks

---

## Phase 2 — Reproducible NASA corpus acquisition

- [x] define initial aerospace corpus
- [x] NASA NTRS metadata search
- [x] normalize NTRS records
- [x] versioned corpus configuration
- [x] document manifests
- [x] PDF-link resolution
- [x] streamed downloads
- [x] `.part` temporary files
- [x] download validation
- [x] checksums
- [x] acquisition receipts
- [x] NASA citation/source URLs
- [ ] formal dataset card
- [ ] corpus inclusion/exclusion criteria
- [ ] corpus-version comparison tooling
- [ ] additional approved aerospace sources

---

## Phase 3 — Processing and provenance

- [x] source-checksum verification
- [x] PDF text extraction
- [x] page-boundary preservation
- [x] empty-page preservation
- [x] page-level records
- [x] extraction receipts
- [x] deterministic overlapping chunks
- [x] document/page identifiers
- [x] page ranges
- [x] citation URLs
- [x] source URLs
- [x] source-document checksums
- [x] chunking receipts
- [ ] add document title to every chunk
- [ ] add publication date to every chunk
- [ ] semantic chunking experiment
- [ ] fixed versus semantic chunking comparison
- [ ] table detection
- [ ] structured table extraction
- [ ] figure detection
- [ ] figure image/caption extraction
- [ ] OCR fallback only when native extraction is unavailable

---

## Phase 4 — Retrieval baselines

### BM25

- [x] tokenization
- [x] inverted index
- [x] configurable `k1`
- [x] configurable `b`
- [x] deterministic tie-breaking
- [x] full chunk provenance
- [x] CLI
- [x] tests
- [x] real NASA corpus search

### Dense retrieval

- [x] Sentence Transformers
- [x] normalized embeddings
- [x] NumPy persistence
- [x] aligned metadata
- [x] versioned manifest
- [x] exact cosine similarity
- [x] CLI
- [x] tests
- [x] index over 3,233 chunks
- [ ] evaluate alternative embedding models
- [ ] embedding-throughput benchmark
- [ ] ANN indexing when scale requires it
- [ ] vector database integration

---

## Phase 5 — Retrieval evaluation

### v0.1

- [x] eight aerospace queries
- [x] BM25 annotation candidates
- [x] relevance judgments
- [x] Recall@5
- [x] Recall@10
- [x] MRR@10
- [x] NDCG@10
- [x] aggregate/per-query reports
- [x] BM25 and dense reports
- [x] candidate-pool bias documented

### pooled v0.2

- [x] top-20 BM25 candidates
- [x] top-20 dense candidates
- [x] candidate combination/deduplication
- [x] blinded annotation records
- [x] deterministic ordering
- [x] 278 candidates reviewed
- [x] 101 relevant / 177 non-relevant labels
- [x] BM25 reevaluation
- [x] dense reevaluation
- [x] Hybrid RRF evaluation
- [x] cross-encoder reranker evaluation
- [ ] independent second-pass relevance audit
- [ ] expand to 25–40 retrieval queries
- [ ] multiple assessors
- [ ] inter-annotator agreement
- [ ] regression thresholds

---

## Phase 6 — Hybrid retrieval

- [x] Reciprocal Rank Fusion
- [x] independent BM25/dense retrieval
- [x] deterministic candidate deduplication
- [x] source ranks and scores
- [x] retrieval provenance
- [x] CLI
- [x] unit tests
- [x] pooled benchmark
- [ ] tune RRF parameters on separate development data

---

## Phase 7 — Cross-encoder reranking

- [x] cross-encoder model
- [x] bounded Hybrid RRF candidate reranking
- [x] retrieval provenance
- [x] CLI
- [x] deterministic fake-scorer tests
- [x] scoring latency
- [x] pooled evaluation
- [ ] alternate reranker benchmark
- [ ] CPU/MPS/CUDA comparison

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

---

## Phase 8 — Grounded answer generation

### Core

- [x] provider protocol
- [x] deterministic provider
- [x] structured provider response
- [x] grounded-answer schema
- [x] claim schema
- [x] authoritative citation schema
- [x] source-document schema
- [x] bounded evidence/context
- [x] citation-ID requirements
- [x] application-side citation resolution
- [x] invalid state rejection
- [x] source-document summaries
- [x] JSON writer
- [x] CLI
- [x] OpenAI Responses API adapter
- [ ] local neural LLM provider
- [ ] neighboring-chunk expansion experiment
- [ ] near-duplicate context-removal experiment

### Evidence sufficiency

- [x] deterministic sufficiency configuration
- [x] informative query-term coverage
- [x] minimum supported-term check
- [x] single-evidence coverage
- [x] numeric-support check
- [x] named-anchor support check
- [x] exact-query threshold
- [x] morphology normalization
- [x] claim-qualifier support
- [x] calibrated technical-compound handling
- [x] auditable rejection reasons
- [x] refusal before provider invocation
- [x] Sufficiency v0.2.1

### Facet-aware evidence

- [x] deterministic shared-facet planning
- [x] facet-specific retrieval
- [x] semantic facet verification
- [x] deduplication
- [x] balanced evidence selection
- [x] ordinary-retrieval fallback
- [x] integrated CLI support
- [x] integrated generation benchmark support
- [ ] broaden facet planner only after additional benchmark coverage

---

## Phase 9 — Provider hardening and safety

### Provider infrastructure

- [x] versioned provider configuration
- [x] structured prompt builder
- [x] prompt version identifier
- [x] OpenAI structured-output adapter
- [x] HTTP transport
- [x] provider factory
- [x] timeout handling
- [x] bounded retries
- [x] retryable/non-retryable transport errors
- [x] structured-response validation
- [x] latency telemetry
- [x] input/output token telemetry
- [x] estimated cost telemetry
- [x] secret redaction

### Guardrails

- [x] retrieved evidence treated as untrusted input
- [x] prompt-injection detection heuristics
- [x] explicit evidence delimiters
- [x] hidden/system prompt extraction patterns
- [x] role-reassignment detection
- [x] tool-execution injection detection
- [x] unknown evidence-ID rejection
- [x] malformed-provider-payload rejection
- [x] provider-error regression tests
- [x] prompt-injection regression tests

### Future hardening

- [ ] broaden adversarial evaluation dataset
- [ ] add semantic prompt-injection classifier experiment
- [ ] add provider circuit-breaker policy
- [ ] add rate-limit specific integration tests
- [ ] add fault-injection benchmark
- [ ] add production secret manager integration

---

## Phase 10 — Generation evaluation

- [x] answerability-labeled queries
- [x] unsupported controls
- [x] answerability accuracy
- [x] answerable completion
- [x] unsupported refusal
- [x] claim citation coverage
- [x] citation-reference validity
- [x] source-document coverage
- [x] expected-term recall
- [x] structural-validity checks
- [x] per-query results
- [x] telemetry evaluation
- [x] deterministic provider baseline
- [x] OpenAI provider baseline
- [x] expanded v0.3 dataset: 32 queries
- [x] multi-document synthesis cases
- [x] provider call/bypass policy metric
- [x] latency/token/cost telemetry
- [x] final 32-query run with zero answerability failures
- [x] final comparison artifact
- [ ] semantic citation-support scoring
- [ ] semantic answer-faithfulness evaluation
- [ ] semantic answer-relevance evaluation
- [ ] independent human review
- [ ] multiple benchmark assessors
- [ ] larger benchmark
- [ ] generation regression thresholds in CI

---

## Phase 11 — FastAPI serving — NEXT

### Application

- [ ] add FastAPI dependency
- [ ] add application factory
- [ ] configure dependency injection
- [ ] add startup/shutdown lifecycle
- [ ] load retrieval/generation components once per process

### Endpoints

- [ ] `GET /health`
- [ ] `GET /ready`
- [ ] `POST /v1/query`
- [ ] request/response Pydantic schemas
- [ ] structured error responses
- [ ] request IDs
- [ ] optional debug metadata policy
- [ ] OpenAPI documentation

### API tests

- [ ] health endpoint
- [ ] readiness endpoint
- [ ] supported query
- [ ] unsupported query
- [ ] blank query rejection
- [ ] invalid request rejection
- [ ] citation preservation
- [ ] provider bypass behavior
- [ ] provider error behavior
- [ ] facet-aware query behavior

---

## Phase 12 — Docker and local service deployment

- [ ] Dockerfile
- [ ] `.dockerignore`
- [ ] reproducible container build
- [ ] non-root runtime user
- [ ] environment-variable documentation
- [ ] health check
- [ ] local container smoke test
- [ ] image-size review
- [ ] dependency caching
- [ ] Docker Compose only if additional services require it

---

## Phase 13 — Observability and reliability

- [ ] structured JSON logging
- [ ] request ID propagation
- [ ] retrieval latency
- [ ] reranker latency
- [ ] facet-retrieval usage
- [ ] sufficiency result
- [ ] provider called/bypassed
- [ ] provider attempts/retries
- [ ] provider latency
- [ ] token counts
- [ ] estimated cost
- [ ] citation count
- [ ] error counters
- [ ] P50/P95 request latency
- [ ] redaction verification
- [ ] OpenTelemetry instrumentation
- [ ] load test
- [ ] failure-mode runbook

---

## Phase 14 — Cloud deployment

- [ ] select deployment target
- [ ] container registry
- [ ] managed secret storage
- [ ] deploy service
- [ ] health/readiness configuration
- [ ] structured logs
- [ ] deployment CI workflow
- [ ] rollback procedure
- [ ] cost estimate
- [ ] public demo policy and abuse limits

---

## Phase 15 — Persistent vector infrastructure

Do this only when the service requirements justify it.

- [ ] PostgreSQL + pgvector development configuration
- [ ] vector-schema migration
- [ ] embeddings/provenance persistence
- [ ] metadata filtering
- [ ] document upsert/delete
- [ ] index-version metadata
- [ ] pgvector retrieval implementation
- [ ] compare pgvector with exact NumPy baseline
- [ ] retrieval latency benchmark
- [ ] backup/restore instructions

---

## Phase 16 — Multimodal report processing

- [ ] figure detection
- [ ] figure-caption extraction
- [ ] page linkage
- [ ] table detection
- [ ] structured table extraction
- [ ] multimodal retrieval records
- [ ] image/table citation representation
- [ ] multimodal evaluation dataset
- [ ] multimodal answer tests
- [ ] OCR fallback policy

---

## Phase 17 — Evaluation maturity

- [ ] larger retrieval benchmark
- [ ] larger generation benchmark
- [ ] conflicting-evidence cases
- [ ] partial-evidence cases
- [ ] adversarial prompt-injection benchmark
- [ ] semantic citation support
- [ ] claim-level entailment evaluation
- [ ] independent human evaluation
- [ ] regression thresholds in CI
- [ ] benchmark versioning policy
- [ ] experiment registry

---

## Release criteria for the next serving milestone

The FastAPI/Docker milestone is complete only when:

```text
local quality gate passes
+
API tests pass
+
supported query returns grounded citations
+
unsupported query bypasses provider when appropriate
+
facet-aware synthesis query works through the API
+
Docker image builds
+
container health/readiness checks pass
+
secrets are not logged
+
request/provider telemetry is structured
```
