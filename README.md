# AeroRAG-X

A production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is built around a curated NASA Technical Reports Server (NTRS) corpus. It separates corpus provenance, retrieval, reranking, evidence sufficiency, generation, citation resolution, serving, and evaluation into independently testable layers.

The current system supports deterministic local generation, OpenAI structured generation, and local Hugging Face Transformers generation through the same grounded provider interface.

---

## System architecture

```mermaid
flowchart TD
    A["NASA NTRS metadata and PDFs"] --> B["Versioned citation-preserving corpus"]
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

    K --> L{"Generation backend"}
    L --> M["Deterministic local provider"]
    L --> N["OpenAI Responses API"]
    L --> O["Hugging Face Transformers"]

    M --> P["Structured grounded response"]
    N --> P
    O --> P

    P --> Q["Evidence-ID validation"]
    Q --> R["Application-side citation resolution"]
    R --> S["Shared RAG runtime"]

    S --> T["Typer CLI"]
    S --> U["FastAPI"]
    U --> V["Structured logs + Prometheus + OpenTelemetry"]
    U --> W["Docker / Cloud Run"]
```

Dense retrieval and generation are selected independently. For example:

```text
Dense backend:       numpy
Generation backend:  transformers
```

or:

```text
Dense backend:       pgvector
Generation backend:  openai
```

---

## Current capabilities

- curated NASA NTRS corpus with **3,233 citation-preserving chunks**
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- exact NumPy cosine search
- optional PostgreSQL + pgvector persistence
- runtime-selectable dense backends
- Reciprocal Rank Fusion hybrid retrieval
- cross-encoder reranking
- deterministic facet-aware evidence selection
- evidence-sufficiency gating
- grounded refusals before model invocation
- deterministic local generation
- OpenAI Responses API structured generation
- local Hugging Face Transformers generation
- structured JSON validation
- evidence-ID validation
- authoritative application-side claim citations
- provider latency and token telemetry
- FastAPI serving
- request IDs and structured errors
- structured JSON logging
- Prometheus metrics
- OpenTelemetry tracing
- Docker serving
- GitHub Actions CI
- private Google Cloud Run Gen2 validation

The NumPy backend remains the default for the current static corpus. pgvector is available when persistence, transactional mutation, or database-backed metadata is useful.

---

## Design principles

AeroRAG-X is built around several engineering questions:

1. Can the source corpus be reproduced?
2. Can every retrieved chunk retain authoritative provenance?
3. Can retrieval components be evaluated independently?
4. Can unsupported questions be rejected before expensive model inference?
5. Can generation providers be interchangeable without changing the RAG pipeline?
6. Can final citations remain application-controlled rather than model-generated?
7. Can local and remote LLMs share the same grounded structured-provider interface?
8. Can every major capability be compared against a frozen baseline?

The project emphasizes:

- provenance preservation
- reproducibility
- protected evaluation splits
- refusal behavior
- citation validity
- failure analysis
- provider observability
- backend interchangeability
- reproducible deployment

---

# Reproducible local workflows

## Deterministic local demo

```bash
./scripts/demo_local.sh
```

The deterministic runtime uses NumPy dense retrieval by default and does not require an external generation API.

## Real local Transformers smoke test

```bash
python scripts/smoke_transformers.py
```

The smoke script loads the complete runtime once and runs:

- one supported aerospace query, which must invoke the local model and return grounded citations;
- one deliberately unsupported query, which must be rejected by the evidence-sufficiency gate before local-model inference.

The real-model smoke test is intentionally not part of normal CI because model weights may need to be downloaded.

---

# Corpus acquisition and provenance

The NASA processing pipeline includes:

- NTRS metadata search
- reproducible corpus configuration
- versioned manifests
- PDF-link resolution
- streamed acquisition
- partial-download handling
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
- embedding manifests

Provenance is preserved through retrieval, generation, and citation resolution.

---

# Retrieval and ranking

## BM25

The lexical retriever supports deterministic tokenization, configurable BM25 parameters, deterministic tie-breaking, and full chunk provenance.

## Dense retrieval

Current embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Embedding dimension:

```text
384
```

Dense retrieval can use either:

```text
NumPy exact cosine
PostgreSQL + pgvector
```

