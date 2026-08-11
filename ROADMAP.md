# AeroRAG-X Roadmap

AeroRAG-X is an independent, evaluation-first engineering project exploring evidence-grounded language-model systems for aerospace technical knowledge.

The governing principle is:

> **Add capability only when its behavior can be measured against an existing baseline.**

---

# Origin

The questions behind AeroRAG-X grew out of my experience working on **HERO**, a Georgia Tech Grand Challenge project sponsored by **Delta Air Lines**.

That experience motivated a broader interest in how aerospace technical information could be searched, synthesized, and connected back to the evidence supporting an engineering answer.

AeroRAG-X is an independent continuation of that technical curiosity.

It is not a HERO or Delta Air Lines deliverable.

The project asks:

> **How far can an evidence-grounded aerospace knowledge system be developed while keeping provenance, failure behavior, model adaptation, and system trade-offs measurable?**

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
pgvector
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
final Base+RAG vs LoRA+RAG evaluation
        ↓
four-way model study
        ↓
bounded adaptive retrieval
        ↓
semantic evaluation
        ↓
efficient inference
        ↓
multimodal technical reports
```

---

# Current status

Completed:

- [x] NASA NTRS corpus
- [x] 3,233 citation-preserving chunks
- [x] BM25 retrieval
- [x] Sentence Transformer embeddings
- [x] NumPy exact dense retrieval
- [x] PostgreSQL + pgvector
- [x] Hybrid Reciprocal Rank Fusion
- [x] cross-encoder reranking
- [x] evidence-sufficiency gating
- [x] facet-aware retrieval
- [x] deterministic grounded generation
- [x] OpenAI structured generation
- [x] Hugging Face Transformers generation
- [x] application-side citation resolution
- [x] FastAPI
- [x] Docker
- [x] Prometheus
- [x] OpenTelemetry
- [x] private Cloud Run validation
- [x] protected evaluation
- [x] failure-tolerant generation benchmarking
- [x] frozen local Qwen baseline
- [x] PEFT / LoRA training
- [x] assistant-only loss masking
- [x] MPS-compatible training
- [x] best-checkpoint selection
- [x] adapter reload verification
- [x] structured-generation failure analysis
- [x] prompt hardening
- [x] bounded output-budget hardening
- [x] duplicate evidence-ID normalization
- [x] final Base+RAG benchmark
- [x] final LoRA+RAG benchmark

Current:

- [ ] Base / LoRA / Base+RAG / LoRA+RAG study

Next:

- [ ] bounded adaptive retrieval
- [ ] semantic evaluation
- [ ] efficient inference
- [ ] multimodal report retrieval

---

# Phase 1 — Repository foundation — COMPLETE

- [x] Python 3.12
- [x] `src/` layout
- [x] `pyproject.toml`
- [x] editable installation
- [x] configuration files
- [x] Typer CLI
- [x] Ruff
- [x] pytest
- [x] strict mypy
- [x] GitHub Actions
- [x] pull-request workflow
- [x] MIT license

Future:

- [ ] formal coverage threshold
- [ ] pre-commit hooks

---

# Phase 2 — NASA corpus acquisition — COMPLETE

- [x] NASA NTRS metadata acquisition
- [x] reproducible corpus definition
- [x] versioned configuration
- [x] manifests
- [x] PDF-link resolution
- [x] streamed acquisition
- [x] validation
- [x] checksums
- [x] acquisition receipts
- [x] NASA citation URLs
- [x] source URLs

Future:

- [ ] additional public aerospace sources
- [ ] refined inclusion/exclusion rules
- [ ] corpus-version comparison

---

# Phase 3 — Processing and provenance — COMPLETE

- [x] PDF extraction
- [x] page-boundary preservation
- [x] deterministic chunking
- [x] document IDs
- [x] page IDs
- [x] page ranges
- [x] source URLs
- [x] citation URLs
- [x] source checksums
- [x] processing receipts

Future:

- [ ] semantic chunking experiment
- [ ] structured table extraction
- [ ] figure extraction
- [ ] OCR fallback

---

# Phase 4 — Retrieval baselines — COMPLETE

## BM25

- [x] deterministic tokenization
- [x] inverted index
- [x] configurable BM25 parameters
- [x] deterministic tie-breaking
- [x] provenance preservation

## Dense retrieval

Model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

- [x] normalized embeddings
- [x] 384 dimensions
- [x] NumPy persistence
- [x] aligned metadata
- [x] exact cosine search
- [x] 3,233-chunk index

Future:

- [ ] embedding-model comparison
- [ ] larger-scale ANN experiment only when justified

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

- [ ] larger relevance set
- [ ] multiple assessors
- [ ] inter-annotator agreement

---

# Phase 6 — Hybrid retrieval — COMPLETE

- [x] Reciprocal Rank Fusion
- [x] lexical + dense retrieval
- [x] deterministic deduplication
- [x] rank preservation
- [x] score preservation
- [x] provenance

---

# Phase 7 — Cross-encoder reranking — COMPLETE

Model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

- [x] bounded reranking
- [x] deterministic tests
- [x] latency measurement
- [x] provenance
- [x] evaluation

Future:

- [ ] reranker comparison

---

# Phase 8 — Grounded generation — COMPLETE

- [x] provider interface
- [x] deterministic provider
- [x] OpenAI provider
- [x] Transformers provider
- [x] structured response schema
- [x] claim schema
- [x] evidence references
- [x] bounded context
- [x] application-controlled citations
- [x] invalid-state rejection

---

# Phase 9 — Evidence sufficiency — COMPLETE

- [x] minimum evidence
- [x] informative query-term coverage
- [x] numeric support
- [x] named anchors
- [x] exact-value handling
- [x] claim qualifiers
- [x] auditable rejection reasons
- [x] provider bypass

The gate remains independent of model adaptation.

---

# Phase 10 — Facet-aware retrieval — COMPLETE

- [x] deterministic facet planning
- [x] facet-specific search
- [x] semantic facet verification
- [x] evidence deduplication
- [x] balanced evidence selection
- [x] original-query evidence
- [x] fallback behavior

The implementation remains deliberately bounded.

---

# Phase 11 — Provider hardening — COMPLETE

- [x] versioned provider configuration
- [x] grounded prompt builder
- [x] response validation
- [x] bounded retries
- [x] evidence delimiters
- [x] token telemetry
- [x] latency telemetry
- [x] cost telemetry
- [x] secret redaction
- [x] prompt-injection heuristics
- [x] unknown evidence-ID rejection
- [x] exact duplicate evidence-ID normalization

Future:

- [ ] broader adversarial testing
- [ ] fault-injection benchmark
- [ ] circuit-breaker experiment

---

# Phase 12 — Generation evaluation — COMPLETE / ONGOING

Implemented:

- [x] answerability labels
- [x] unsupported controls
- [x] answerability accuracy
- [x] answerable completion
- [x] unsupported refusal
- [x] citation coverage
- [x] citation validity
- [x] source-document coverage
- [x] expected-term recall
- [x] structural validity
- [x] provider telemetry
- [x] generation failure categories
- [x] local / remote provider classification
- [x] frozen evaluation artifacts

Future:

- [ ] semantic expected-concept matching
- [ ] claim-evidence entailment
- [ ] answer-to-claim completeness
- [ ] human review
- [ ] larger protected benchmark

---

# Phase 13 — FastAPI — COMPLETE

- [x] application factory
- [x] shared heavy runtime
- [x] environment configuration
- [x] `/health`
- [x] `/ready`
- [x] `/v1/query`
- [x] `/metrics`
- [x] request IDs
- [x] structured errors
- [x] NumPy backend
- [x] pgvector backend
- [x] deterministic provider
- [x] OpenAI provider
- [x] Transformers provider

---

# Phase 14 — Docker — COMPLETE

- [x] Python 3.12 image
- [x] non-root runtime
- [x] health check
- [x] artifact mounts
- [x] CI build

---

# Phase 15 — Observability — COMPLETE

- [x] structured logs
- [x] request correlation
- [x] Prometheus
- [x] OpenTelemetry
- [x] BM25 latency
- [x] dense latency
- [x] RRF latency
- [x] reranker latency
- [x] sufficiency telemetry
- [x] provider telemetry
- [x] token counts
- [x] citation counts

---

# Phase 16 — Private Cloud Run — COMPLETE

- [x] Artifact Registry
- [x] Cloud Run Gen2
- [x] private invocation
- [x] dedicated runtime identity
- [x] Cloud Storage artifacts
- [x] authenticated health validation
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
- [x] persistent embeddings
- [x] transactional upserts
- [x] model metadata
- [x] dimension validation
- [x] NumPy comparison
- [x] PostgreSQL tests
- [x] CI integration
- [x] runtime backend selection

Measured:

```text
3,233 chunks
384 dimensions
8 / 8 exact top-10 matches
mean overlap@10 = 1.0
```

Future:

- [ ] metadata filtering
- [ ] deletion workflow
- [ ] backup/restore
- [ ] ANN at larger corpus scale

---

# Phase 18 — Local Qwen generation — COMPLETE

Model:

```text
Qwen/Qwen3-0.6B
```

Implemented:

- [x] Hugging Face Transformers
- [x] Accelerate
- [x] model chat templates
- [x] deterministic decoding
- [x] output limits
- [x] JSON parsing
- [x] provider telemetry
- [x] Apple MPS
- [x] CUDA detection
- [x] CPU fallback

---

# Phase 19 — Untuned local-model baseline — COMPLETE

Original frozen local benchmark:

```text
Queries: 32
Answerable: 20
Unsupported: 12

