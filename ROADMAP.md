# AeroRAG-X Roadmap

AeroRAG-X is an evaluation-first, evidence-grounded RAG and local-LLM engineering project for aerospace technical knowledge.

The governing principle is:

> Add capability only when its behavior can be measured against an existing baseline.

---

# Development sequence

```text
Reliable NASA corpus
        ↓
citation-preserving processing
        ↓
BM25 + dense retrieval
        ↓
pooled retrieval evaluation
        ↓
Hybrid RRF
        ↓
cross-encoder reranking
        ↓
grounded generation
        ↓
evidence-sufficiency gating
        ↓
structured provider hardening
        ↓
generation evaluation
        ↓
FastAPI
        ↓
Docker
        ↓
observability
        ↓
private Cloud Run
        ↓
pgvector backend
        ↓
local Hugging Face generation
        ↓
protected local-model baseline
        ↓
PEFT / LoRA
        ↓
model + RAG ablation study
        ↓
reduced-precision inference
        ↓
bounded research agent
        ↓
agent evaluation
        ↓
multimodal retrieval
```

---

# Current status

The text-RAG infrastructure, persistent vector backend, and first real local Hugging Face generation path are implemented.

Validated capabilities include:

- [x] NASA NTRS corpus
- [x] 3,233 citation-preserving chunks
- [x] BM25
- [x] Sentence Transformer retrieval
- [x] NumPy exact dense retrieval
- [x] PostgreSQL + pgvector retrieval
- [x] Hybrid RRF
- [x] cross-encoder reranking
- [x] evidence-sufficiency gating
- [x] facet-aware evidence retrieval
- [x] deterministic generation
- [x] OpenAI structured generation
- [x] local Hugging Face Transformers generation
- [x] application-side citation resolution
- [x] FastAPI
- [x] Docker
- [x] structured logs
- [x] Prometheus
- [x] OpenTelemetry
- [x] private Cloud Run validation
- [x] protected evaluation split
- [x] CI regression policy
- [x] real Qwen local smoke validation
- [x] unsupported-query local-model bypass

---

# Current priority

The next priority is to freeze a protected benchmark for the untuned local Qwen baseline.

Immediate sequence:

1. merge the local Transformers provider;
2. freeze untuned Qwen + RAG evaluation;
3. classify local-model failure modes;
4. add PEFT / LoRA training;
5. compare base, RAG, LoRA, and LoRA + RAG;
6. benchmark reduced-precision inference;
7. add a bounded tool-using research workflow;
8. evaluate agent behavior.

---

# Phase 1 — Repository foundation — IMPLEMENTED

- [x] Python `src/` layout
- [x] `pyproject.toml`
- [x] Python 3.12
- [x] editable installation
- [x] Typer CLI
- [x] YAML configuration
- [x] Ruff
- [x] pytest
- [x] coverage reporting
- [x] strict mypy
- [x] GitHub Actions
- [x] feature-branch workflow
- [x] pull-request workflow
- [x] MIT license
- [x] protected `main`
- [x] required CI before merge
- [x] force-push prevention

Future:

- [ ] formal coverage threshold
- [ ] pre-commit hooks

---

# Phase 2 — NASA corpus acquisition — IMPLEMENTED

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
- [ ] corpus-version comparison tooling
- [ ] additional approved aerospace sources

---

# Phase 3 — Processing and provenance — IMPLEMENTED

- [x] PDF extraction
- [x] page-boundary preservation
- [x] page-level records
- [x] deterministic overlapping chunks
- [x] document IDs
- [x] page IDs
- [x] page ranges
- [x] source URLs
- [x] NASA citation URLs
- [x] source checksums
- [x] processing receipts

Future:

- [ ] title on every chunk
- [ ] publication date on every chunk
- [ ] semantic chunking experiment
- [ ] fixed vs semantic comparison
- [ ] table extraction
- [ ] figure extraction
- [ ] OCR fallback

---

# Phase 4 — Retrieval baselines — IMPLEMENTED

## BM25

- [x] deterministic tokenization
- [x] inverted index
- [x] configurable `k1`
- [x] configurable `b`
- [x] deterministic tie-breaking
- [x] provenance preservation
- [x] CLI
- [x] tests

## Dense