## Hybrid retrieval

BM25 and dense results are combined with Reciprocal Rank Fusion while preserving source ranks, scores, and chunk provenance.

## Cross-encoder reranking

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

The reranker operates over a bounded Hybrid RRF candidate set and records scoring latency separately.

## Facet-aware evidence retrieval

A deterministic facet-aware wrapper supports selected multi-part synthesis questions. It can derive facet-specific searches, validate facet support, deduplicate chunks, balance evidence, and fall back to ordinary retrieval.

The current implementation is intentionally constrained and is not presented as a general-purpose autonomous agent.

---

# Dense retrieval backends

## NumPy exact cosine

The NumPy backend:

- loads versioned `.npy` embeddings
- loads aligned metadata
- performs exact cosine similarity
- requires no database service
- remains the default for the current corpus

Select explicitly with:

```bash
export AERORAGX_DENSE_BACKEND=numpy
```

## PostgreSQL + pgvector

Install optional dependencies:

```bash
python -m pip install -e ".[dev,vector]"
```

Start the local service:

```bash
docker compose -f docker-compose.vector.yml up -d
```

Configure the connection:

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"
```

Load the existing versioned embeddings:

```bash
python scripts/load_pgvector.py
```

Select pgvector:

```bash
export AERORAGX_DENSE_BACKEND=pgvector
```

Stop PostgreSQL while preserving its volume:

```bash
docker compose -f docker-compose.vector.yml down
```

Do not use `down -v` unless the persistent database volume should intentionally be deleted.

---

# NumPy vs pgvector validation

| Property | Value |
|---|---:|
| Corpus chunks | 3,233 |
| Embedding dimension | 384 |
| Evaluation queries | 8 |
| Retrieval depth | 10 |

## Retrieval equivalence

| Metric | Result |
|---|---:|
| Exact top-10 matches | 8 / 8 |
| Exact-match rate | 1.0000 |
| Mean overlap@10 | 1.0000 |
| Maximum score delta | 2.8e-07 |

## Retrieval quality

| Backend | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|
| NumPy | 0.277778 | 0.552083 | 0.397576 |
| pgvector | 0.277778 | 0.552083 | 0.397576 |

## Local latency

| Backend | Mean | P50 | P95 |
|---|---:|---:|---:|
| NumPy | 7.121 ms | 6.410 ms | 10.068 ms |
| pgvector | 20.517 ms | 20.254 ms | 22.301 ms |

At the current corpus scale, NumPy remains the lower-latency option. pgvector is retained for persistence, transactional updates, and future mutable-corpus requirements.

Comparison artifact:

```text
artifacts/evaluation/vector_backend_comparison_v0_1.json
```

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
- stricter behavior for exact-value questions

If evidence is insufficient, the generation provider can be bypassed completely. This improves grounding behavior and avoids unnecessary model latency.

---

# Generation backends

Supported runtime modes:

```text
local
openai
transformers
```

Select the mode with:

```bash
export AERORAGX_RUNTIME_MODE=<mode>
```

## Deterministic local generation

```bash
export AERORAGX_RUNTIME_MODE=local
```

This provider is useful for deterministic regression tests, CI, and reproducible local demos.

## OpenAI structured generation

```bash
export AERORAGX_RUNTIME_MODE=openai
export OPENAI_API_KEY="your-key"
```

Relevant configuration:

```text
configs/generation_openai_v0_1.yaml
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml
```

Do not commit API keys.

## Local Hugging Face Transformers generation

```bash
export AERORAGX_RUNTIME_MODE=transformers
export AERORAGX_DENSE_BACKEND=numpy
```

Current first local baseline:

```text
Qwen/Qwen3-0.6B
```

Relevant configuration:

```text
configs/generation_transformers_v0_1.yaml
configs/transformers_runtime_v0_1.yaml
configs/provider_v0_1.yaml
```

The local transport supports:

- Hugging Face `AutoTokenizer`
- Hugging Face `AutoModelForCausalLM`
- model-specific chat templates
- automatic CUDA / Apple MPS / CPU device selection
- configurable dtype
- deterministic decoding
- optional thinking control
- input-token budget validation
- bounded output generation
- strict JSON parsing
- evidence-ID validation
- input/output token telemetry
- provider latency telemetry
- zero external API-token cost

The Transformers path reuses the existing `StructuredGenerationProvider`; it does not create a separate RAG implementation.

```text
retrieved evidence
      ↓