Completed: 32 / 32
Generation failures: 0

Answerability: 1.0000
Completion: 1.0000
Unsupported refusal: 1.0000
Citation coverage: 1.0000
Citation validity: 1.0000
Source coverage: 1.0000
Structural validity: 1.0000
Expected-term recall: 0.9138
```

This baseline was frozen before adapter training.

---

# Phase 20 — PEFT / LoRA training — COMPLETE

Goal:

> Increase structured technical decomposition while preserving grounded system behavior.

## Data

- [x] independent training-data construction
- [x] protected benchmark separation
- [x] train/dev split
- [x] overlap audit
- [x] context-window eligibility
- [x] refusal examples
- [x] structured grounded targets

Final eligible data:

```text
106 training examples
12 development examples
```

## Tokenization

- [x] production chat template
- [x] assistant-only loss
- [x] prompt masking
- [x] tokenization audit

## Training

```text
Model: Qwen/Qwen3-0.6B

LoRA rank: 16
alpha: 32
dropout: 0.05

targets:
q_proj
k_proj
v_proj
o_proj
```

- [x] PEFT
- [x] gradient checkpointing
- [x] Apple MPS training
- [x] tiny-overfit gate
- [x] 3-epoch full run
- [x] development evaluation
- [x] best-checkpoint selection
- [x] adapter save/reload validation

Best checkpoint:

```text
Epoch 2
```

---

# Phase 21 — LoRA failure analysis — COMPLETE

The first protected LoRA run exposed:

```text
truncated JSON
supported response with zero formal claims
duplicate evidence IDs
```

Implemented investigation:

- [x] preserve failed benchmark
- [x] reproduce failures
- [x] distinguish transport and validation failures
- [x] test increased bounded output budget
- [x] harden structured prompt
- [x] require claims for supported responses
- [x] require complete JSON
- [x] reduce redundant generation
- [x] request unique evidence IDs
- [x] normalize exact duplicate evidence IDs
- [x] preserve unknown-ID rejection
- [x] targeted robustness benchmark
- [x] full rerun

This phase demonstrates an important project principle:

```text
training success
!=
system reliability
```

---

# Phase 22 — Final Base+RAG vs LoRA+RAG — COMPLETE

Evaluation set:

```text
20 answerable
12 unsupported
32 total
```

## Reliability

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

## Response decomposition

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Formal claims | 32 | 53 |
| Claims / answerable query | 1.600 | 2.650 |
| Citation references | 40 | 96 |

Claim-count increase:

```text
65.625%
```

Across answerable queries:

```text
claim count improved: 16
claim count decreased: 2
unchanged: 2
```

## Systems trade-off

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Output tokens | 3,314 | 5,182 |
| P50 provider latency | 8.88 s | 14.87 s |
| P95 provider latency | 16.08 s | 19.13 s |
| External API cost | $0 | $0 |

## Important limitation

Aggregate expected-term recall is unchanged, but individual query behavior differs.

Observed:

```text
para_005:
0.667 → 1.000