- [x] Sentence Transformers
- [x] normalized embeddings
- [x] NumPy persistence
- [x] aligned metadata
- [x] versioned manifest
- [x] exact cosine similarity
- [x] CLI
- [x] tests
- [x] 3,233-chunk index

Future:

- [ ] alternative embedding models
- [ ] embedding-throughput benchmark
- [ ] ANN only when corpus scale justifies it

---

# Phase 5 — Retrieval evaluation — IMPLEMENTED

- [x] retrieval v0.1
- [x] pooled v0.2
- [x] Recall@5
- [x] Recall@10
- [x] MRR@10
- [x] NDCG@10
- [x] BM25 comparison
- [x] dense comparison
- [x] Hybrid RRF comparison
- [x] reranker comparison
- [x] 278 pooled candidates
- [x] 101 relevant labels
- [x] 177 non-relevant labels

Future:

- [ ] larger retrieval dataset
- [ ] independent relevance audit
- [ ] multiple assessors
- [ ] inter-annotator agreement
- [ ] retrieval-regression thresholds

---

# Phase 6 — Hybrid retrieval — IMPLEMENTED

- [x] Reciprocal Rank Fusion
- [x] independent BM25 and dense search
- [x] deterministic candidate deduplication
- [x] source ranks and scores
- [x] provenance
- [x] CLI
- [x] tests
- [x] pooled evaluation

---

# Phase 7 — Cross-encoder reranking — IMPLEMENTED

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

- [x] bounded candidate reranking
- [x] deterministic fake-scorer tests
- [x] provenance
- [x] latency measurement
- [x] pooled evaluation
- [x] CLI

Future:

- [ ] alternate reranker benchmark
- [ ] CPU / MPS / CUDA comparison

---

# Phase 8 — Grounded generation — IMPLEMENTED

- [x] provider protocol
- [x] deterministic provider
- [x] structured response schema
- [x] claim schema
- [x] citation schema
- [x] source-document schema
- [x] bounded evidence and context
- [x] evidence-ID validation
- [x] application-side citation resolution
- [x] invalid-state rejection
- [x] JSON output
- [x] CLI integration
- [x] OpenAI adapter

---

# Phase 9 — Evidence sufficiency — IMPLEMENTED

- [x] minimum evidence count
- [x] informative query-term coverage
- [x] minimum supported terms
- [x] single-evidence coverage
- [x] numeric support
- [x] named-anchor support
- [x] exact-query handling
- [x] morphology normalization
- [x] claim-qualifier support
- [x] auditable rejection reasons
- [x] provider bypass
- [x] v0.2.1 calibration

The gate is both a grounding mechanism and an inference-cost/latency control.

---

# Phase 10 — Facet-aware evidence retrieval — IMPLEMENTED

- [x] deterministic facet planning
- [x] facet-specific search
- [x] semantic facet verification
- [x] evidence deduplication
- [x] balanced evidence selection
- [x] original-query evidence
- [x] fallback behavior
- [x] CLI integration
- [x] evaluation integration

Future:

- [ ] broaden only after additional benchmark coverage

---

# Phase 11 — Provider hardening — IMPLEMENTED

- [x] versioned provider configuration
- [x] structured prompt builder
- [x] prompt version IDs
- [x] OpenAI structured adapter
- [x] HTTP transport
- [x] provider factory
- [x] timeout handling
- [x] bounded retries
- [x] response validation
- [x] latency telemetry
- [x] token telemetry
- [x] cost telemetry
- [x] secret redaction
- [x] prompt-injection heuristics
- [x] evidence delimiters
- [x] unknown evidence-ID rejection

Future:

- [ ] broader adversarial evaluation
- [ ] semantic injection detector experiment
- [ ] circuit breaker
- [ ] fault-injection benchmark
- [ ] Secret Manager integration

---

# Phase 12 — Generation evaluation — IMPLEMENTED

- [x] answerability labels
- [x] unsupported controls
- [x] answerability accuracy
- [x] answerable completion
- [x] unsupported refusal
- [x] claim citation coverage
- [x] citation-reference validity
- [x] source-document coverage
- [x] expected-term recall
- [x] structural validity
- [x] per-query reports
- [x] provider telemetry
- [x] deterministic baseline
- [x] OpenAI baseline
- [x] 32-query v0.3 development set
- [x] 12-query protected v0.4 deterministic held-out set
- [x] frozen artifacts
- [x] CI regression policy

## Development v0.3

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

## Protected deterministic held-out v0.4