grounded prompt
      ↓
TransformersStructuredModelTransport
      ↓
local causal LM
      ↓
structured JSON payload
      ↓
Pydantic validation
      ↓
evidence-ID validation
      ↓
application-side citation resolution
```

---

# Real local-model validation

The real smoke workflow has been validated with:

```text
Model:         Qwen/Qwen3-0.6B
Dense backend: NumPy
Device:        Apple MPS
```

## Supported case

Query:

```text
How can battery thermal runaway propagate in electric aircraft?
```

Observed smoke behavior:

| Field | Result |
|---|---:|
| Evidence sufficient | Yes |
| Provider called | Yes |
| Provider succeeded | Yes |
| Claims | 1 |
| Citations | 1 |
| Source documents | 1 |
| Input tokens | 2,295 |
| Output tokens | 218 |
| Total tokens | 2,513 |
| External API cost | $0 |
| Provider latency | ~12.2 s |

## Unsupported case

Query:

```text
What was the exact cabin temperature recorded during NASA's 2047 hydrogen-electric aircraft certification flight?
```

Observed smoke behavior:

| Field | Result |
|---|---:|
| Evidence sufficient | No |
| Provider called | No |
| Claims | 0 |
| Citations | 0 |
| Source documents | 0 |

These are smoke validations, not a multi-query model benchmark. A frozen untuned local-model benchmark is the next evaluation milestone.

---

# Provider trust boundary

The generation model is not trusted to construct final citation metadata.

```text
model claim
    ↓
evidence ID
    ↓
application-side evidence lookup
    ↓
authoritative citation
```

Unknown evidence IDs are rejected.

Final citation metadata can include:

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

---

# Evaluation

Retrieval and generation evaluation are treated separately.

Implemented evaluation includes:

- retrieval benchmark v0.1
- pooled retrieval benchmark v0.2
- NumPy-vs-pgvector comparison
- generation v0.3 development benchmark
- deterministic-provider evaluation
- OpenAI-provider evaluation
- protected held-out deterministic evaluation
- answerability metrics
- refusal metrics
- citation metrics
- structural-validity checks
- latency metrics
- token metrics
- cost metrics
- CI-enforced frozen regression policy

The local Transformers provider has completed smoke validation. Its frozen benchmark has not yet been established.

## Generation v0.3 development benchmark

| Category | Queries |
|---|---:|
| Expected-answerable | 20 |
| Unsupported | 12 |
| Total | 32 |

Final evaluated configuration:

```text
Sufficiency v0.2.1
+ Facet Retrieval v0.1
+ OpenAI Responses API
```

| Metric | Final |
|---|---:|
| Answerability accuracy | 1.0000 |
| Answerable completion | 1.0000 |
| Unsupported refusal | 1.0000 |
| Claim citation coverage | 1.0000 |
| Citation-reference validity | 1.0000 |
| Expected-term recall | 0.9310 |
| Structural validity | 1.0000 |
| Provider call-policy accuracy | 1.0000 |

Provider telemetry:

| Metric | Value |
|---|---:|
| Provider calls | 20 |
| Provider bypasses | 12 |
| Total tokens | 58,915 |
| Estimated benchmark cost | $0.103745 |
| P50 provider latency | 5.6394 s |
| P95 provider latency | 7.6947 s |
| Retry rate | 0.0 |

These figures describe the development benchmark only and are not evidence of universal RAG correctness.

## Held-out deterministic evaluation v0.4

| Category | Queries |
|---|---:|
| Expected-answerable | 6 |
| Unsupported | 6 |
| Total | 12 |

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

The held-out result is recorded as evidence and is not used as a tuning target.

---

# FastAPI service

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `GET` | `/ready` | Runtime readiness |
| `POST` | `/v1/query` | Grounded answer |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Swagger/OpenAPI documentation |
| `GET` | `/redoc` | ReDoc documentation |
| `GET` | `/openapi.json` | OpenAPI schema |

Core environment variables:

```text
AERORAGX_RUNTIME_MODE
AERORAGX_DENSE_BACKEND
AERORAGX_CANDIDATE_TOP_K
AERORAGX_EVIDENCE_TOP_K
```

pgvector additionally uses:

```text
AERORAGX_VECTOR_DATABASE_URL
```

## Run deterministic API

```bash
export AERORAGX_RUNTIME_MODE=local
export AERORAGX_DENSE_BACKEND=numpy