para_009:
0.667 → 0.333
```

Therefore the current conclusion is:

> LoRA increases structured decomposition substantially, but does not uniformly increase every measure of content coverage.

---

# Phase 23 — Four-way model study — CURRENT

Goal:

> **Separate the contribution of retrieval from the contribution of adaptation.**

Conditions:

| Condition | LoRA | RAG |
|---|---|---|
| Base | No | No |
| LoRA | Yes | No |
| Base + RAG | No | Yes |
| LoRA + RAG | Yes | Yes |

Already frozen:

- [x] Base + RAG
- [x] LoRA + RAG

Next:

- [ ] closed-book Base evaluator
- [ ] closed-book LoRA evaluator
- [ ] Base closed-book run
- [ ] LoRA closed-book run
- [ ] common metrics
- [ ] four-way comparison report

## Closed-book metrics

Measure:

- completion
- generation failures
- expected-term recall
- formal claims
- claims/query
- structural validity
- provider latency
- token usage

Do not compute artificial citation metrics for closed-book responses.

Citation fields should be:

```text
N/A
```

The experiment should answer:

```text
What does retrieval contribute?

What does LoRA contribute?

What happens when retrieval and LoRA are combined?
```

---

# Phase 24 — Bounded adaptive retrieval — PLANNED

Goal:

> Determine whether one bounded recovery step can improve questions where the initial retrieved evidence is weak.

Proposed state machine:

```text
QUESTION
   ↓
RETRIEVE
   ↓
