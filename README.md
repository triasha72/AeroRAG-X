# AeroRAG-X

A production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is built around a curated NASA Technical Reports Server (NTRS) corpus. It combines reproducible document acquisition, citation-preserving processing, lexical and semantic retrieval, interchangeable dense-vector backends, Reciprocal Rank Fusion, cross-encoder reranking, deterministic facet-aware evidence selection, evidence-sufficiency gating, structured generation, authoritative claim-level citation resolution, provider telemetry, FastAPI serving, containerization, observability, and private cloud deployment.

Every generated claim is tied back to retrieved evidence whose document ID, page range, NASA citation URL, source URL, and source-document checksum are preserved through the pipeline.

---

## System architecture

```mermaid
flowchart TD
    A["NASA NTRS metadata and PDFs"] --> B["Versioned corpus and citation-preserving chunks"]

    B --> C["BM25 lexical retrieval"]
    B --> D["Sentence Transformer embeddings"]

    D --> E{"Dense backend"}
    E --> F["NumPy exact cosine"]
    E --> G["PostgreSQL + pgvector"]

    C --> H["Hybrid Reciprocal Rank Fusion"]
    F --> H
    G --> H

    H --> I["Cross-encoder reranking"]
    I --> J["Facet-aware evidence retrieval"]
    J --> K["Evidence-sufficiency gate"]
    K --> L["Structured generation"]
    L --> M["Application-side citation resolution"]

    M --> N["Shared RAG runtime"]
    N --> O["Typer CLI"]
    N --> P["FastAPI service"]

    P --> Q["Structured logs + Prometheus + OpenTelemetry"]
    P --> R["Docker"]
    P --> S["Private Cloud Run"]
```

---

## Current status

AeroRAG-X implements an end-to-end text RAG system with CLI and HTTP interfaces.

Current capabilities include:

- curated NASA NTRS corpus with **3,233 citation-preserving chunks**
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- interchangeable **NumPy** and **PostgreSQL + pgvector** dense-retrieval backends
- Reciprocal Rank Fusion hybrid retrieval
- cross-encoder reranking
- deterministic facet-aware evidence retrieval
- evidence-sufficiency gating
- grounded refusals for unsupported questions
- deterministic local generation
- OpenAI Responses API provider support
- authoritative application-side claim citations
- FastAPI serving
- request IDs and structured errors
- non-root Docker serving
- structured JSON logging
- Prometheus metrics
- OpenTelemetry tracing
- deterministic load validation
- GitHub Actions CI
- private Google Cloud Run Gen2 deployment

The NumPy backend remains the lightweight default for the current static corpus. PostgreSQL + pgvector is available as an optional persistent backend and can be selected without changing the downstream Hybrid RRF pipeline.

---

## Project overview

AeroRAG-X explores how an engineering RAG system can remain reproducible, evaluable, and evidence-grounded rather than treating retrieval and generation as a single opaque pipeline.

The project emphasizes:

- provenance preservation
- explicit retrieval evaluation
- protected held-out evaluation
- refusal behavior
- citation validity
- failure analysis
- provider observability
- backend interchangeability
- reproducible deployment

The project includes deterministic regression checks and a protected held-out generation-evaluation split so measured results remain separate from future system tuning.

---

## Reproducible local demo

Run the complete deterministic local API demonstration:

```bash
./scripts/demo_local.sh
```

The default local runtime uses the NumPy dense backend.

---

# Implemented capabilities

## Corpus acquisition and provenance

- NASA NTRS metadata search
- reproducible corpus configuration
- versioned document manifests
- PDF-link resolution
- streamed PDF acquisition
- checksum validation
- acquisition receipts
- page-level PDF extraction
- citation-preserving overlapping chunks
- document identifiers
- page identifiers
- page ranges
- source URLs
- NASA citation URLs
- source-document checksums
- persistent corpus manifests
- persistent embedding manifests

---

## Retrieval and ranking

### Lexical retrieval

- BM25
- deterministic tokenization
- configurable BM25 parameters
- deterministic tie-breaking
- full chunk provenance

### Dense retrieval

- Sentence Transformers
- normalized embeddings
- versioned embedding manifests
- exact cosine similarity
- persistent NumPy embeddings
- optional PostgreSQL + pgvector persistence
- runtime-selectable dense backends

