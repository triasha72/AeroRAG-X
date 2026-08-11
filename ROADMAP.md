# AeroRAG-X Roadmap

AeroRAG-X is an independent, evaluation-first project exploring evidence-grounded language-model systems for aerospace technical knowledge.

The governing principle is:

> **Add capability only when its behavior can be measured against an existing baseline.**

The project did not begin with a target stack.

It began with a question:

> Can an AI system help navigate aerospace technical literature while keeping retrieval provenance, evidence sufficiency, citations, and failure behavior visible?

As the project evolved, work such as **HeRo — Adaptive Orchestration of Agentic RAG on Heterogeneous Mobile SoC** influenced how I thought about RAG as a systems problem rather than only a retrieval-plus-prompting problem:

https://arxiv.org/abs/2603.01661

The useful idea for AeroRAG-X is the broader systems perspective: retrieval, routing, generation, latency, resource use, and failure handling should be measurable components.

AeroRAG-X applies that mindset to a different domain and set of questions: aerospace technical knowledge, provenance, grounded synthesis, model adaptation, and bounded orchestration.

---

# Development sequence

```text
NASA technical corpus
        ↓
citation-preserving processing
        ↓
BM25
        ↓
dense retrieval
        ↓
retrieval evaluation
        ↓
Hybrid RRF
        ↓
cross-encoder reranking
        ↓
grounded generation
        ↓
evidence-sufficiency gating
        ↓
generation evaluation
        ↓
FastAPI
        ↓
Docker
        ↓
observability
        ↓
private Cloud Run validation
        ↓
pgvector backend
        ↓
local Qwen generation
        ↓
protected local-model baseline
        ↓
PEFT / LoRA adaptation
        ↓
failure analysis
        ↓
structured-generation hardening
        ↓
final Base+RAG vs LoRA+RAG benchmark
        ↓
four-way Base / LoRA / RAG study
        ↓
bounded adaptive retrieval
        ↓
agent evaluation
        ↓
semantic evaluation
        ↓
multimodal technical reports
```

---

# Current status

## Completed

- [x] reproducible NASA NTRS corpus
- [x] 3,233 citation-preserving chunks
- [x] BM25 retrieval
- [x] Sentence Transformer embeddings
- [x] exact NumPy dense retrieval
- [x] PostgreSQL + pgvector
- [x] Hybrid Reciprocal Rank Fusion
- [x] cross-encoder reranking
- [x] facet-aware evidence retrieval
- [x] evidence-sufficiency gating
- [x] deterministic grounded generation
- [x] OpenAI structured generation
- [x] local Hugging Face generation
- [x] application-side citation resolution
- [x] FastAPI
- [x] Docker
- [x] Prometheus
- [x] OpenTelemetry
- [x] private Cloud Run validation
- [x] protected evaluation split
- [x] failure-tolerant generation evaluation
- [x] frozen local Qwen baseline
- [x] PEFT / LoRA training pipeline
- [x] leakage-aware LoRA train/dev preparation
- [x] assistant-only loss masking
- [x] MPS-compatible training
- [x] tiny-overfit learnability gate
- [x] best-checkpoint selection
- [x] real PEFT adapter loading
- [x] Base+RAG vs LoRA+RAG evaluation
- [x] structured-generation failure analysis
- [x] bounded output-budget hardening
- [x] prompt-contract hardening
- [x] duplicate evidence-ID normalization
- [x] strict unknown evidence-ID validation
- [x] final 32-query zero-failure Base+RAG benchmark
- [x] final 32-query zero-failure LoRA+RAG benchmark

---

# Current milestone

The current milestone is no longer fine-tuning.

The first full LoRA evaluation exposed real structured-generation failure modes.

Those failures were retained and diagnosed rather than discarded.

The progression was approximately:

```text
LoRA training
    ↓
initial protected evaluation
    ↓
structured-generation failures observed
    ↓
failure reproduction
    ↓
root-cause isolation
    ↓
prompt + budget hardening
    ↓
duplicate evidence-ID normalization
    ↓
final controlled evaluation
```

