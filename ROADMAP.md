# AeroRAG-X Roadmap

AeroRAG-X is an independent, evaluation-first engineering project exploring evidence-grounded language-model systems for aerospace technical knowledge.

The governing principle is:

> **Add capability only when its behavior can be measured against an existing baseline.**

---

# Origin

The questions behind AeroRAG-X grew out of my experience working on **HERO**, a Georgia Tech Grand Challenge project sponsored by **Delta Air Lines**.

AeroRAG-X is an independent continuation of that technical curiosity and is not a HERO or Delta Air Lines deliverable.

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
LoRA failure analysis
        ↓
structured-generation hardening
        ↓
final Base+RAG vs LoRA+RAG evaluation
        ↓
closed-book Base / LoRA evaluation
        ↓
canonical-refusal normalization
        ↓
corrected four-way model/system study
        ↓
semantic and claim-level evaluation
        ↓
bounded adaptive retrieval
        ↓
adaptive-retrieval evaluation
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
- [x] frozen local Qwen baseline
- [x] PEFT / LoRA training
- [x] assistant-only loss masking
- [x] MPS-compatible training
- [x] best-checkpoint selection
- [x] adapter reload verification
- [x] LoRA structured-generation failure analysis
- [x] structured-generation prompt hardening
- [x] bounded output-budget hardening
- [x] duplicate evidence-ID normalization
- [x] final Base+RAG benchmark
- [x] final LoRA+RAG benchmark
- [x] closed-book Base evaluator
- [x] closed-book LoRA evaluator
- [x] raw closed-book v0.1 benchmark
- [x] raw refusal-payload diagnosis
- [x] canonical-refusal normalization
- [x] normalized closed-book v0.2 benchmark
- [x] corrected four-way Base / LoRA system study
- [x] semantic expected-concept baseline

Current:

- [ ] claim-level and unsupported-response evaluation

Next:

- [ ] unsupported-response semantic taxonomy
- [ ] claim-evidence entailment
- [ ] answer-to-claim completeness
- [ ] targeted human audit
- [ ] bounded adaptive retrieval
- [ ] adaptive-retrieval evaluation
- [ ] efficient inference
- [ ] multimodal technical-report retrieval

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
- [x] closed-book evaluation
- [x] canonical-refusal normalization
- [x] four-way system comparison

Current extensions:

- [ ] semantic expected-concept matching
- [ ] claim-evidence entailment
- [ ] answer-to-claim completeness
- [ ] unsupported-response taxonomy
- [ ] redundancy measurement
- [ ] targeted human review

Future:

- [ ] larger protected benchmark
- [ ] multiple human assessors
- [ ] inter-annotator agreement
- [ ] confidence intervals

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
- [ ] backup / restore
- [ ] ANN only at a larger corpus scale

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
- [x] bounded output
- [x] JSON parsing
- [x] provider telemetry
- [x] Apple MPS
- [x] CUDA detection
- [x] CPU fallback
- [x] optional PEFT adapter loading

---

# Phase 19 — Untuned local-model grounded baseline — COMPLETE

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

Training success is treated as a prerequisite for evaluation, not as evidence of generalization.

---

# Phase 21 — LoRA failure analysis — COMPLETE

The first protected LoRA + RAG run exposed:

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

This phase established:

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
claim count increased: 16
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

Therefore:

> LoRA increases structured decomposition substantially, but does not uniformly increase every measure of content coverage.

---

# Phase 23 — Four-way Base / LoRA system study — COMPLETE

Goal:

> **Separate model-adaptation effects from the behavior of the full grounded system.**

Conditions:

| Condition | LoRA | Grounded RAG |
|---|---|---|
| Base closed-book | No | No |
| LoRA closed-book | Yes | No |
| Base + RAG | No | Yes |
| LoRA + RAG | Yes | Yes |

## Closed-book evaluator

Implemented:

- [x] separate closed-book response contract
- [x] no artificial citation fields
- [x] shared Transformers transport
- [x] Base / LoRA adapter checks
- [x] answerability metrics
- [x] refusal metrics
- [x] expected-term recall
- [x] formal claim counts
- [x] structural validation
- [x] latency telemetry
- [x] token telemetry
- [x] focused unit tests
- [x] real-model canaries