Current embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Current embedding dimension:

```text
384
```

### Hybrid retrieval

- BM25 + dense retrieval
- Reciprocal Rank Fusion
- deterministic candidate deduplication
- preserved source ranks
- preserved source scores
- retrieval provenance
- interchangeable dense backend without changing Hybrid RRF

### Reranking

Current cross-encoder:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Capabilities:

- bounded Hybrid RRF candidate reranking
- deterministic ranking behavior
- source provenance
- scoring-latency measurement

### Facet-aware evidence retrieval

A narrow deterministic facet-aware wrapper supports selected multi-part synthesis queries.

It:

- derives facet-specific searches
- retrieves evidence for each facet
- verifies semantic facet support
- deduplicates by `chunk_id`
- balances evidence across supported facets
- includes original-query evidence
- falls back to ordinary retrieval when facet support is insufficient

The implementation is intentionally constrained and is not presented as a general-purpose agent.

---

## Dense retrieval backends

AeroRAG-X currently supports two dense retrieval implementations behind the same higher-level retrieval interface.

### NumPy exact cosine

The NumPy implementation:

- loads versioned `.npy` embeddings
- loads aligned citation-preserving metadata
- performs exact cosine similarity
- requires no database service
- is the default runtime backend
- has the lowest latency for the current small static corpus

Select it with:

```bash
export AERORAGX_DENSE_BACKEND=numpy
```

or omit the variable because NumPy is the default.

### PostgreSQL + pgvector

The optional pgvector implementation provides:

- persistent vector storage
- persistent chunk provenance
- PostgreSQL-backed metadata
- transactional upserts
- embedding-model metadata
- index-version metadata
- exact cosine retrieval
- database-backed corpus counts
- deterministic NumPy-equivalence validation
- PostgreSQL integration tests in CI
- runtime selection without modifying Hybrid RRF

Install the optional dependencies with:

```bash
python -m pip install -e ".[dev,vector]"
```

Start the local PostgreSQL + pgvector service:

```bash
docker compose -f docker-compose.vector.yml up -d
```

Configure the connection:

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"
```

Load the existing versioned embedding index into PostgreSQL:

```bash
python scripts/load_pgvector.py
```

Select pgvector:

```bash
export AERORAGX_DENSE_BACKEND=pgvector
```

The database can be stopped without deleting its persistent Docker volume:

```bash
docker compose -f docker-compose.vector.yml down
```

Do not use `down -v` unless the database volume should intentionally be deleted.

---

## NumPy vs pgvector validation

The pgvector backend was validated against the existing exact NumPy dense-retrieval implementation using the same versioned embeddings.

Benchmark configuration:

| Property | Value |
|---|---:|
| Corpus chunks | 3,233 |
| Embedding dimension | 384 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Evaluation queries | 8 |
| Retrieval depth | 10 |

### Retrieval equivalence

| Metric | Result |
|---|---:|
| Exact top-10 matches | 8 / 8 |
| Exact-match rate | 1.0000 |
| Mean overlap@10 | 1.0000 |
| Maximum score delta | 2.8e-07 |

### Retrieval quality

| Backend | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|
| NumPy | 0.277778 | 0.552083 | 0.397576 |
| pgvector | 0.277778 | 0.552083 | 0.397576 |

### Local latency

| Backend | Mean | P50 | P95 |
|---|---:|---:|---:|
| NumPy | 7.121 ms | 6.410 ms | 10.068 ms |
| pgvector | 20.517 ms | 20.254 ms | 22.301 ms |

The result does **not** indicate that pgvector is preferable for every workload.

For the current 3,233-chunk static corpus, exact NumPy retrieval remains lower-latency. pgvector is retained as an optional backend because it adds persistent, transactional, database-backed vector infrastructure and provides a path toward mutable corpora and metadata-filtered retrieval.

The comparison artifact is stored at:

```text
artifacts/evaluation/vector_backend_comparison_v0_1.json
```

A runtime smoke test also verified that NumPy and pgvector produce identical Hybrid RRF top-five results for the same technical query.

---

# Grounded generation and safety

AeroRAG-X provides:

- provider-agnostic generation interface
- deterministic local generation provider
- OpenAI Responses API structured provider adapter
- versioned provider configuration
- versioned prompt configuration
- prompt-injection heuristics
- explicit evidence delimiters
- structured-response validation
- timeout handling
- bounded retries
- token telemetry
- latency telemetry
- estimated-cost telemetry
- provider request IDs
- evidence-sufficiency gating
- grounded refusal
- application-side citation resolution

The external model is not trusted to construct final citation metadata.

Instead:

```text
provider claim
      |
      v