python -m uvicorn aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000
```

## Run local Transformers API

```bash
python -m pip install -e ".[dev,llm]"

export AERORAGX_RUNTIME_MODE=transformers
export AERORAGX_DENSE_BACKEND=numpy

python -m uvicorn aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000
```

The first run may download public Hugging Face model weights.

Example query:

```bash
curl -sS \
  -X POST \
  http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How can battery thermal runaway propagate in electric aircraft?"
  }'
```

---

# Installation

AeroRAG-X requires Python 3.12 or newer.

```bash
git clone https://github.com/triasha72/AeroRAG-X.git
cd AeroRAG-X

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Core development:

```bash
python -m pip install -e ".[dev]"
```

With pgvector:

```bash
python -m pip install -e ".[dev,vector]"
```

With local LLM support:

```bash
python -m pip install -e ".[dev,llm]"
```

Complete development environment:

```bash
python -m pip install -e ".[dev,vector,llm]"
```

Conda example:

```bash
conda create -n aeroragx-py312 python=3.12
conda activate aeroragx-py312
python -m pip install --upgrade pip
python -m pip install -e ".[dev,vector,llm]"
```

---

# CI and validation

GitHub Actions validates:

- Python 3.12
- development dependencies
- pgvector dependencies
- local-LLM dependencies
- Ruff formatting
- Ruff linting
- pytest and coverage
- strict mypy
- vector utility scripts
- frozen generation-regression policy
- PostgreSQL + pgvector integration
- Docker build

The real Qwen smoke test remains opt-in.

Run the local quality gate:

```bash
unset AERORAGX_VECTOR_DATABASE_URL

ruff format .
ruff check .

mypy src/aeroragx
mypy scripts/load_pgvector.py
mypy scripts/benchmark_vector_backends.py
mypy scripts/smoke_transformers.py

pytest

git diff --check
```

Real-model validation:

```bash
python scripts/smoke_transformers.py
```

---

# Docker and cloud status

AeroRAG-X has a non-root Docker serving path and a private Google Cloud Run Gen2 validation path.

The existing deployed Cloud Run validation uses the artifact-backed baseline runtime. Local Transformers has been validated on Apple MPS, but no production local-LLM GPU deployment benchmark is claimed yet.

---

# Security and limitations

AeroRAG-X currently:

- treats retrieved evidence as untrusted model input
- validates structured provider output
- rejects unknown evidence IDs
- resolves final citations application-side
- redacts provider secrets from transport errors
- can reject unsupported questions before model invocation
- uses environment variables for secrets
- runs Docker as a non-root user
- keeps deployed Cloud Run access private
- preserves source-document checksums
- validates pgvector corpus counts against versioned artifacts

Current limitations include:

- no local-model fine-tuning yet
- no PEFT / LoRA adapter yet
- no frozen local-Transformers benchmark yet
- no constrained-decoding JSON grammar
- no semantic entailment verifier
- no general-purpose autonomous agent
- no multimodal figure retrieval
- no structured table retrieval
- no managed production PostgreSQL deployment
- no large-scale ANN benchmark
- no production local-LLM GPU deployment benchmark
- no claim of Qualcomm-hardware optimization

---

# Development direction

```text
local Transformers provider                DONE
        ↓
protected untuned local-model benchmark    NEXT
        ↓
failure analysis
        ↓
PEFT / LoRA domain adaptation
        ↓
base vs RAG vs LoRA vs LoRA + RAG
        ↓
reduced-precision inference benchmark
        ↓
bounded tool-using research agent
        ↓
agent evaluation
```

The project uses measured behavior rather than architectural complexity as the criterion for adopting new capabilities.

See `ROADMAP.md` for the detailed sequence.

---

# License

MIT