| Metric | Result |
|---|---:|
| Answerability accuracy | 0.9167 |
| Answerable completion | 1.0000 |
| Unsupported refusal | 0.8333 |
| Claim citation coverage | 1.0000 |
| Citation-reference validity | 1.0000 |
| Expected-term recall | 0.7778 |
| Structural validity | 1.0000 |

Future:

- [ ] semantic citation support
- [ ] answer faithfulness
- [ ] answer relevance
- [ ] human review
- [ ] multiple assessors

---

# Phase 13 — FastAPI — IMPLEMENTED

- [x] application factory
- [x] query-service injection
- [x] shared heavy runtime
- [x] environment-driven configuration
- [x] deterministic mode
- [x] OpenAI mode
- [x] Transformers mode
- [x] NumPy backend selection
- [x] pgvector backend selection
- [x] `/health`
- [x] `/ready`
- [x] `/v1/query`
- [x] `/metrics`
- [x] request IDs
- [x] structured errors
- [x] provider observability
- [x] API tests
- [x] runtime reuse

---

# Phase 14 — Docker and local deployment — IMPLEMENTED

- [x] Dockerfile
- [x] `.dockerignore`
- [x] Python 3.12 image
- [x] non-root runtime
- [x] health check
- [x] read-only corpus mounts
- [x] read-only embedding mounts
- [x] deterministic container smoke test
- [x] GitHub Actions Docker build
- [x] BuildKit cache

Future:

- [ ] dedicated local-Transformers Docker benchmark
- [ ] GPU-container benchmark when appropriate

---

# Phase 15 — Observability — IMPLEMENTED

- [x] structured JSON logs
- [x] request-ID correlation
- [x] trace/span correlation
- [x] runtime-load events
- [x] HTTP latency
- [x] total RAG latency
- [x] BM25 latency
- [x] dense latency
- [x] Hybrid RRF latency
- [x] reranker latency
- [x] facet telemetry
- [x] sufficiency telemetry
- [x] provider called/bypassed
- [x] provider attempts
- [x] provider latency
- [x] token counts
- [x] cost telemetry
- [x] citation counts
- [x] Prometheus
- [x] OpenTelemetry
- [x] load testing
- [x] failure runbook

---

# Phase 16 — Private Cloud Run — IMPLEMENTED

- [x] Artifact Registry
- [x] immutable image digest
- [x] Cloud Run Gen2
- [x] dedicated runtime service account
- [x] private invocation
- [x] Cloud Storage artifact mounts
- [x] bucket-scoped read permissions
- [x] authenticated health validation
- [x] authenticated readiness validation
- [x] authenticated query validation

Future:

- [ ] infrastructure as code
- [ ] deployment CI
- [ ] rollback automation
- [ ] cloud budget alerts
- [ ] public-demo policy
- [ ] public rate limiting
- [ ] local-LLM cloud deployment benchmark

---

# Phase 17 — Persistent vector infrastructure — IMPLEMENTED

- [x] PostgreSQL + pgvector
- [x] Docker Compose development service
- [x] vector-store configuration
- [x] persistent embeddings
- [x] persistent provenance
- [x] transactional upserts
- [x] embedding-model metadata
- [x] dimension validation
- [x] index-version metadata
- [x] exact cosine retrieval
- [x] NumPy comparison
- [x] exact retrieval equivalence
- [x] latency comparison
- [x] PostgreSQL integration tests
- [x] PostgreSQL CI service
- [x] runtime backend selection
- [x] API backend selection
- [x] NumPy retained as default

Measured:

```text
3,233 chunks
384 dimensions
8/8 exact top-10 matches
overlap@10 = 1.0
max score delta = 2.8e-07
```

Future:

- [ ] metadata filtering
- [ ] deletion workflow
- [ ] backup/restore
- [ ] HNSW comparison at larger scale
- [ ] managed PostgreSQL deployment

---

# Phase 18 — Local neural generation — IMPLEMENTED

Current first baseline model:

```text
Qwen/Qwen3-0.6B
```

## Dependencies and configuration

- [x] optional `llm` dependency group
- [x] PyTorch
- [x] Hugging Face Transformers
- [x] Accelerate
- [x] versioned Transformers runtime configuration
- [x] versioned generation configuration

## Transport