The final Base+RAG and LoRA+RAG configurations both achieved:

```text
32 / 32 completed
0 generation failures

answerability accuracy          1.0000
answerable completion           1.0000
unsupported refusal             1.0000
claim citation coverage         1.0000
citation-reference validity     1.0000
source-document coverage        1.0000
expected-term recall            0.9310
structural validity             1.0000
```

The model-adaptation phase can therefore be treated as complete enough to move to controlled ablations.

---

# Phase 1 — Repository foundation — COMPLETE

- [x] Python `src/` layout
- [x] Python 3.12
- [x] `pyproject.toml`
- [x] editable installation
- [x] Typer CLI
- [x] YAML configuration
- [x] Ruff
- [x] pytest
- [x] strict mypy
- [x] GitHub Actions
- [x] branch / pull-request workflow
- [x] MIT license

Future:

- [ ] formal coverage threshold
- [ ] pre-commit hooks

---

# Phase 2 — NASA corpus acquisition — COMPLETE

- [x] NASA NTRS metadata search
- [x] reproducible corpus definition
- [x] versioned corpus configuration
- [x] manifests
- [x] PDF-link resolution
- [x] streamed acquisition
- [x] partial-download handling
- [x] validation
- [x] checksums
- [x] acquisition receipts
- [x] NASA citation URLs
- [x] source URLs

Future:

- [ ] refined inclusion/exclusion rules
- [ ] corpus-version comparison
- [ ] additional public aerospace sources

---

# Phase 3 — Processing and provenance — COMPLETE

- [x] PDF extraction
- [x] page-boundary preservation
- [x] page records
- [x] deterministic overlapping chunks
- [x] document IDs
- [x] page IDs
- [x] page ranges
- [x] source URLs
- [x] NASA citation URLs
- [x] source checksums
- [x] processing receipts

Future:

- [ ] semantic chunking comparison
- [ ] structured table extraction
- [ ] figure extraction
- [ ] OCR fallback

---

# Phase 4 — Retrieval baselines — COMPLETE

## BM25

- [x] deterministic tokenization
- [x] inverted index
- [x] configurable parameters
- [x] deterministic tie-breaking
- [x] provenance
- [x] CLI
- [x] tests

## Dense

Current model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

- [x] normalized embeddings
- [x] 384-dimensional vectors
- [x] versioned metadata
- [x] exact cosine retrieval
- [x] NumPy persistence
- [x] tests
- [x] 3,233-chunk index

---

# Phase 5 — Retrieval evaluation — COMPLETE

Implemented:

- [x] Recall@5
- [x] Recall@10
- [x] MRR@10
- [x] NDCG@10
- [x] pooled evaluation
- [x] BM25 comparison
- [x] dense comparison
- [x] Hybrid RRF comparison
- [x] reranker comparison

Future:

- [ ] larger retrieval benchmark
- [ ] multiple relevance assessors
- [ ] inter-annotator agreement

---

# Phase 6 — Hybrid RRF — COMPLETE

- [x] independent lexical and dense retrieval
- [x] Reciprocal Rank Fusion
- [x] candidate deduplication
- [x] source-rank preservation
- [x] provenance
- [x] evaluation

---

# Phase 7 — Cross-encoder reranking — COMPLETE

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

- [x] bounded candidate reranking
- [x] deterministic testing
- [x] latency telemetry
- [x] provenance
- [x] evaluation

Future:

- [ ] alternate reranker comparison

---

# Phase 8 — Grounded generation — COMPLETE

- [x] provider protocol
- [x] deterministic provider
- [x] OpenAI provider
- [x] local Transformers provider
- [x] structured response schema
- [x] claim schema
- [x] evidence references
- [x] bounded context
- [x] application-controlled citations
- [x] unknown-ID rejection

---

# Phase 9 — Evidence sufficiency — COMPLETE

- [x] minimum evidence requirements
- [x] informative query-term coverage
- [x] numeric support
- [x] named-anchor support
- [x] exact-value handling
- [x] claim qualifiers
- [x] auditable rejection reasons
- [x] model bypass

The sufficiency gate remains part of the system even after model adaptation.

