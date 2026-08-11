# AeroRAG-X

**An evaluation-first, evidence-grounded RAG system for aerospace technical knowledge.**

AeroRAG-X is an independent engineering project exploring a question I kept running into while working with technical aerospace literature:

> How can a language model help retrieve and synthesize engineering knowledge without losing the evidence trail that makes the answer trustworthy?

The project is built around public NASA Technical Reports Server (NTRS) material and treats retrieval, grounding, generation, citations, evaluation, and deployment as separate engineering problems rather than hiding them behind a chatbot interface.

AeroRAG-X currently combines:

- citation-preserving NASA document processing;
- BM25 and dense retrieval;
- hybrid Reciprocal Rank Fusion;
- cross-encoder reranking;
- evidence-sufficiency gating;
- grounded structured generation;
- application-controlled citations;
- local and remote language-model backends;
- PEFT / LoRA adaptation of a local Qwen model;
- PostgreSQL + pgvector;
- FastAPI serving;
- Docker and private Cloud Run validation;
- Prometheus and OpenTelemetry;
- frozen evaluation benchmarks and failure analysis.

---

## Where the idea came from

AeroRAG-X grew out of my interest in two related problems:

1. technical knowledge in aerospace is distributed across large collections of reports, papers, presentations, and historical documents;
2. a useful engineering assistant needs to show not only an answer, but also **why that answer can be trusted**.

One project that influenced how I started thinking about the systems side of the problem was **HeRo — Adaptive Orchestration of Agentic RAG on Heterogeneous Mobile SoC**:

https://arxiv.org/abs/2603.01661

What interested me most was not reproducing HeRo's hardware environment. It was the broader idea that RAG should be treated as an **end-to-end system** whose retrieval stages, model calls, routing decisions, latency, resource usage, and failure modes can be measured independently.

AeroRAG-X explores that systems mindset in a different setting: aerospace technical knowledge.

The emphasis here is therefore on:

- evidence provenance;
- retrieval quality;
- grounded refusal;
- citation integrity;
- local-model behavior;
- model adaptation;
- reproducible experiments;
- failure diagnosis;
- backend trade-offs;
- bounded orchestration.

The project has intentionally evolved through measured experiments rather than by adding components only because they are common in modern AI stacks.

---

# System architecture

```mermaid
flowchart TD
    A["NASA NTRS metadata + technical reports"] --> B["Versioned citation-preserving corpus"]

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
    L --> O["Qwen3-0.6B"]
    L --> P["Qwen3-0.6B + PEFT / LoRA"]

    M --> Q["Structured grounded response"]
    N --> Q
    O --> Q
    P --> Q

    Q --> R["Structured-response validation"]
    R --> S["Evidence-ID normalization + validation"]
    S --> T["Application-side citation resolution"]

    T --> U["Shared RAG runtime"]

    U --> V["Typer CLI"]
    U --> W["FastAPI"]

    W --> X["Prometheus + OpenTelemetry"]
    W --> Y["Docker / Cloud Run"]

    U --> Z["Frozen evaluation framework"]
```

---

# Current capabilities

## Corpus and provenance

- NASA NTRS corpus
- **3,233 citation-preserving chunks**
- document IDs
- page IDs
- page ranges
- NASA citation URLs
- original source URLs
- source-document checksums
- versioned processing artifacts
- reproducible manifests

## Retrieval

- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- exact NumPy cosine search
- PostgreSQL + pgvector backend
- runtime-selectable dense backend
- Reciprocal Rank Fusion
- cross-encoder reranking
- facet-aware retrieval for selected synthesis questions

Current embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Embedding dimension:

```text
384
```

Current reranker:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

## Grounding

- evidence-sufficiency gate
- unsupported-query rejection before model inference
- bounded evidence context
- structured response schema
- evidence-ID validation
- duplicate evidence-ID normalization
- unknown evidence-ID rejection
- authoritative application-side citation resolution
- source-document provenance

## Generation

Supported generation modes:

```text
local
openai
transformers
```

Local neural model:

```text
Qwen/Qwen3-0.6B
```

The local model can run as:

```text
Base Qwen
```

or:

```text
Base Qwen + PEFT / LoRA adapter
```

## Serving and operations