- [x] `TransformersStructuredModelTransport`
- [x] lazy Hugging Face model loading
- [x] `AutoTokenizer`
- [x] `AutoModelForCausalLM`
- [x] model-specific chat templates
- [x] configurable thinking mode
- [x] configurable decoding
- [x] input-token budget validation
- [x] output-token limit
- [x] strict JSON parsing
- [x] token telemetry
- [x] provider errors

## Hardware

- [x] automatic CUDA detection
- [x] automatic Apple MPS detection
- [x] CPU fallback
- [x] configurable dtype
- [x] real Apple MPS validation

## Architecture integration

- [x] provider-factory integration
- [x] existing structured-provider reuse
- [x] zero external API-token cost
- [x] API runtime mode
- [x] provider observability label
- [x] NumPy compatibility
- [x] pgvector-compatible runtime selection
- [x] public generation-package exports

## Testing

- [x] fake tokenizer/model unit tests
- [x] factory tests
- [x] API settings tests
- [x] API observability tests
- [x] offline CI support
- [x] real supported-query smoke test
- [x] real unsupported-query provider bypass
- [x] reproducible `scripts/smoke_transformers.py`

This phase establishes functionality. It does not establish broad local-model quality.

---

# Phase 19 — Untuned local-model benchmark — CURRENT PRIORITY

Goal:

> Freeze the behavior of untuned Qwen + AeroRAG-X before any fine-tuning.

## Evaluation design

- [ ] audit the existing generation evaluator for local providers
- [ ] ensure local provider telemetry is recorded correctly
- [ ] freeze benchmark configuration
- [ ] preserve the existing held-out split
- [ ] avoid tuning against protected held-out data

## Metrics

- [ ] answerability accuracy
- [ ] answerable completion
- [ ] unsupported refusal
- [ ] claim citation coverage
- [ ] citation-reference validity
- [ ] source-document coverage
- [ ] expected-term recall
- [ ] structural validity
- [ ] provider-call policy
- [ ] JSON parse failure rate
- [ ] provider failure rate
- [ ] input tokens
- [ ] output tokens
- [ ] P50 provider latency
- [ ] P95 provider latency
- [ ] P50 total RAG latency
- [ ] P95 total RAG latency

## Local-model failure analysis

- [ ] answer-to-claim coverage
- [ ] incomplete claim decomposition
- [ ] unnecessary refusal
- [ ] unsupported synthesis
- [ ] malformed JSON
- [ ] invalid evidence references
- [ ] retrieval miss
- [ ] reranking miss
- [ ] sufficiency false positive
- [ ] sufficiency false negative

Target artifacts:

```text
artifacts/evaluation/generation_transformers_base_v0_1.json
artifacts/evaluation/generation_transformers_base_telemetry_v0_1.json
```

The baseline must be frozen before LoRA training begins.

---

# Phase 20 — PEFT / LoRA domain adaptation — PLANNED

Goal:

> Improve structured grounded synthesis behavior without training the model to memorize the NASA corpus.

Planned subsystem:

```text
src/aeroragx/training/
├── dataset.py
├── split.py
├── formatting.py
├── sft.py
├── adapter.py
└── evaluation.py
```

Planned configuration:

```text
configs/training/lora_v0_1.yaml
```

Data requirements:

- [ ] preserve evidence IDs
- [ ] preserve refusal examples
- [ ] preserve structured output
- [ ] train/dev/test boundaries
- [ ] query-overlap audit
- [ ] answer-overlap audit
- [ ] source-document leakage audit
- [ ] configuration hashes
- [ ] deterministic seeds

Training requirements:

- [ ] add PEFT
- [ ] configure LoRA targets
- [ ] train first adapter
- [ ] track base-model revision
- [ ] track adapter version
- [ ] track dataset hash
- [ ] track LoRA parameters
- [ ] record trainable-parameter count

LoRA should target better structured JSON, claim decomposition, evidence-ID use, refusal behavior, and concise synthesis. It is not a replacement for retrieval.

---

# Phase 21 — Base vs RAG vs LoRA experiment — PLANNED

| Model | RAG | Purpose |
|---|---|---|
| Base | No | model-only baseline |
| Base | Yes | retrieval benefit |
| LoRA | No | adaptation-only benefit |
| LoRA | Yes | adapted RAG |
| OpenAI | Yes | external reference |

All configurations should use the same frozen evaluation set.

