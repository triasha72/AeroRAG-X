# AeroRAG-X

**An evaluation-first, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.**

AeroRAG-X is an independent engineering project exploring how language models can retrieve and synthesize aerospace technical information without losing the evidence trail needed to evaluate the answer.

The system is built around public NASA Technical Reports Server (NTRS) material and treats corpus construction, retrieval, reranking, grounding, generation, citations, evaluation, and deployment as separately measurable engineering problems.

---

## Project origin

The idea for AeroRAG-X grew out of questions I became interested in while working on **HERO**, a Georgia Tech Grand Challenge project sponsored by **Delta Air Lines**.

That experience motivated me to think more deeply about how large collections of aerospace technical information could be searched and synthesized while retaining clear traceability between an answer and the evidence supporting it.

AeroRAG-X developed from that interest as an independent project.

It is not a HERO or Delta Air Lines deliverable. Instead, it explores a related technical question independently:

> **Can a language-model system help navigate aerospace technical literature while making provenance, evidence sufficiency, citations, model behavior, and failure modes measurable?**

That question has driven the project more than any particular software stack.

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

    L --> M["Deterministic provider"]
    L --> N["OpenAI"]
    L --> O["Qwen3-0.6B"]
    L --> P["Qwen3-0.6B + PEFT / LoRA"]

    M --> Q["Structured response"]
    N --> Q
    O --> Q
    P --> Q

    Q --> R["Response validation"]
    R --> S["Evidence-ID validation"]
    S --> T["Application-side citation resolution"]

    T --> U["Shared RAG runtime"]

    U --> V["CLI"]
    U --> W["FastAPI"]
    U --> X["Evaluation"]

    W --> Y["Prometheus + OpenTelemetry"]
    W --> Z["Docker / private Cloud Run"]
```

---

# What the project currently includes

## Corpus and provenance

- public NASA NTRS technical material
- **3,233 citation-preserving chunks**
- document identifiers
- page identifiers
- page ranges
- source URLs
- NASA citation URLs
- source-document checksums
- reproducible manifests
- versioned processing artifacts

## Retrieval

- BM25
- Sentence Transformer embeddings
- exact NumPy cosine retrieval
- PostgreSQL + pgvector
- runtime-selectable dense backends
- Reciprocal Rank Fusion
- cross-encoder reranking
- deterministic facet-aware evidence retrieval

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

- evidence-sufficiency gating
- unsupported-query rejection before generation
- bounded evidence context
- structured response validation
- evidence-ID validation
- exact duplicate evidence-reference normalization
- unknown evidence-ID rejection
- application-side citation resolution
- source-document provenance

## Generation

Supported modes:

```text
local
openai
transformers
```

Current local model:

```text
Qwen/Qwen3-0.6B
```

Local generation can run as:

```text
Base Qwen
```

or:

```text
Qwen + PEFT / LoRA adapter
```

## Serving and operations

- FastAPI
- Docker
- private Google Cloud Run Gen2 validation
- structured logging
- request IDs
- Prometheus metrics
- OpenTelemetry tracing
- provider latency telemetry
- provider token telemetry
- provider call/bypass telemetry
- GitHub Actions CI

---

# Engineering principles

AeroRAG-X is organized around measurable questions.

1. Can the source corpus be reproduced?
2. Can every retrieved chunk preserve authoritative provenance?
3. Can lexical, dense, hybrid, and reranked retrieval be evaluated independently?
4. Can unsupported questions be rejected before model inference?
5. Can different language models use the same grounded interface?
6. Can citations remain application-controlled instead of model-generated?
7. Can invalid model outputs be detected rather than silently accepted?
8. Can negative experiments be preserved and diagnosed?
9. Can model adaptation be separated experimentally from retrieval improvements?
10. Can future adaptive workflows remain bounded and observable?

The project emphasizes:

```text
provenance
reproducibility
grounded refusal
citation integrity
failure analysis
protected evaluation
backend interchangeability
bounded behavior
measured trade-offs
```

---

# Retrieval

## BM25

The lexical baseline provides:

- deterministic tokenization
- configurable BM25 parameters
- deterministic tie-breaking
- provenance preservation

## Dense retrieval

The dense index uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

and stores 384-dimensional embeddings.

Available backends:

```text
NumPy exact cosine
PostgreSQL + pgvector
```

## Hybrid retrieval

BM25 and dense rankings are combined using Reciprocal Rank Fusion.

The system retains:

- lexical rank
- dense rank
- fused rank
- scores
- complete chunk provenance

## Cross-encoder reranking

Current reranker:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

A bounded Hybrid-RRF candidate set is reranked before evidence selection.

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

## Local retrieval latency

| Backend | Mean |
|---|---:|
| NumPy | 7.121 ms |
| pgvector | 20.517 ms |

At the current corpus size, exact NumPy retrieval remains the simpler and faster default.

pgvector is retained for future requirements involving:

- persistence
- transactional updates
- metadata filtering
- mutable indexes
- database-backed retrieval

---

# Evidence sufficiency

Before generation, AeroRAG-X evaluates whether retrieved evidence is sufficient to answer the question.

Current configuration:

```text
configs/sufficiency_v0_2_1.yaml
```

The gate considers:

- minimum evidence count
- informative query-term coverage
- supported terms
- numeric support
- named anchors
- claim qualifiers
- exact-value questions

When evidence is insufficient:

```text
question
    ↓