- FastAPI
- Docker
- private Google Cloud Run Gen2 validation
- request IDs
- structured errors
- structured JSON logs
- Prometheus
- OpenTelemetry
- provider latency telemetry
- provider token telemetry
- provider-call / bypass telemetry
- GitHub Actions CI

---

# Design principles

AeroRAG-X is organized around a few recurring questions:

1. Can the source corpus be reproduced?
2. Can every answer be traced back to authoritative evidence?
3. Can retrieval components be evaluated independently?
4. Can unsupported questions be rejected before model inference?
5. Can local and remote models use the same grounded interface?
6. Can model-generated evidence references be validated before becoming citations?
7. Can failures be recorded instead of silently converted into apparently valid answers?
8. Can new capabilities be compared with frozen baselines?
9. Can local-model adaptation be evaluated separately from retrieval improvements?
10. Can orchestration remain bounded and observable as the system becomes more agentic?

The project therefore emphasizes:

```text
provenance
reproducibility
measurement
failure analysis
bounded behavior
grounded refusal
citation integrity
backend interchangeability
protected evaluation
```

---

# Retrieval pipeline

## BM25

The lexical retriever includes:

- deterministic tokenization;
- configurable BM25 parameters;
- deterministic tie-breaking;
- full chunk provenance.

## Dense retrieval

Dense retrieval supports:

```text
NumPy exact cosine
PostgreSQL + pgvector
```

The current corpus is small enough that exact NumPy retrieval remains a strong default.

## Hybrid retrieval

BM25 and dense results are combined using Reciprocal Rank Fusion.

The fused result retains:

- lexical rank;
- dense rank;
- fused rank;
- source scores;
- chunk provenance.

## Cross-encoder reranking

A bounded candidate set is reranked with:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Reranker latency is recorded independently.

---

# NumPy vs pgvector

The same stored embeddings were evaluated through both dense backends.

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

| Backend | Mean |
|---|---:|
| NumPy | 7.121 ms |
| pgvector | 20.517 ms |

At the current corpus size, NumPy remains the simpler low-latency backend.

pgvector is retained because it becomes useful when the corpus needs:

- persistence;
- transactional updates;
- metadata filtering;
- mutable indexing;
- database-backed retrieval.

---

# Evidence-sufficiency gate

Before generation, AeroRAG-X asks whether the retrieved evidence is sufficient to support an answer.

Current configuration:

```text
configs/sufficiency_v0_2_1.yaml
```

The gate considers:

- evidence count;
- informative query-term coverage;
- supported terms;
- numeric evidence;
- named anchors;
- claim qualifiers;
- exact-value questions.

When evidence is insufficient:

```text
question
   ↓
retrieval
   ↓
sufficiency = false
   ↓
grounded refusal
```

The generation model is not called.

This is both a grounding control and an inference-cost control.

---

# Provider trust boundary

AeroRAG-X does not trust a language model to construct final citation metadata.

The model returns evidence references:

```text
model claim
    ↓
evidence ID
```

The application then performs:

```text
evidence-ID normalization
        ↓
known-ID validation
        ↓
authoritative evidence lookup
        ↓
application-generated citation
```

Exact repeated evidence references are deduplicated while preserving order.

Unknown evidence IDs are still rejected.

A final citation can include:

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

# Local Qwen generation

The local generation backend uses:

```text
Qwen/Qwen3-0.6B
```

through Hugging Face Transformers.

The runtime supports:

- `AutoTokenizer`
- `AutoModelForCausalLM`
- model-specific chat templates
- CPU / Apple MPS / CUDA device selection
- configurable dtype
- deterministic decoding
- bounded generation
- strict JSON parsing
- structured-response validation
- token telemetry
- provider latency telemetry

The local generation path uses the same RAG and grounding infrastructure as the other providers.

---

# PEFT / LoRA adaptation

AeroRAG-X includes a reproducible PEFT / LoRA adaptation pipeline for the local Qwen model.

The purpose of the adaptation experiment was not to replace retrieval.

The question was:

> Can a small local model produce richer, more structured aerospace answers while preserving the grounding and refusal behavior of the RAG system?

The training workflow includes:

- independent training examples;
- protected evaluation separation;
- assistant-only loss masking;
- deterministic train/dev splits;
- context-window eligibility checks;
- gradient checkpointing;
- Apple MPS training support;
- tiny-overfit learnability validation;
- best-checkpoint selection;
- adapter save/reload verification;
- experiment provenance.

Training configuration:

```text
Base model: Qwen/Qwen3-0.6B
Training examples: 106
Development examples: 12
Epochs: 3

LoRA rank: 16
LoRA alpha: 32
LoRA dropout: 0.05

Target modules:
q_proj
k_proj
v_proj
o_proj
```

The best checkpoint was selected from development loss rather than simply taking the final training epoch.

Adapter weights remain local and are not committed to the repository.

---

# Why failure analysis is part of the project

The first LoRA evaluation was not treated as a successful experiment simply because training loss decreased.

It exposed several structured-generation failures:

```text
truncated JSON
supported response with missing claims
duplicate evidence references
```

Those failures were preserved as experiment artifacts and investigated individually.

The resulting robustness work introduced:

- a larger but still bounded generation budget;
- explicit complete-JSON instructions;
- concise structured-output guidance;
- supported-answer claim requirements;
- unique evidence-ID guidance;
- deterministic duplicate evidence-ID normalization;
- strict continued rejection of unknown evidence IDs.

This progression is intentionally part of the repository history.

AeroRAG-X treats negative results as engineering evidence rather than something to remove from the project record.

---

# Final Base+RAG vs LoRA+RAG evaluation

The final controlled benchmark uses:

```text
32 frozen queries
20 expected-answerable
12 deliberately unsupported
```

Both configurations use the same:

- corpus;
- retrieval pipeline;
- dense backend;
- RRF configuration;
- reranker;
- candidate depth;
- evidence depth;
- evidence-sufficiency gate;
- prompt policy;
- generation budget;
- deterministic decoding configuration.

The primary model-side difference is whether the trained LoRA adapter is active.

## Final v0.3 results

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Completed queries | 32 / 32 | 32 / 32 |
| Generation failures | 0 | 0 |
| Answerability accuracy | 1.0000 | 1.0000 |
| Answerable completion | 1.0000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation-reference validity | 1.0000 | 1.0000 |
| Source-document coverage | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 |
| Formal claims | 32 | 53 |
| Claims / answerable query | 1.600 | 2.650 |
| Citation references | 40 | 96 |
| Provider calls | 20 | 20 |
| Provider bypasses | 12 | 12 |
| External API cost | $0 | $0 |

## Runtime trade-off

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Input tokens | 51,289 | 51,289 |
| Output tokens | 3,314 | 5,182 |
| Total tokens | 54,603 | 56,471 |
| P50 provider latency | 8.88 s | 14.87 s |
| P95 provider latency | 16.08 s | 19.13 s |

The adapted model therefore produced substantially more output while preserving the benchmark's measured reliability and exact expected-term recall.

Longer output is not automatically treated as higher quality. More detailed claim-decomposition and semantic coverage remain separate evaluation questions.

---

# Evaluation philosophy

AeroRAG-X keeps retrieval and generation evaluation separate.

Implemented evaluation includes:

- BM25 retrieval evaluation;
- dense retrieval evaluation;
- Hybrid RRF evaluation;
- reranker evaluation;
- NumPy-vs-pgvector equivalence;
- deterministic-generation benchmarks;
- OpenAI-generation benchmarks;
- local-model benchmarks;
- unsupported controls;
- answerability accuracy;
- refusal accuracy;
- citation coverage;
- citation-reference validity;
- source-document coverage;
- expected-term recall;
- structured-response validity;
- generation failure categories;
- latency telemetry;
- token telemetry;
- provider-call telemetry.

Exact expected-term recall is intentionally treated as a diagnostic rather than a complete semantic metric.

For example:

```text
detect
detection
detected
```

may describe the same concept while scoring differently under exact lexical matching.

Future evaluation therefore includes semantic concept matching and claim-evidence faithfulness.

---

# FastAPI

Available endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | process health |
| `GET` | `/ready` | runtime readiness |
| `POST` | `/v1/query` | grounded query |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI schema |

Run the deterministic API:

```bash
export AERORAGX_RUNTIME_MODE=local
export AERORAGX_DENSE_BACKEND=numpy

python -m uvicorn aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000
```