evidence ID
      |
      v
AeroRAG-X authoritative metadata
      |
      v
final citation
```

---

# Evaluation

AeroRAG-X treats retrieval and generation evaluation as separate engineering problems.

Implemented evaluation includes:

- retrieval benchmark v0.1
- pooled retrieval benchmark v0.2
- NumPy-vs-pgvector backend comparison
- generation v0.3 benchmark
- deterministic-provider evaluation
- OpenAI-provider evaluation
- protected held-out generation evaluation
- answerability metrics
- refusal metrics
- citation metrics
- structural-validity checks
- latency metrics
- token metrics
- cost metrics
- CI-enforced regression policy
- frozen benchmark artifacts

---

# Generation v0.3 benchmark

The development benchmark contains:

| Category | Queries |
|---|---:|
| Expected-answerable | 20 |
| Unsupported | 12 |
| Total | 32 |

Final configuration:

```text
Sufficiency v0.2.1
+ Facet Retrieval v0.1
+ OpenAI Responses API provider
```

## Final generation results

| Metric | Baseline | Final |
|---|---:|---:|
| Answerability accuracy | 0.9375 | 1.0000 |
| Answerable completion | 0.9000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation-reference validity | 1.0000 | 1.0000 |
| Expected-term recall | 0.9138 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 |

## Provider-routing results

| Metric | Baseline | Final |
|---|---:|---:|
| Provider calls | 22 | 20 |
| Provider bypasses | 10 | 12 |
| Provider call-policy accuracy | 0.8750 | 1.0000 |
| Total tokens | 63,638 | 58,915 |
| Estimated benchmark cost | $0.105733 | $0.103745 |

Measured provider latency:

| Metric | Value |
|---|---:|
| P50 provider latency | 5.6394 s |
| P95 provider latency | 7.6947 s |
| Provider retry rate | 0.0 |

The final development benchmark produced zero answerability failures.

These figures describe the current **32-query development benchmark only**. They are not evidence of universal RAG correctness or general performance outside the evaluated corpus and query set.

Tracked artifacts:

```text
artifacts/evaluation/generation_deterministic_v0_3.json
artifacts/evaluation/generation_deterministic_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3.json
artifacts/evaluation/generation_openai_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3_final.json
artifacts/evaluation/generation_openai_v0_3_final_telemetry.json
artifacts/evaluation/generation_v0_3_final_comparison.json
```

---

# Held-out deterministic evaluation v0.4

A separate 12-query held-out deterministic generation set is maintained independently from the 32-query development benchmark.

The held-out queries were not used to select retrieval, generation, facet-retrieval, or sufficiency settings.

| Category | Queries |
|---|---:|
| Expected-answerable | 6 |
| Unsupported | 6 |
| Total | 12 |

Frozen configuration:

```text
generation_v0_1.yaml
sufficiency_v0_2_1.yaml
facet_retrieval_v0_1.yaml
candidate_top_k = 20
evidence_top_k = 5
```

Results:

| Metric | Held-out result |
|---|---:|
| Answerability accuracy | 0.9167 |
| Answerable completion | 1.0000 |
| Unsupported refusal | 0.8333 |
| Claim citation coverage | 1.0000 |
| Citation-reference validity | 1.0000 |
| Source-document coverage | 1.0000 |
| Expected-term recall | 0.7778 |
| Structural validity | 1.0000 |

The held-out result is recorded as evidence. It is not used as a tuning target or CI threshold.

Tracked artifacts:

```text
data/evaluation/generation_queries_v0_4_heldout.jsonl
tests/test_generation_heldout_split.py
artifacts/evaluation/generation_deterministic_v0_4_heldout_baseline.json
```

---

# Retrieval benchmarks

## Retrieval benchmark v0.1

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

The v0.1 relevance judgments were generated from a BM25 candidate pool, so the comparison may favor BM25.

## Pooled retrieval benchmark v0.2

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

Current cross-encoder:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Scoring-only CPU baseline:

| Field | Value |
|---|---:|
| Queries | 8 |
| Query-chunk pairs | 160 |
| Total scoring time | 3.170787 s |
| Milliseconds per pair | 19.817420 ms |
| Hardware | MacBook Air CPU baseline |

---

# Evidence-sufficiency gate

Primary implementation:

```text
src/aeroragx/generation/sufficiency.py
```

Current configuration:

```text
configs/sufficiency_v0_2_1.yaml
```

The gate checks:

- minimum evidence count
- informative query-term coverage
- minimum supported terms
- single-evidence coverage
- numeric support
- named-anchor support
- claim-qualifier support
- stricter coverage for exact-value questions

The complete sufficiency decision is preserved in retrieval metadata.

If evidence is insufficient, AeroRAG-X can refuse the request before invoking an external generation provider.

---

# Facet-aware retrieval

Primary implementation:

```text
src/aeroragx/generation/facet_retrieval.py
```

Configuration:

```text
configs/facet_retrieval_v0_1.yaml
```

For recognized multi-facet synthesis patterns, the wrapper:

- derives deterministic facet searches
- retrieves evidence for each facet
- validates facet identity
- deduplicates chunks
- balances supported facets
- includes original-query evidence
- falls back to ordinary retrieval when semantic facet support is unavailable

The current implementation is intentionally narrow.

---

# FastAPI service

The same grounded-generation runtime is exposed through FastAPI.

The heavy retrieval and generation runtime is constructed once during application startup and reused across requests.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `GET` | `/ready` | Runtime readiness |
| `POST` | `/v1/query` | Generate one grounded answer |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Swagger/OpenAPI documentation |
| `GET` | `/redoc` | ReDoc documentation |
| `GET` | `/openapi.json` | OpenAPI schema |

---

## Runtime environment

Core runtime environment variables:

```text
AERORAGX_RUNTIME_MODE
AERORAGX_DENSE_BACKEND
AERORAGX_CANDIDATE_TOP_K
AERORAGX_EVIDENCE_TOP_K
```

When pgvector is selected:

```text
AERORAGX_VECTOR_DATABASE_URL
```

Supported generation modes:

```text
local
openai
```

Supported dense backends:

```text
numpy
pgvector
```

---

## Local deterministic mode with NumPy

```bash
unset OPENAI_API_KEY