## Raw closed-book v0.1

The first full Base run produced:

```text
27 / 32 completed
5 response-validation failures
```

Raw-payload investigation showed:

```text
4 canonical refusals
+ explanatory claims

1 canonical refusal
+ missing insufficient_knowledge field
```

These were schema-compliance failures rather than five independent hallucination failures.

The original artifacts remain preserved.

## Canonical-refusal normalization

A narrow normalizer was introduced.

Only the exact canonical refusal sentence may:

- recover a missing `insufficient_knowledge=true`
- discard explanatory claims when the response already represents a canonical refusal

Unrelated malformed outputs remain invalid.

Targeted five-query validation:

```text
5 / 5 completed
0 failures
1.0000 answerability
1.0000 unsupported refusal
1.0000 structural validity
```

## Corrected closed-book v0.2

| Metric | Base closed-book | LoRA closed-book |
|---|---:|---:|
| Completed | 32 / 32 | 32 / 32 |
| Failures | 0 | 0 |
| Answerability | 0.7812 | 0.7812 |
| Completion | 1.0000 | 1.0000 |
| Strict unsupported refusal | 0.4167 | 0.4167 |
| Expected-term recall | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 |
| Formal answerable claims | 21 | 33 |
| Claims / answerable query | 1.050 | 1.650 |

Closed-book claim-count increase:

```text
57.1%
```

## Final corrected four-way study

| Metric | Base closed-book | LoRA closed-book | Base + RAG | LoRA + RAG |
|---|---:|---:|---:|---:|
| Completed | 32 / 32 | 32 / 32 | 32 / 32 | 32 / 32 |
| Failures | 0 | 0 | 0 | 0 |
| Answerability | 0.7812 | 0.7812 | 1.0000 | 1.0000 |
| Strict unsupported refusal | 0.4167 | 0.4167 | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Formal claims | 21 | 33 | 32 | 53 |
| Claims / answerable query | 1.050 | 1.650 | 1.600 | 2.650 |

Primary conclusions:

1. LoRA does not change the measured normalized closed-book reliability metrics on this benchmark.
2. LoRA increases formal technical decomposition in both closed-book and grounded conditions.
3. The full grounded evidence pipeline provides the strongest unsupported-query reliability boundary.
4. Lexical expected-term recall cannot distinguish systems whose behavior differs substantially.
5. Semantic and claim-level evaluation is required before adding more orchestration complexity.

---

# Phase 24 — Semantic and claim-level evaluation — COMPLETE

Primary question:

> **Does increased formal claim decomposition correspond to genuinely better supported technical content?**

Completed evaluation layers:

- [x] semantic expected-concept coverage
- [x] claim-to-evidence support
- [x] answer-to-claim completeness
- [x] unsupported-response semantic taxonomy
- [x] within-answer claim redundancy
- [x] consolidated Phase 24 quality report

The adjudication stages use frozen policies and single structured review passes. They are not presented as independent multi-assessor human studies.

## Consolidated grounded-system result

| Dimension | Base + RAG | LoRA + RAG | LoRA - Base |
|---|---:|---:|---:|
| Semantic concept coverage, conservative micro | 38.16% | 51.32% | +13.16 pp |
| Semantic concept coverage, upper-bound micro | 53.95% | 65.79% | +11.84 pp |
| Strict claim-evidence support | 65.62% | 67.92% | +2.30 pp |
| Support-or-partial claim-evidence support | 87.50% | 90.57% | +3.07 pp |
| Full answer-to-claim capture | 10.00% | 45.00% | +35.00 pp |
| Full-or-partial answer-to-claim capture | 60.00% | 95.00% | +35.00 pp |
| Full redundancy rate | 0.00% | 1.89% | +1.89 pp |
| Partial-overlap rate | 12.50% | 39.62% | +27.12 pp |
| Unsupported-query safe non-assertion | 100.00% | 100.00% | +0.00 pp |

Claim counts:

```text
Base + RAG     32 formal claims
LoRA + RAG     53 formal claims
```

Claim-support adjudication also found:

```text
Base + RAG     0 contradicted claims
LoRA + RAG     3 contradicted claims
```