LoRA does not replace evidence validation.

---

# Phase 10 — Facet-aware evidence retrieval — COMPLETE

- [x] deterministic facet planning
- [x] facet-specific retrieval
- [x] evidence deduplication
- [x] balanced evidence selection
- [x] original-query retrieval
- [x] fallback behavior

This remains intentionally constrained rather than being called a general autonomous agent.

---

# Phase 11 — Provider hardening — COMPLETE

- [x] versioned provider configuration
- [x] grounded prompt builder
- [x] response validation
- [x] evidence delimiters
- [x] timeout configuration
- [x] bounded retries
- [x] secret redaction
- [x] prompt-injection heuristics
- [x] unknown evidence-ID rejection
- [x] duplicate evidence-ID normalization
- [x] token telemetry
- [x] latency telemetry
- [x] external cost telemetry

Future:

- [ ] broader adversarial benchmark
- [ ] fault-injection testing
- [ ] circuit-breaker experiment

---

# Phase 12 — Generation evaluation — COMPLETE / ONGOING

Implemented:

- [x] answerability labels
- [x] unsupported controls
- [x] completion metrics
- [x] refusal metrics
- [x] citation coverage
- [x] citation-reference validity
- [x] source-document coverage
- [x] expected-term recall
- [x] structural validity
- [x] failure categories
- [x] provider telemetry
- [x] latency
- [x] tokens
- [x] cost
- [x] frozen evaluation artifacts

Future:

- [ ] semantic expected-concept matching
- [ ] claim-evidence entailment
- [ ] answer-to-claim completeness
- [ ] human review
- [ ] larger protected set

---

# Phase 13 — FastAPI — COMPLETE

- [x] application factory
- [x] shared runtime
- [x] `/health`
- [x] `/ready`
- [x] `/v1/query`
- [x] `/metrics`
- [x] request IDs
- [x] structured errors
- [x] NumPy mode
- [x] pgvector mode
- [x] local generation
- [x] OpenAI generation
- [x] Transformers generation

---

# Phase 14 — Docker — COMPLETE

- [x] Python 3.12 container
- [x] non-root runtime
- [x] health checks
- [x] read-only artifact mounts
- [x] CI Docker build

---

# Phase 15 — Observability — COMPLETE

- [x] structured logs
- [x] request correlation
- [x] OpenTelemetry
- [x] Prometheus
- [x] retrieval latency
- [x] reranker latency
- [x] sufficiency telemetry
- [x] provider call / bypass
- [x] provider latency
- [x] token counts
- [x] citation counts

---

# Phase 16 — Private Cloud Run — COMPLETE

- [x] Artifact Registry
- [x] Cloud Run Gen2
- [x] private invocation
- [x] dedicated runtime identity
- [x] Cloud Storage artifact mounts
- [x] authenticated health checks
- [x] authenticated query validation

Future:

- [ ] infrastructure as code
- [ ] deployment CI
- [ ] rollback automation

---

# Phase 17 — Persistent vector infrastructure — COMPLETE

- [x] PostgreSQL
- [x] pgvector
- [x] Docker Compose
- [x] transactional upserts
- [x] model/dimension validation
- [x] NumPy equivalence benchmark
- [x] PostgreSQL integration tests
- [x] CI service
- [x] runtime backend selection

Measured:

```text
3,233 vectors
384 dimensions
8 / 8 exact top-10 matches
mean overlap@10 = 1.0
```

Future:

- [ ] metadata filtering
- [ ] deletion workflow
- [ ] backup / restore
- [ ] ANN only when corpus size justifies it

---

# Phase 18 — Local Qwen generation — COMPLETE

Model:

```text
Qwen/Qwen3-0.6B
```

Implemented:

- [x] Hugging Face Transformers
- [x] Accelerate
- [x] chat templates
- [x] automatic MPS / CUDA / CPU selection
- [x] configurable dtype
- [x] deterministic decoding
- [x] bounded output
- [x] JSON parsing
- [x] token telemetry
- [x] real Apple MPS validation

---

# Phase 19 — Untuned local benchmark — COMPLETE