export AERORAGX_RUNTIME_MODE=local
export AERORAGX_DENSE_BACKEND=numpy
export AERORAGX_CANDIDATE_TOP_K=20
export AERORAGX_EVIDENCE_TOP_K=5

python -m uvicorn \
  aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000
```

Check health:

```bash
curl -sS http://127.0.0.1:8000/health
echo

curl -sS http://127.0.0.1:8000/ready
echo
```

Example query:

```bash
curl -sS \
  -X POST \
  http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why is cryogenic hydrogen storage challenging for aircraft?"
  }'
```

---

## Local deterministic mode with pgvector

Install:

```bash
python -m pip install -e ".[dev,vector]"
```

Start PostgreSQL:

```bash
docker compose -f docker-compose.vector.yml up -d
```

Set:

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"
export AERORAGX_RUNTIME_MODE=local
export AERORAGX_DENSE_BACKEND=pgvector
export AERORAGX_CANDIDATE_TOP_K=20
export AERORAGX_EVIDENCE_TOP_K=5
```

If the database has not yet been populated:

```bash
python scripts/load_pgvector.py
```

Start the API:

```bash
python -m uvicorn \
  aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000
```

The rest of the RAG pipeline is unchanged:

```text
BM25
+
pgvector dense retrieval
↓
Hybrid RRF
↓
cross-encoder reranker
↓
facet-aware evidence selection
↓
evidence-sufficiency gate
↓
grounded generation
```

---

## OpenAI-backed mode

The generation provider and dense-retrieval backend are configured independently.