retrieval
    ↓
evidence assessment
    ↓
insufficient
    ↓
grounded refusal
```

The language model is not called.

The gate is therefore both:

```text
a grounding control
+
an inference-cost control
```

---

# Citation trust boundary

The model does not construct authoritative citation metadata.

The model produces claims linked to evidence IDs:

```text
claim
  ↓
evidence ID
```

The application then performs:

```text
duplicate-ID normalization
        ↓
known-ID validation
        ↓
evidence lookup
        ↓
authoritative citation construction
```

Exact duplicate references are normalized.

Unknown evidence IDs remain invalid.

Citation metadata can include:

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

# Local language-model generation

Current local model:

```text
Qwen/Qwen3-0.6B
```

The Hugging Face runtime supports:

- `AutoTokenizer`
- `AutoModelForCausalLM`
- model chat templates
- Apple MPS
- CUDA
- CPU fallback
- configurable dtype
- deterministic decoding
- bounded output
- strict JSON parsing
- structured-response validation
- token telemetry
- latency telemetry

The local model uses the same retrieval and grounding infrastructure as the other generation providers.

---

# PEFT / LoRA adaptation

AeroRAG-X includes a reproducible PEFT / LoRA adaptation pipeline for the local Qwen model.

The experiment asks:

> **Can a small local model produce more granular technical responses while preserving the reliability and grounding behavior already supplied by the RAG system?**

LoRA is not used as a replacement for retrieval.

## Training configuration

```text
Base model: Qwen/Qwen3-0.6B

Training examples: 106
Development examples: 12

Epochs: 3

LoRA rank: 16
LoRA alpha: 32
LoRA dropout: 0.05

Targets:
q_proj
k_proj
v_proj
o_proj
```

The training workflow includes:

- independent training-data construction
- protected benchmark separation
- overlap auditing
- context-window eligibility checking
- assistant-only loss masking
- deterministic splits
- gradient checkpointing
- Apple MPS support
- tiny-overfit learnability validation
- development-loss checkpoint selection
- adapter save/reload verification
- dataset and environment provenance

The best checkpoint was selected at **Epoch 2** based on development loss.

The adapter weights remain local and are not committed to the repository.

---

# Why negative results are preserved

The first full LoRA evaluation did not pass all reliability requirements.

Observed failure modes included:

```text
truncated JSON
supported response without formal claims
duplicate evidence references
```

Instead of discarding that run, the project preserved it and reproduced each failure.

The investigation led to:

- a larger but still bounded output budget
- explicit complete-JSON instructions
- more concise structured-output guidance
- explicit claim requirements for supported answers
- evidence-reference uniqueness guidance
- deterministic duplicate-reference normalization
- regression testing of unknown-ID rejection

This distinction is important:

```text
successful training
!=
reliable deployed behavior
```

The project evaluates both.

---

# Final Base+RAG vs LoRA+RAG benchmark

The final controlled benchmark contains:

```text
32 queries
20 expected-answerable
12 unsupported controls
```

Both conditions use the same:

- corpus
- BM25 index
- dense index
- Hybrid RRF
- reranker
- candidate depth
- evidence depth
- sufficiency policy
- prompt configuration
- generation budget
- deterministic decoding

The model-side intervention is the presence or absence of the LoRA adapter.

## Quality and reliability

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

## Response decomposition

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Formal claims | 32 | 53 |
| Claims / answerable query | 1.600 | 2.650 |
| Citation references | 40 | 96 |

The adapter increased formal-claim count by:

```text
65.625%
```

while aggregate expected-term recall and the measured reliability metrics remained unchanged.

Across the 20 answerable questions:

```text
16 showed more formal claims with LoRA
2 showed fewer formal claims
2 were unchanged
```

This supports a narrower conclusion than simply saying that LoRA made the model "better":

> **LoRA substantially increased structured technical decomposition on this benchmark while preserving the measured system-level reliability properties.**

---

# Query-level limitations

Aggregate metrics do not tell the entire story.

For example:

```text
para_005
expected-term recall:
0.667 → 1.000
```

while:

```text
para_009
expected-term recall:
0.667 → 0.333
```

Therefore increased response decomposition does not guarantee improved content coverage on every query.

The exact expected-term metric is also lexical rather than semantic.

For example:

```text
detect
detected
detection
```

may express the same concept while producing different exact-term scores.

This motivates the next semantic-evaluation phase.

---

# Runtime trade-off

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Input tokens | 51,289 | 51,289 |
| Output tokens | 3,314 | 5,182 |
| Total tokens | 54,603 | 56,471 |
| P50 provider latency | 8.88 s | 14.87 s |
| P95 provider latency | 16.08 s | 19.13 s |
| External API cost | $0 | $0 |

The LoRA model produces more structured output but also requires more generation time.

The project records that trade-off rather than treating longer output as automatically superior.

---

# Evaluation philosophy

Retrieval and generation are evaluated separately.

Current evaluation includes:

- BM25 retrieval benchmarks
- dense retrieval benchmarks
- Hybrid RRF comparison
- reranker comparison
- NumPy vs pgvector equivalence
- answerability
- unsupported controls
- grounded refusal
- citation coverage
- citation-reference validity
- source-document coverage
- expected-term recall
- structural validity
- generation-failure categories
- provider-call policy
- latency
- token usage
- external API cost

Planned semantic evaluation includes:

- semantic expected-concept matching
- claim-evidence entailment
- answer-to-claim completeness
- answer relevance
- redundancy measurement
- human review

---

# FastAPI

Endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | process health |
| `GET` | `/ready` | runtime readiness |
| `POST` | `/v1/query` | grounded query |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | OpenAPI documentation |
| `GET` | `/openapi.json` | OpenAPI schema |

Run deterministic mode:

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

Start the database:

```bash
docker compose \
  -f docker-compose.vector.yml \
  up -d