Frozen baseline:

```text
Queries: 32
Answerable: 20
Unsupported: 12

Completed: 32 / 32
Failures: 0

Answerability: 1.0000
Completion: 1.0000
Unsupported refusal: 1.0000
Citation coverage: 1.0000
Citation validity: 1.0000
Source coverage: 1.0000
Structural validity: 1.0000
Expected-term recall: 0.9138
```

The baseline was frozen before LoRA training.

---

# Phase 20 — PEFT / LoRA adaptation — COMPLETE

Goal:

> Improve the behavior of a small local model without sacrificing the grounding guarantees already provided by the RAG system.

Implemented:

## Dataset

- [x] independent training-data construction
- [x] benchmark separation
- [x] train/dev split
- [x] overlap auditing
- [x] context-window eligibility
- [x] structured grounded targets
- [x] refusal examples

## Tokenization

- [x] production chat template
- [x] assistant-only loss
- [x] prompt-token masking
- [x] tokenization audit

## Training

- [x] Qwen3-0.6B
- [x] PEFT
- [x] LoRA
- [x] rank 16
- [x] alpha 32
- [x] q/k/v/o projection targets
- [x] gradient checkpointing
- [x] MPS validation
- [x] tiny-overfit gate
- [x] full 3-epoch run
- [x] dev-loss model selection
- [x] adapter reload verification

Training data:

```text
106 training examples
12 development examples
```

The best checkpoint was selected at Epoch 2.

---

# Phase 21 — LoRA failure analysis and robustness — COMPLETE

The initial LoRA benchmark exposed:

```text
truncated structured JSON
supported response without claims
duplicate evidence IDs
```

The project intentionally retained the failed experiment.

Implemented corrections:

- [x] reproduce each failure
- [x] isolate transport vs validation failures
- [x] test larger bounded output budget
- [x] add structured prompt v0.2
- [x] require claims for supported responses
- [x] encourage concise complete JSON
- [x] require unique evidence IDs
- [x] normalize exact duplicate evidence IDs
- [x] preserve strict unknown-ID rejection
- [x] regression-test normalization
- [x] rerun problematic-query gate
- [x] rerun full protected benchmark

This phase is an important part of the project because it demonstrates the distinction between:

```text
model training success
```

and:

```text
system reliability
```

They are not the same thing.

---

# Phase 22 — Final Base+RAG vs LoRA+RAG — COMPLETE

Frozen evaluation:

```text
20 answerable
12 unsupported
32 total
```

## Final quality

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Completed | 32 / 32 | 32 / 32 |
| Failures | 0 | 0 |
| Answerability | 1.0000 | 1.0000 |
| Completion | 1.0000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Citation coverage | 1.0000 | 1.0000 |
| Citation validity | 1.0000 | 1.0000 |
| Source coverage | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 |
| Formal claims | 32 | 53 |
| Claims / answerable query | 1.600 | 2.650 |
| Citation references | 40 | 96 |

## Systems trade-off

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Output tokens | 3,314 | 5,182 |
| P50 provider latency | 8.88 s | 14.87 s |
| P95 provider latency | 16.08 s | 19.13 s |
| External API cost | $0 | $0 |

The adapter therefore changes generation behavior without degrading the currently measured reliability metrics.

Semantic quality remains a separate evaluation problem.

---

# Phase 23 — Four-way model study — NEXT

Goal:

> Separate the effects of retrieval from the effects of model adaptation.

Conditions:

| Condition | LoRA | Retrieval |
|---|---|---|
| Base | No | No |
| LoRA | Yes | No |
| Base + RAG | No | Yes |
| LoRA + RAG | Yes | Yes |

The Base+RAG and LoRA+RAG conditions are already available.

Next implementation:

- [ ] closed-book Base evaluator
- [ ] closed-book LoRA evaluator
- [ ] common frozen query set
- [ ] no synthetic citation scoring in closed-book conditions
- [ ] structural validity
- [ ] expected-concept recall
- [ ] latency
- [ ] token usage
- [ ] failure rate
- [ ] comparative report

The experiment should answer:

```text
What