Example using OpenAI generation and the default NumPy backend:

```bash
export AERORAGX_RUNTIME_MODE=openai
export AERORAGX_DENSE_BACKEND=numpy
export AERORAGX_CANDIDATE_TOP_K=20
export AERORAGX_EVIDENCE_TOP_K=5
export OPENAI_API_KEY="your-key"
```

OpenAI execution uses:

```text
configs/generation_openai_v0_1.yaml
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml
configs/sufficiency_v0_2_1.yaml
configs/facet_retrieval_v0_1.yaml
```

Do not commit API keys.

After testing:

```bash
unset OPENAI_API_KEY
export AERORAGX_RUNTIME_MODE=local
```

---

# Request IDs and structured errors

Every HTTP request receives an AeroRAG-X request identifier.

Responses include:

```text
X-Request-ID: <uuid>
```

Structured errors include the same request ID:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed.",
    "request_id": "<same UUID as X-Request-ID>"
  }
}
```

| HTTP status | Error code | Meaning |
|---:|---|---|
| 422 | `invalid_request` | Request-schema validation failure |
| 502 | `provider_failure` | Generation-provider failure |
| 503 | `runtime_unavailable` | RAG runtime unavailable |
| 500 | `internal_error` | Unexpected internal failure |

Provider and internal exception details are not exposed directly to clients.

---

# Provider telemetry and trust boundary

When an external structured provider is invoked, retrieval metadata can contain:

- provider request ID
- provider name
- model name
- attempt count
- latency
- input tokens
- output tokens
- total tokens
- estimated cost
- prompt-injection assessment
- provider success state
- provider error type

If the sufficiency gate rejects a request before provider invocation, provider telemetry remains absent.

Retrieved evidence is treated as untrusted model input.

The provider may return a relationship such as:

```text
claim -> evidence ID
```

AeroRAG-X then resolves the evidence ID to authoritative application-side metadata.

Final citations preserve:

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

Unknown evidence references are rejected.

---

# Installation

AeroRAG-X requires Python 3.12 or newer.

## Standard development install

```bash
git clone https://github.com/triasha72/AeroRAG-X.git
cd AeroRAG-X

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Development install with pgvector

```bash
python -m pip install -e ".[dev,vector]"
```

## Conda

```bash
conda create -n aeroragx-py312 python=3.12
conda activate aeroragx-py312

python -m pip install --upgrade pip
python -m pip install -e ".[dev,vector]"
```

Check:

```bash
aeroragx --help
```

---

# Important CLI workflows

## Cross-encoder reranking

```bash
aeroragx ntrs-reranker-search \
  --query "battery thermal runaway" \
  --candidate-top-k 20 \
  --top-k 10
```

## Deterministic grounded answer

```bash
aeroragx ntrs-grounded-answer \
  --query "How can battery thermal runaway propagate in electric aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_2_1.yaml
```

## OpenAI grounded answer with facet-aware retrieval

```bash
aeroragx ntrs-grounded-answer \
  --query "What thermal-management challenges are shared by battery-electric and fuel-cell aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_openai_v0_1.yaml \
  --provider-config configs/provider_v0_1.yaml \
  --http-transport-config configs/http_transport_openai_v0_1.yaml \
  --provider-runtime-config configs/provider_runtime_openai_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_2_1.yaml \
  --facet-retrieval-config configs/facet_retrieval_v0_1.yaml
```

---

# Vector-backend development workflows

## Start pgvector

```bash
docker compose -f docker-compose.vector.yml up -d
```

## Check service health

```bash
docker compose -f docker-compose.vector.yml ps
```

## Load versioned embeddings

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"

python scripts/load_pgvector.py
```

## Verify persisted corpus

```bash
docker exec aeroragx-postgres \
  psql -U aeroragx -d aeroragx \
  -c "SELECT COUNT(*) FROM aerorag_chunks;"
```

## Compare vector backends

```bash
python scripts/benchmark_vector_backends.py
```

Comparison output:

```text
artifacts/evaluation/vector_backend_comparison_v0_1.json
```

---

# Dockerized local service

AeroRAG-X can run the FastAPI serving layer inside a non-root Docker container.

The current application image uses CPU-only PyTorch and defaults to the NumPy dense backend.

Build:

```bash
docker build \
  -t aeroragx:local \
  .