```

Configure:

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"
```

Load the existing embeddings:

```bash
python scripts/load_pgvector.py
```

Select pgvector:

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

Core development:

```bash
python -m pip install -e ".[dev]"
```

Local language-model support:

```bash
python -m pip install -e ".[dev,llm]"
```

Vector support:

```bash
python -m pip install -e ".[dev,vector]"
```

Training support:

```bash
python -m pip install -e ".[dev,llm,training]"
```

Complete local development environment:

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

Real-model evaluations remain opt-in because they require local model weights and substantially more compute than unit tests.

---

# Deployment status

Validated path:

```text
local runtime
     ↓
FastAPI
     ↓
Docker
     ↓
private Google Cloud Run Gen2
```

The cloud validation path is private.

The project does not currently claim production-scale local-LLM GPU deployment performance.

---

# Current research direction

The completed LoRA experiment leads to three new questions.

## 1. Retrieval versus adaptation

The next experiment is a four-way study:

```text
Base
LoRA
Base + RAG
LoRA + RAG
```

This separates:

```text
model knowledge
adaptation
retrieval
adaptation + retrieval
```

The Base+RAG and LoRA+RAG conditions are already frozen.

The next step is to evaluate closed-book Base and LoRA using the same question set.

---

## 2. Bounded adaptive retrieval

After the four-way study, AeroRAG-X will test whether limited retrieval adaptation helps difficult questions.

Proposed workflow:

```text
question
   ↓
retrieve
   ↓
assess evidence
   ↓
sufficient? ───── yes ───→ generate
   │
   no
   ↓
rewrite query
   ↓
retrieve once more
   ↓
assess again
   ↓
generate or grounded refusal
```

Hard limit:

```text
maximum retrieval passes = 2
```

The objective is not a generic autonomous agent.

The objective is to measure whether bounded adaptive retrieval improves difficult-query recovery without sacrificing:

- termination guarantees
- grounding
- citation validity
- observability
- reproducibility

---

## 3. Semantic evaluation

The current benchmark deliberately uses deterministic metrics.

The next evaluation layer should determine whether:

```text
more claims
```

actually correspond to:

```text
better supported technical coverage
```

Planned metrics include:

- semantic expected-concept recall
- claim-evidence entailment
- claim redundancy
- answer-to-claim completeness
- human assessment

---

# Current status

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
semantic evaluation                      PLANNED
efficient local inference                PLANNED
multimodal technical-report retrieval    FUTURE
```

---

# What AeroRAG-X is not

AeroRAG-X is not intended to be:

- a generic chatbot
- an unrestricted autonomous agent
- a collection of frameworks added for stack breadth
- a benchmark claiming universal aerospace correctness
- a replacement for engineering judgment
- a hardware-specific optimization project without hardware-specific evidence

It is an experiment in building and measuring **evidence-grounded technical knowledge systems**.

---

# License

MIT