ASSESS
   │
   ├── sufficient ─────────────→ GENERATE
   │
   └── insufficient
             ↓
        REWRITE QUERY
             ↓
        RETRIEVE AGAIN
             ↓
           ASSESS
             │
             ├── sufficient → GENERATE
             │
             └── insufficient
                     ↓
               GROUNDED REFUSAL
```

Hard constraints:

```text
maximum retrieval passes = 2
bounded state transitions
deterministic termination
validated inputs
evidence provenance preserved
grounded refusal preserved
```

Potential operations:

```text
retrieve
assess_evidence
rewrite_query
retrieve_facet_evidence
inspect_source
```

The objective is not autonomous behavior.

The objective is a measurable comparison between:

```text
single-pass retrieval
vs
bounded adaptive retrieval
```

---

# Phase 25 — Adaptive-retrieval evaluation — PLANNED

Metrics:

- [ ] difficult-query recovery
- [ ] answerability
- [ ] unsupported refusal
- [ ] grounding
- [ ] citation validity
- [ ] unnecessary second retrievals
- [ ] retrieval attempts/query
- [ ] invalid transitions
- [ ] termination failures
- [ ] latency overhead
- [ ] token overhead

Failure categories:

```text
routing failure
rewrite failure
retrieval failure
evidence-assessment failure
unnecessary recovery
termination failure
unsupported synthesis
citation failure
```

---

# Phase 26 — Semantic evaluation — PLANNED

The current expected-term metric is deterministic but lexical.

Next metrics:

- [ ] semantic expected-concept recall
- [ ] claim-evidence entailment
- [ ] claim support
- [ ] answer-to-claim completeness
- [ ] answer relevance
- [ ] redundancy
- [ ] independent human assessment

Primary question:

> Does increased claim decomposition correspond to genuinely better technical coverage?

---

# Phase 27 — Efficient local inference — PLANNED

Only after the model-quality studies are complete.

Measure:

- [ ] model-load time
- [ ] peak memory
- [ ] generation latency
- [ ] P50
- [ ] P95
- [ ] tokens/second
- [ ] structured-output validity
- [ ] grounding preservation

Candidates:

```text
FP16
BF16 where supported
INT8 where supported
```

Hardware-specific performance claims require actual measurements on that hardware.

---

# Phase 28 — Multimodal technical reports — FUTURE

Potential work:

- [ ] figure detection
- [ ] figure captions
- [ ] page linkage
- [ ] table extraction
- [ ] structured tables
- [ ] image retrieval
- [ ] image citations
- [ ] table citations
- [ ] multimodal evaluation
- [ ] OCR fallback

---

# Phase 29 — Evaluation maturity — ONGOING

Completed:

- [x] retrieval evaluation
- [x] generation evaluation
- [x] protected benchmark
- [x] local-model baseline
- [x] LoRA benchmark
- [x] negative-result preservation
- [x] failure categorization
- [x] structured-generation regression tests
- [x] provider telemetry
- [x] backend comparison

Future:

- [ ] larger protected set
- [ ] conflicting evidence
- [ ] partial evidence
- [ ] adversarial unsupported questions
- [ ] semantic metrics
- [ ] multiple human assessors
- [ ] inter-annotator agreement
- [ ] confidence intervals

---

# Phase 30 — Releases and reproducibility — ONGOING

The repository history now records:

```text
retrieval baseline
generation baseline
OpenAI reference
local Qwen baseline
pgvector comparison
LoRA training
failed LoRA evaluation
failure diagnosis
structured-output hardening
final Base+RAG / LoRA+RAG evaluation
```

Candidate future experiment milestones:

```text
four-way adaptation/retrieval study
bounded adaptive retrieval
semantic evaluation
efficient inference
multimodal retrieval
```

Release labels should follow completed experiments rather than a fixed schedule.

---

# Explicit non-priorities

The project will not add technologies purely for stack breadth.

Current non-priorities include:

- Kubernetes
- Redis
- additional vector databases
- unrestricted autonomous agents
- reinforcement learning without a measured need
- HNSW at the current corpus scale
- multiple orchestration frameworks
- additional cloud providers
- speculative hardware optimization
- frontend redesign

New infrastructure should follow a measured engineering requirement.

---

# Immediate next milestone

The next question is:

> **How much of AeroRAG-X's final behavior comes from retrieval, and how much comes from LoRA adaptation?**

Sequence:

```text
freeze Base+RAG
        ↓
freeze LoRA+RAG
        ↓
build closed-book response schema
        ↓
build closed-book evaluator
        ↓
run Base closed-book
        ↓
run LoRA closed-book
        ↓
compare all four conditions
        ↓
analyze retrieval/adaptation interaction
        ↓
begin bounded adaptive retrieval
```

After that:

> **Can one bounded retrieval-recovery step improve weak-evidence questions without sacrificing grounding, termination, or citation integrity?**

That becomes the next systems experiment.
