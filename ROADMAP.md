# AeroRAG-X Roadmap

AeroRAG-X is a production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

The project follows an evaluation-first delivery path:

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
-> FastAPI serving
-> containerization
-> observability
-> private cloud deployment
-> persistent vector infrastructure
-> private cloud deployment
-> persistent vector infrastructure
-> local neural generation
-> parameter-efficient domain adaptation
-> agentic research workflow
-> multimodal retrieval
-> evaluation maturity
-> release and reproducibility
```

## Current project status

### Completed text-RAG capabilities

- [x] NASA NTRS metadata ingestion
- [x] Reproducible corpus manifests
- [x] PDF acquisition and checksum validation
- [x] Page-level PDF extraction
- [x] Citation-preserving overlapping chunks
- [x] BM25 lexical retrieval
- [x] Sentence Transformer dense retrieval
- [x] Exact cosine search over 3,233 chunks
- [x] Reciprocal Rank Fusion hybrid retrieval
- [x] Cross-encoder reranking
- [x] Pooled relevance evaluation
- [x] Provider-agnostic grounded generation
- [x] Deterministic local provider
- [x] OpenAI Responses API provider adapter
- [x] Structured provider responses
- [x] Prompt versioning and injection heuristics
- [x] Timeout and bounded retry behavior
- [x] Latency, token, and cost telemetry
- [x] Deterministic evidence-sufficiency gating
- [x] Numeric, named-anchor, and claim-qualifier checks
- [x] Deterministic facet-aware evidence retrieval
- [x] Semantic facet verification
- [x] Generation v0.3 telemetry benchmark
- [x] 32-query final generation benchmark
- [x] Zero answerability failures on the current benchmark
- [x] Frozen final benchmark artifacts
- [x] Shared reusable RAG runtime
- [x] Production-oriented FastAPI serving path
- [x] Environment-driven local and OpenAI API modes
- [x] Structured API errors and per-request request IDs
- [x] Controlled live OpenAI HTTP validation
- [x] Controlled unsupported-query provider-bypass validation
- [x] Dockerized local serving
- [x] Structured logs, metrics, tracing, and load validation
- [x] Private Cloud Run deployment with authenticated live validation

## Final generation v0.3 results

| Metric | Baseline | Final |
|---|---:|---:|
| Answerability accuracy | 0.9375 | 1.0000 |
| Answerable completion | 0.9000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation-reference validity | 1.0000 | 1.0000 |
| Expected-term recall | 0.9138 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 |
| Provider call-policy accuracy | 0.8750 | 1.0000 |

Final provider telemetry:

| Metric | Value |
|---|---:|
| Provider calls | 20 |
| Provider bypasses | 12 |
| Total tokens | 58,915 |
| Estimated benchmark cost | $0.103745 |
| P50 provider latency | 5.6394 s |
| P95 provider latency | 7.6947 s |
| Retry rate | 0.0 |

## Current priority

Version 0.1.0 freezes a validated evidence-grounded text-RAG baseline.

Post-v0.1 development has added an optional PostgreSQL + pgvector dense-retrieval backend with exact retrieval-equivalence validation and runtime backend selection.

The next technical priority is model-side capability:

1. add a local Hugging Face Transformers generation provider;
2. establish a protected baseline for local neural generation;
3. add PEFT / LoRA domain adaptation;
4. compare base, RAG, LoRA, and LoRA + RAG configurations;
5. add a bounded tool-using research agent;
6. evaluate agent task completion, tool selection, grounding, latency, and failure behavior.

Evaluation remains the governing principle: new model or agent capabilities should be benchmarked against existing baselines rather than adopted solely because they are more complex.

---

## Phase 1 — Repository foundation — IMPLEMENTED

- [x] Python package with `src/` layout
- [x] `pyproject.toml`
- [x] Editable installation
- [x] Typer CLI
- [x] YAML configuration
- [x] Ruff
- [x] pytest
- [x] Coverage reporting
- [x] Strict mypy
- [x] GitHub Actions
- [x] Feature-branch and pull-request workflow
- [x] MIT license

Future repository hardening:

- [x] Protect `main`
- [x] Require passing CI before merge
- [x] Prevent force pushes to `main`
- [ ] Enforce coverage threshold
- [ ] Add pre-commit hooks

## Phase 2 — Reproducible NASA corpus acquisition — IMPLEMENTED

- [x] Define initial aerospace corpus
- [x] NASA NTRS metadata search
- [x] Normalize NTRS records
- [x] Versioned corpus configuration
- [x] Document manifests
- [x] PDF-link resolution
- [x] Streamed downloads
- [x] `.part` temporary files
- [x] Download validation
- [x] Checksums
- [x] Acquisition receipts
- [x] NASA citation and source URLs
- [x] Formal dataset card

Future expansion:

- [ ] Corpus inclusion and exclusion criteria refinement
- [ ] Corpus-version comparison tooling
- [ ] Additional approved aerospace sources

## Phase 3 — Processing and provenance — IMPLEMENTED

- [x] Source-checksum verification
- [x] PDF text extraction
- [x] Page-boundary preservation
- [x] Empty-page preservation
- [x] Page-level records
- [x] Extraction receipts
- [x] Deterministic overlapping chunks
- [x] Document and page identifiers
- [x] Page ranges
- [x] Citation URLs
- [x] Source URLs
- [x] Source-document checksums
- [x] Chunking receipts

Future processing work:

- [ ] Add document title to every chunk
- [ ] Add publication date to every chunk
- [ ] Semantic chunking experiment
- [ ] Fixed versus semantic chunking comparison
- [ ] Table detection and structured table extraction
- [ ] Figure detection and figure-caption extraction
- [ ] OCR fallback when native extraction is unavailable

## Phase 4 — Retrieval baselines — IMPLEMENTED

### BM25

- [x] Tokenization
- [x] Inverted index
- [x] Configurable `k1`
- [x] Configurable `b`
- [x] Deterministic tie-breaking
- [x] Full chunk provenance
- [x] CLI support
- [x] Tests
- [x] Real NASA corpus search

### Dense retrieval

- [x] Sentence Transformers
- [x] Normalized embeddings
- [x] NumPy persistence
- [x] Aligned metadata
- [x] Versioned manifest
- [x] Exact cosine similarity
- [x] CLI support
- [x] Tests
- [x] Index over 3,233 chunks

Future retrieval-baseline work:

- [ ] Evaluate alternative embedding models
- [ ] Embedding-throughput benchmark
- [ ] ANN indexing when scale requires it
- [ ] Vector-database integration when justified

## Phase 5 — Retrieval evaluation — IMPLEMENTED

### v0.1

- [x] Eight aerospace queries
- [x] BM25 annotation candidates
- [x] Relevance judgments
- [x] Recall@5
- [x] Recall@10
- [x] MRR@10
- [x] NDCG@10
- [x] Aggregate and per-query reports
- [x] BM25 and dense reports
- [x] Candidate-pool bias documented

### Pooled v0.2

- [x] Top-20 BM25 candidates
- [x] Top-20 dense candidates
- [x] Candidate combination and deduplication
- [x] Blinded annotation records
- [x] Deterministic ordering
- [x] 278 candidates reviewed
- [x] 101 relevant and 177 non-relevant labels
- [x] BM25 reevaluation
- [x] Dense reevaluation
- [x] Hybrid RRF evaluation
- [x] Cross-encoder reranker evaluation

Future evaluation work:

- [ ] Independent second-pass relevance audit
- [ ] Expand to 25–40 retrieval queries
- [ ] Multiple assessors
- [ ] Inter-annotator agreement
- [ ] Retrieval regression thresholds

## Phase 6 — Hybrid retrieval — IMPLEMENTED

- [x] Reciprocal Rank Fusion
- [x] Independent BM25 and dense retrieval
- [x] Deterministic candidate deduplication
- [x] Source ranks and scores
- [x] Retrieval provenance
- [x] CLI support
- [x] Unit tests
- [x] Pooled benchmark

Future work:

- [ ] Tune RRF parameters on separate development data

## Phase 7 — Cross-encoder reranking — IMPLEMENTED

- [x] Cross-encoder model
- [x] Bounded Hybrid RRF candidate reranking
- [x] Retrieval provenance
- [x] CLI support
- [x] Deterministic fake-scorer tests
- [x] Scoring-latency measurement
- [x] Pooled evaluation

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Future work:

- [ ] Alternate reranker benchmark
- [ ] CPU, MPS, and CUDA comparison

## Phase 8 — Grounded answer generation — IMPLEMENTED

### Core generation

- [x] Provider protocol
- [x] Deterministic provider
- [x] Structured provider response
- [x] Grounded-answer schema
- [x] Claim schema
- [x] Authoritative citation schema
- [x] Source-document schema
- [x] Bounded evidence and context
- [x] Citation-ID requirements
- [x] Application-side citation resolution
- [x] Invalid-state rejection
- [x] Source-document summaries
- [x] JSON writer
- [x] CLI support
- [x] OpenAI Responses API adapter

### Evidence sufficiency

- [x] Deterministic sufficiency configuration
- [x] Informative query-term coverage
- [x] Minimum supported-term check
- [x] Single-evidence coverage
- [x] Numeric-support check
- [x] Named-anchor support check
- [x] Exact-query threshold
- [x] Morphology normalization
- [x] Claim-qualifier support
- [x] Auditable rejection reasons
- [x] Refusal before provider invocation
- [x] Sufficiency v0.2.1 calibration

### Facet-aware evidence

- [x] Deterministic shared-facet planning
- [x] Facet-specific retrieval
- [x] Semantic facet verification
- [x] Deduplication
- [x] Balanced evidence selection
- [x] Ordinary-retrieval fallback
- [x] Integrated CLI support
- [x] Integrated generation-benchmark support

Future work:

- [ ] Local neural LLM provider
- [ ] Neighboring-chunk expansion experiment
- [ ] Near-duplicate context-removal experiment
- [ ] Broaden facet planner after additional benchmark coverage

## Phase 9 — Provider hardening and safety — IMPLEMENTED

### Provider infrastructure

- [x] Versioned provider configuration
- [x] Structured prompt builder
- [x] Prompt version identifier
- [x] OpenAI structured-output adapter
- [x] HTTP transport
- [x] Provider factory
- [x] Timeout handling
- [x] Bounded retries
- [x] Retryable and non-retryable transport errors
- [x] Structured-response validation
- [x] Latency telemetry
- [x] Input and output token telemetry
- [x] Estimated cost telemetry
- [x] Secret redaction

### Guardrails

- [x] Retrieved evidence treated as untrusted input
- [x] Prompt-injection detection heuristics
- [x] Explicit evidence delimiters
- [x] Hidden and system-prompt extraction patterns
- [x] Role-reassignment detection
- [x] Tool-execution injection detection
- [x] Unknown evidence-ID rejection
- [x] Malformed-provider-payload rejection
- [x] Provider-error regression tests
- [x] Prompt-injection regression tests

Future hardening:

- [ ] Broaden adversarial evaluation dataset
- [ ] Semantic prompt-injection classifier experiment
- [ ] Provider circuit-breaker policy
- [ ] Rate-limit-specific integration tests
- [ ] Fault-injection benchmark
- [ ] Production Secret Manager integration

## Phase 10 — Generation evaluation — IMPLEMENTED

- [x] Answerability-labeled queries
- [x] Unsupported controls
- [x] Answerability accuracy
- [x] Answerable completion
- [x] Unsupported refusal
- [x] Claim citation coverage
- [x] Citation-reference validity
- [x] Source-document coverage
- [x] Expected-term recall
- [x] Structural-validity checks
- [x] Per-query results
- [x] Telemetry evaluation
- [x] Deterministic provider baseline
- [x] OpenAI provider baseline
- [x] Expanded v0.3 dataset with 32 queries
- [x] Multi-document synthesis cases
- [x] Provider call and bypass policy metric
- [x] Latency, token, and cost telemetry
- [x] Final 32-query run with zero answerability failures
- [x] Final comparison artifact
- [x] Frozen deterministic-generation regression policy in CI

Future work:

- [ ] Semantic citation-support scoring
- [ ] Semantic answer-faithfulness evaluation
- [ ] Semantic answer-relevance evaluation
- [ ] Independent human review
- [ ] Multiple benchmark assessors
- [ ] Larger benchmark
- [ ] Generation regression thresholds in CI

## Phase 11 — FastAPI serving — IMPLEMENTED

- [x] FastAPI dependency
- [x] Application factory
- [x] Query-service dependency injection
- [x] Startup and shutdown lifespan
- [x] Shared runtime construction
- [x] Load retrieval and generation components once per process
- [x] Environment-driven runtime configuration
- [x] Deterministic local mode
- [x] OpenAI-backed mode
- [x] `GET /health`
- [x] `GET /ready`
- [x] `POST /v1/query`
- [x] Request and response Pydantic schemas
- [x] Structured error responses
- [x] Per-request `X-Request-ID`
- [x] Validation-error mapping
- [x] Provider-error mapping
- [x] Runtime-unavailable mapping
- [x] Safe internal-error mapping
- [x] OpenAPI documentation
- [x] API tests
- [x] Deterministic local HTTP smoke test
- [x] Real NASA retrieval through FastAPI
- [x] Runtime reuse across multiple HTTP requests
- [x] Controlled OpenAI-backed HTTP request
- [x] Provider telemetry validation
- [x] Unsupported-query provider bypass validation

Future work:

- [ ] Extended API regression coverage
- [ ] Optional debug-metadata exposure policy

## Phase 12 — Docker and local service deployment — IMPLEMENTED

- [x] Dockerfile
- [x] `.dockerignore`
- [x] Python 3.12 slim serving image
- [x] CPU-only PyTorch runtime
- [x] Reproducible container build
- [x] Non-root runtime user
- [x] Environment-variable documentation
- [x] Container health check
- [x] Extended model-loading startup allowance
- [x] Generated corpus mounted read-only
- [x] Generated dense index mounted read-only
- [x] Deterministic local container boot
- [x] Container health and readiness validation
- [x] Real NASA-backed query through container
- [x] Grounded claims and authoritative citations through container
- [x] `X-Request-ID` preservation through container
- [x] Reproducible `scripts/docker_smoke.sh` integration test
- [x] Docker image architecture validation
- [x] CPU dependency validation
- [x] Docker image-size review
- [x] Docker build validation in GitHub Actions
- [x] BuildKit GitHub Actions cache

Deferred:

- [ ] Docker Compose when additional services require it

## Phase 13 — Observability and reliability — IMPLEMENTED

- [x] Structured JSON logging
- [x] Request-ID propagation into logs
- [x] Retrieval latency measurement
- [x] Reranker latency measurement
- [x] Facet-retrieval usage telemetry
- [x] Sufficiency result telemetry
- [x] Provider called and bypassed telemetry
- [x] Provider attempts and retries
- [x] Provider latency, token counts, and estimated cost
- [x] Citation-count telemetry
- [x] Error counters
- [x] Prometheus metrics
- [x] P50/P95/P99 request-latency validation
- [x] Redaction verification
- [x] OpenTelemetry instrumentation
- [x] OTLP/HTTP export
- [x] Local OpenTelemetry Collector validation
- [x] Deterministic load test
- [x] Failure-mode runbook

## Phase 14 — Private Cloud Run deployment — IMPLEMENTED

### Completed deployment work

- [x] Artifact Registry image repository
- [x] Immutable image-digest verification
- [x] Cloud Run Gen2 service deployment
- [x] Port `8000` service configuration
- [x] Two CPU cores and 2 GiB memory configuration
- [x] Concurrency of one
- [x] Zero minimum instances and one maximum instance
- [x] 300-second request timeout
- [x] Dedicated Cloud Run runtime service account
- [x] Bucket-scoped `roles/storage.objectViewer` access
- [x] Separate Cloud Storage corpus bucket
- [x] Separate Cloud Storage embeddings bucket
- [x] Read-only Cloud Storage volume mounts
- [x] Byte-for-byte cloud artifact verification
- [x] Private service policy with unauthenticated access disabled
- [x] Authenticated `GET /health` validation
- [x] Authenticated `GET /ready` validation
- [x] Authenticated `POST /v1/query` validation
- [x] Cloud deployment documentation

### Deferred production hardening

- [ ] Deployment automation or infrastructure-as-code
- [ ] Managed Secret Manager integration for cloud-hosted provider credentials
- [ ] Deployment CI workflow
- [ ] Formal rollback automation
- [ ] Cloud budget alerts and cost policy
- [ ] Public-demo policy
- [ ] Public API rate limiting and abuse controls

## Phase 15 — Persistent vector infrastructure — IMPLEMENTED

The first persistent-vector milestone adds PostgreSQL + pgvector as an optional dense backend while retaining exact NumPy search as the lightweight default.

### Completed

- [x] PostgreSQL + pgvector local development configuration
- [x] Versioned vector-store configuration
- [x] Persistent embedding storage
- [x] Citation-preserving chunk provenance
- [x] Transactional chunk/vector upserts
- [x] Embedding-model metadata
- [x] Embedding-dimension validation
- [x] Index-version metadata
- [x] Exact cosine retrieval through pgvector
- [x] NumPy-vs-pgvector backend comparison
- [x] Retrieval-equivalence validation
- [x] Retrieval-latency benchmark
- [x] PostgreSQL integration tests
- [x] PostgreSQL + pgvector service in GitHub Actions
- [x] Runtime-selectable NumPy / pgvector dense backends
- [x] API environment configuration through `AERORAGX_DENSE_BACKEND`
- [x] NumPy retained as the lightweight default

### Measured validation

- 3,233 corpus chunks
- 384-dimensional `sentence-transformers/all-MiniLM-L6-v2` embeddings
- 8 / 8 exact top-10 retrieval matches
- exact-match rate = 1.0
- mean overlap@10 = 1.0
- maximum score delta = 2.8e-07
- identical Recall@10
- identical MRR@10
- identical NDCG@10
- identical Hybrid RRF top-five runtime results for the validated query

The current benchmark showed that NumPy remains lower-latency for the present 3,233-chunk static corpus. pgvector is therefore retained as an optional backend for persistence, transactional updates, database-backed metadata, and future mutable-corpus requirements rather than replacing NumPy by default.

### Deferred scale work

- [ ] Metadata-filtered retrieval API
- [ ] Document deletion workflow
- [ ] Backup and restore runbook
- [ ] Exact pgvector versus HNSW benchmark at materially larger corpus sizes
- [ ] Managed PostgreSQL deployment

## Phase 16 — Multimodal report processing

- [ ] Figure detection
- [ ] Figure-caption extraction
- [ ] Page linkage
- [ ] Table detection
- [ ] Structured table extraction
- [ ] Multimodal retrieval records
- [ ] Image and table citation representation
- [ ] Multimodal evaluation dataset
- [ ] Multimodal answer tests
- [ ] OCR fallback policy

## Phase 17 — Evaluation maturity

- [x] Frozen deterministic 32-query generation baseline
- [x] Versioned generation-regression policy
- [x] Generation quality thresholds enforced in CI
- [x] Development and held-out generation-evaluation splits
- [x] Frozen deterministic v0.4 held-out baseline with 12 queries
- [ ] Larger retrieval benchmark
- [ ] Larger generation benchmark
- [ ] Conflicting-evidence cases
- [ ] Partial-evidence cases
- [ ] Adversarial prompt-injection benchmark
- [ ] Retrieval and end-to-end latency regression thresholds
- [ ] Semantic citation support
- [ ] Semantic answer faithfulness
- [ ] Semantic answer relevance
- [ ] Independent human review
- [ ] Multiple benchmark assessors

## Phase 18 — v0.1.0 release and reproducibility

- [x] Merge the cloud-deployment pull request through green CI
- [x] Protect `main`
- [x] Add a service architecture diagram
- [x] Add one reproducible demo workflow
- [x] Publish benchmark summary
- [x] Publish container and Cloud Run usage
- [x] Create versioned release or tag
- [x] Document project scope, limitations, and reproducible usage