Metrics must include answerability, grounding, citation validity, expected-term recall, structure, refusal behavior, latency, and tokens.

---

# Phase 22 — Efficient local inference — PLANNED

Benchmark:

- [ ] model load time
- [ ] peak memory
- [ ] first-token latency
- [ ] total generation latency
- [ ] tokens per second
- [ ] model size
- [ ] structured-output validity
- [ ] grounding quality after reduced precision

Candidates:

- [ ] FP16
- [ ] BF16 where supported
- [ ] INT8 where supported

Do not claim hardware-specific optimization without testing on that hardware.

---

# Phase 23 — Bounded tool-using research agent — PLANNED

Potential tools:

```text
search_corpus
retrieve_document
inspect_source
compare_documents
retrieve_facet_evidence
calculate
```

Potential flow:

```text
question
   ↓
complexity routing
   ↓
simple RAG OR bounded planner
   ↓
tool calls
   ↓
evidence accumulation
   ↓
sufficiency check
   ↓
structured synthesis
   ↓
citation validation
```

Planned safeguards:

- [ ] bounded maximum tool calls
- [ ] deterministic termination policy
- [ ] tool argument validation
- [ ] evidence-ID preservation
- [ ] citation validation
- [ ] ordinary-RAG fallback

LangGraph may be evaluated, but the architecture should not depend entirely on the orchestration framework.

---

# Phase 24 — Agent evaluation — PLANNED

Metrics:

- [ ] task completion
- [ ] correct tool selection
- [ ] correct tool arguments
- [ ] grounded answer rate
- [ ] citation validity
- [ ] unsupported-answer rate
- [ ] unnecessary tool calls
- [ ] invalid tool calls
- [ ] loop rate
- [ ] average tools per query
- [ ] latency
- [ ] token usage
- [ ] external cost

Failure categories:

```text
routing failure
tool-selection failure
tool-argument failure
retrieval failure
insufficient-evidence failure
looping
unsupported synthesis
citation failure
```

---

# Phase 25 — Multimodal technical reports — PLANNED

- [ ] figure detection
- [ ] figure-caption extraction
- [ ] page linkage
- [ ] table detection
- [ ] structured table extraction
- [ ] multimodal records
- [ ] image citations
- [ ] table citations
- [ ] multimodal query dataset
- [ ] multimodal answer evaluation
- [ ] OCR fallback

---

# Phase 26 — Evaluation maturity — ONGOING

Already implemented:

- [x] retrieval benchmarks
- [x] generation benchmark
- [x] regression policy
- [x] development split
- [x] held-out split
- [x] frozen deterministic baseline

Future:

- [ ] larger retrieval benchmark
- [ ] larger generation benchmark
- [ ] conflicting evidence
- [ ] partial evidence
- [ ] adversarial prompt injection
- [ ] latency regression thresholds
- [ ] semantic citation support
- [ ] semantic answer faithfulness
- [ ] semantic answer relevance
- [ ] independent human review
- [ ] multiple assessors
- [ ] inter-annotator agreement

---

# Phase 27 — Release and reproducibility — ONGOING

Completed:

- [x] v0.1.0 baseline
- [x] protected `main`
- [x] architecture diagrams
- [x] deterministic demo
- [x] benchmark reporting
- [x] Docker documentation
- [x] Cloud Run documentation
- [x] pgvector backend
- [x] local Transformers provider
- [x] real local-model smoke script

Candidate future milestones:

```text
v0.2 — local neural generation baseline
v0.3 — PEFT / LoRA evaluation
v0.4 — efficient local inference
v0.5 — bounded agentic research workflow
```

Version naming remains provisional until the corresponding evaluations are complete.

---

# Explicit non-priorities

The following are intentionally not immediate priorities:

- additional vector databases
- Kubernetes
- Redis
- HNSW at the current 3,233-vector scale
- public frontend redesign
- reinforcement learning
- additional cloud providers
- generic autonomous-agent behavior

These may become appropriate later if measured requirements justify them.

---

# Immediate next milestone

The next branch should answer one question:

> How well does the untuned local Qwen model perform across the existing protected AeroRAG-X evaluation framework?

```text
merge Transformers provider
        ↓
create benchmark branch
        ↓
audit evaluator
        ↓
run untuned Qwen benchmark
        ↓
freeze artifacts
        ↓
failure taxonomy
        ↓
only then begin LoRA
```