```

Generated NASA corpus and dense embedding artifacts are not baked into the image. They are mounted read-only:

```bash
docker run \
  -d \
  --name aeroragx-local \
  -p 8000:8000 \
  -e AERORAGX_RUNTIME_MODE=local \
  -e AERORAGX_DENSE_BACKEND=numpy \
  -e AERORAGX_CANDIDATE_TOP_K=20 \
  -e AERORAGX_EVIDENCE_TOP_K=5 \
  -v "$PWD/data/processed:/app/data/processed:ro" \
  -v "$PWD/artifacts/embeddings:/app/artifacts/embeddings:ro" \
  aeroragx:local
```

Run the integration smoke test:

```bash
./scripts/docker_smoke.sh
```

The smoke test validates:

- required runtime artifacts
- container startup
- health
- readiness
- non-root execution
- mounted NASA artifacts
- grounded generation
- claims
- citations
- deterministic provider behavior
- `X-Request-ID`

See:

```text
docs/docker.md
```

The existing Cloud Run deployment continues to use the lightweight artifact-backed runtime. A managed production PostgreSQL deployment is outside the current pgvector milestone.

---

# Production observability and reliability

Production-oriented observability includes:

- structured JSON logs
- request-ID correlation
- trace/span correlation
- runtime loading events
- HTTP timings
- RAG total latency
- retrieval latency
- BM25 latency
- dense-retrieval latency
- hybrid-fusion latency
- reranker latency
- facet-retrieval telemetry
- sufficiency telemetry
- provider called/bypassed telemetry
- provider attempts
- provider latency
- token counts
- estimated cost
- citation-count telemetry
- Prometheus metrics
- OpenTelemetry spans
- OTLP/HTTP export
- deterministic load testing
- observability privacy controls

Local deterministic load validation completed with zero failures through concurrency four.

| Metric | Value |
|---|---:|
| Requests | 20 |
| Concurrency | 4 |
| P50 latency | 993.928 ms |
| P95 latency | 1117.138 ms |
| P99 latency | 1126.538 ms |
| Throughput | 3.966 requests/s |

See:

```text
docs/observability.md
```

---

# Private Cloud Run deployment

AeroRAG-X has been validated as a private Google Cloud Run Gen2 service.

Current deployment characteristics:

- immutable Artifact Registry image digest
- port `8000`
- two CPU cores
- 2 GiB memory
- concurrency of one
- zero minimum instances
- one maximum instance
- 300-second request timeout
- dedicated runtime service account
- read-only Cloud Storage artifact mounts
- authenticated invocation only

Runtime artifact layout:

| Container path | Contents |
|---|---|
| `/app/data/processed` | NASA corpus chunks |
| `/app/artifacts/embeddings` | embedding matrix, metadata, manifest |

The Cloud Run runtime service account uses bucket-scoped read-only storage access.

Authenticated live validation has been completed for:

```text
GET  /health
GET  /ready
POST /v1/query
```

See:

```text
docs/cloud-run.md
```

The current cloud deployment uses the static artifact-backed retrieval path. pgvector is currently validated as an optional local/CI backend rather than a managed production database dependency.

---

# Validation

Run the local quality gate:

```bash
ruff format .
ruff check .
mypy src/aeroragx
mypy scripts/load_pgvector.py
mypy scripts/benchmark_vector_backends.py
pytest
git diff --check
```

The pgvector integration test requires a running PostgreSQL service when:

```text
AERORAGX_VECTOR_DATABASE_URL
```

is configured.

Start it with:

```bash
docker compose -f docker-compose.vector.yml up -d
```

GitHub Actions provisions PostgreSQL + pgvector for integration testing.

---

# Repository structure

```text
AeroRAG-X/
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── artifacts/
│   ├── embeddings/
│   └── evaluation/
│       └── vector_backend_comparison_v0_1.json
│
├── configs/
│   ├── bm25_v0_1.yaml
│   ├── dense_v0_1.yaml
│   ├── facet_retrieval_v0_1.yaml
│   ├── generation_v0_1.yaml
│   ├── generation_openai_v0_1.yaml
│   ├── hybrid_v0_1.yaml
│   ├── provider_v0_1.yaml
│   ├── reranker_v0_1.yaml
│   ├── sufficiency_v0_2_1.yaml
│   └── vector_store_v0_1.yaml
│
├── data/
│
├── docs/
│   ├── api.md
│   ├── architecture.md
│   ├── cloud-run.md
│   ├── demo.md
│   ├── docker.md
│   ├── evaluation.md
│   ├── generation.md
│   └── observability.md
│
├── scripts/
│   ├── benchmark_vector_backends.py
│   ├── demo_local.sh
│   ├── docker_smoke.sh
│   └── load_pgvector.py
│
├── src/
│   └── aeroragx/
│       ├── api/
│       ├── generation/
│       ├── ingestion/
│       ├── processing/
│       ├── retrieval/
│       │   ├── bm25.py
│       │   ├── dense.py
│       │   ├── hybrid.py
│       │   ├── pgvector_store.py
│       │   ├── reranker.py
│       │   └── vector_store.py
│       ├── py.typed
│       └── runtime.py
│
├── tests/
│   ├── test_api_settings.py
│   ├── test_pgvector_store.py
│   └── test_runtime.py
│
├── docker-compose.vector.yml
├── Dockerfile
├── LICENSE
├── README.md
├── ROADMAP.md
└── pyproject.toml
```

---

# Documentation

- `docs/architecture.md` — architecture, trust boundaries, runtime composition, and failure behavior
- `docs/api.md` — FastAPI endpoints, configuration, errors, and smoke testing
- `docs/docker.md` — local Docker workflow and artifact mounts
- `docs/observability.md` — logs, metrics, tracing, privacy, and load validation
- `docs/cloud-run.md` — private Cloud Run deployment and operations
- `docs/demo.md` — reproducible deterministic local demonstration
- `docs/generation.md` — grounded generation and provider behavior
- `docs/evaluation.md` — retrieval and generation evaluation
- `ROADMAP.md` — completed milestones and future development

---

# Security and limitations

AeroRAG-X currently:

- treats retrieved text as untrusted model input
- uses deterministic prompt-injection heuristics
- validates structured provider output
- rejects unknown evidence IDs
- resolves citation metadata application-side
- redacts provider secrets from transport errors
- refuses unsupported questions before provider invocation when possible
- keeps API keys in environment variables
- runs the Docker service as a non-root user
- mounts generated serving artifacts read-only
- uses least-privilege Cloud Run access
- keeps the deployed Cloud Run API private
- validates pgvector corpus count against the versioned dense-index manifest
- keeps NumPy as the default when the database backend provides no measured advantage for the current workload

Current limitations and non-goals include:

- no general-purpose autonomous agent
- no LLM fine-tuning or domain-adapter training yet
- no semantic entailment verifier
- no table or figure retrieval
- no managed production PostgreSQL deployment
- no vector ANN benchmark at materially larger corpus scale
- no production Secret Manager integration for external-provider credentials
- no public unauthenticated API
- no public API rate limiting or abuse-control layer

---

# Release status

Version `0.1.0` freezes the validated text-RAG baseline with:

- reproducible NASA corpus processing
- lexical and semantic retrieval
- Hybrid RRF
- cross-encoder reranking
- evidence-sufficiency gating
- grounded structured generation
- protected evaluation splits
- FastAPI serving
- Docker
- observability
- private Cloud Run validation

Post-v0.1 development adds a validated optional PostgreSQL + pgvector dense-retrieval backend.

The new backend:

- persists the existing versioned embeddings
- preserves chunk provenance
- matches NumPy retrieval quality on the current benchmark
- can be selected at runtime
- is integration-tested through PostgreSQL in CI
- does not replace the faster NumPy default at the current corpus scale

The next major development direction is model-side capability rather than additional retrieval infrastructure:

```text
local Hugging Face Transformers provider
        ↓
PEFT / LoRA domain adaptation
        ↓
base vs RAG vs LoRA vs LoRA + RAG evaluation
        ↓
tool-using agentic research workflow
        ↓
agent evaluation and failure analysis
```

See `ROADMAP.md` for the complete development sequence.