## Unsupported-query taxonomy

| Condition | Safe non-assertion | Unsupported-assertion rate |
|---|---:|---:|
| Base closed-book | 58.33% | 41.67% |
| LoRA closed-book | 75.00% | 25.00% |
| Base + RAG | 100.00% | 0.00% |
| LoRA + RAG | 100.00% | 0.00% |

The taxonomy distinguishes explicit refusals from corrective denials, so a failed strict-refusal metric is not automatically treated as a hallucination.

## Phase 24 conclusion

On this protected grounded benchmark, LoRA increased structured technical decomposition and answer-to-claim completeness, and it produced higher expected-concept coverage while maintaining broadly similar claim-to-evidence support rates.

The additional claims were rarely fully redundant, although partial semantic overlap increased substantially and a small number of contradicted LoRA claims remained.

Retrieval-grounded execution provided the strongest unsupported-query boundary in both grounded conditions.

These results do not establish universal factual accuracy or universal model superiority.

Frozen consolidated artifacts:

```text
artifacts/evaluation/phase24_quality_summary_v0_1.json
artifacts/evaluation/phase24_quality_inputs_v0_1.sha256
artifacts/evaluation/phase24_quality_v0_1.sha256
reports/phase24_quality_v0_1.md
```

---

# Phase 25 — Bounded adaptive retrieval — PLANNED

Goal:

> Determine whether one bounded recovery step can improve questions where initial evidence is weak.

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

The objective is a measured comparison between:

```text
single-pass retrieval
vs
bounded adaptive retrieval
```

not unrestricted autonomous behavior.

---

# Phase 26 — Adaptive-retrieval evaluation — PLANNED

Metrics:

- [ ] difficult-query recovery
- [ ] answerability
- [ ] unsupported refusal
- [ ] semantic claim support
- [ ] citation validity
- [ ] unnecessary second retrievals
- [ ] retrieval attempts / query
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

# Phase 27 — Efficient local inference — PLANNED

Only after the model-quality and adaptive-retrieval studies are complete.

Measure:

- [ ] model-load time
- [ ] peak memory
- [ ] generation latency
- [ ] P50
- [ ] P95
- [ ] tokens / second
- [ ] structured-output validity
- [ ] grounding preservation

Candidates:

```text
FP16
BF16 where supported
INT8 where supported
```

Hardware-specific performance claims require measurements on the hardware being discussed.

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
- [x] four-way Base / LoRA system study
- [x] raw versus normalized contract analysis

Additional completed evaluation milestones:

- [x] semantic expected-concept evaluation
- [x] claim-evidence support adjudication
- [x] unsupported-response taxonomy
- [x] answer-to-claim completeness
- [x] within-answer claim redundancy
- [x] Phase 24 consolidated quality report

Current:

- [ ] bounded adaptive retrieval implementation
- [ ] adaptive-retrieval evaluation design

Future:

- [ ] larger protected set
- [ ] conflicting evidence
- [ ] partial evidence
- [ ] broader adversarial unsupported controls
- [ ] multiple human assessors
- [ ] inter-annotator agreement
- [ ] confidence intervals

---

# Phase 30 — Releases and reproducibility — ONGOING

The repository history records:

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
raw closed-book v0.1
closed-book failure diagnosis
canonical-refusal normalization
normalized closed-book v0.2
corrected four-way model/system study
```

Candidate future experiment milestones:

```text
semantic evaluation
claim/evidence faithfulness
bounded adaptive retrieval
adaptive-retrieval evaluation
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

Phase 24 semantic and claim-level evaluation is complete.

The next question is:

> **Can one bounded retrieval-recovery step improve weak-evidence questions without sacrificing grounding, deterministic termination, or citation integrity?**

Sequence:

```text
freeze Phase 24 consolidated quality baseline
        ↓
implement bounded retrieval state machine
        ↓
define deterministic evidence-recovery trigger
        ↓
allow at most one query rewrite
        ↓
allow at most one second retrieval pass
        ↓
preserve provenance and grounded refusal
        ↓
evaluate single-pass vs bounded adaptive retrieval
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

Only after the bounded adaptive-retrieval study should AeroRAG-X move to efficient local inference or broader retrieval modalities.