Run local Transformers:

```bash
export AERORAGX_RUNTIME_MODE=transformers
export AERORAGX_DENSE_BACKEND=numpy

python -m uvicorn aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000
```

Example:

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

# PostgreSQL + pgvector

Install:

```bash
python -m pip install -e ".[dev,vector]"
```

Start PostgreSQL:

```bash
docker compose \
  -f docker-compose.vector.yml \
  up -d
```

Configure:

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"
```

Load the current index:

```bash
python scripts/load_pgvector.py
```

Select the backend:

```bash
export AERORAGX_DENSE_BACKEND=pgvector
```

---

# Installation

Requires Python 3.12+.

```bash
git clone https://github.com/triasha72/AeroRAG-X.git

cd AeroRAG-X

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
```

Development:

```bash
python -m pip install -e ".[dev]"
```

Local LLM:

```bash
python -m pip install -e ".[dev,llm]"
```

pgvector:

```bash
python -m pip install -e ".[dev,vector]"
```

Complete development environment:

```bash
python -m pip install -e ".[dev,vector,llm,training]"
```

---

# Validation

Run:

```bash
ruff format --check .
ruff check .
mypy src/aeroragx
pytest -q
```

Real-model tests remain opt-in because model weights and local inference are substantially more expensive than normal unit tests.

---

# Deployment

AeroRAG-X has been validated through:

```text
local Python runtime
        ↓
FastAPI
        ↓
Docker
        ↓
private Google Cloud Run Gen2
```

The deployed cloud validation path is private.

No production-scale local-LLM GPU deployment benchmark is currently claimed.

---

# Current research direction

The LoRA+RAG experiment is no longer the endpoint of the project.

The next questions are:

### 1. What came from retrieval, and what came from adaptation?

Run a controlled four-way comparison:

```text
Base
LoRA
Base + RAG
LoRA + RAG
```

### 2. Can evidence recovery become adaptive without becoming unbounded?

Inspired in part by the systems thinking behind HeRo, the next orchestration experiment will evaluate a **bounded evidence-recovery workflow**:

```text
question
   ↓
retrieve
   ↓
assess evidence
   ↓
sufficient ─────────→ answer
   │
   └─ insufficient
          ↓
      rewrite query
          ↓
      retrieve once more
          ↓
      assess
          ↓
      answer or grounded refusal
```

The important constraint is:

```text
maximum retrieval attempts = 2
```

The objective is not to build a generic autonomous agent.

The objective is to measure whether limited adaptive retrieval can improve difficult-query recovery without sacrificing:

- grounding;
- citation validity;
- termination guarantees;
- latency transparency;
- reproducibility.

### 3. Can evaluation move beyond lexical proxies?

Planned work includes:

- semantic expected-concept matching;
- claim-evidence entailment;
- answer-to-claim completeness;
- human assessment;
- larger protected benchmarks.

---

# What AeroRAG-X is not

AeroRAG-X is not intended to be:

- a generic chatbot;
- a collection of AI frameworks added for breadth;
- an autonomous agent with unbounded tool access;
- a benchmark claiming universal aerospace correctness;
- a hardware-optimization project;
- a replacement for engineering judgment.

It is a project about building and measuring **trustworthy technical knowledge systems**.

---

# Status

```text
NASA corpus                              DONE
citation-preserving processing           DONE
BM25                                     DONE
dense retrieval                          DONE
Hybrid RRF                               DONE
cross-encoder reranking                  DONE
evidence sufficiency                     DONE
grounded generation                      DONE
OpenAI provider                          DONE
local Qwen provider                      DONE
FastAPI                                  DONE
Docker                                   DONE
observability                            DONE
private Cloud Run validation             DONE
pgvector                                 DONE
PEFT / LoRA training                     DONE
LoRA failure analysis                    DONE
structured-generation hardening          DONE
Base+RAG vs LoRA+RAG evaluation          DONE

four-way model study                     NEXT
bounded adaptive retrieval               PLANNED
agent evaluation                         PLANNED
semantic evaluation                      PLANNED
multimodal technical-report retrieval    FUTURE
```

See [`ROADMAP.md`](ROADMAP.md) for the experiment sequence.

---

# License

MIT