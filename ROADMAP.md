# AeroRAG-X Roadmap

[Project overview and measured results](README.md)

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
four-way model/system study
        ↓
semantic and claim-level evaluation
        ↓
bounded adaptive retrieval
        ↓
protected adaptive-retrieval evaluation
        ↓
scope-qualifier safeguard and held-out evaluation
        ↓
adaptive-retrieval interoperability and observability
        ↓
edge-runtime benchmark
        ↓
MLX structured-transport foundation
        ↓
controlled MLX 4-bit versus MPS float16 comparison
        ↓
multimodal technical reports
```

# Current status

Completed:

- [x] NASA NTRS corpus
- [x] 3,233 citation-preserving chunks
- [x] BM25, dense, Hybrid RRF, and cross-encoder reranking
- [x] evidence-sufficiency gating and facet-aware retrieval
- [x] deterministic, OpenAI, and Transformers grounded generation
- [x] FastAPI, Docker, Prometheus, OpenTelemetry, and private Cloud Run validation
- [x] PostgreSQL + pgvector equivalence validation
- [x] frozen local Qwen baseline
- [x] PEFT / LoRA training, checkpointing, reload verification, and failure analysis
- [x] final Base+RAG / LoRA+RAG and corrected four-way studies
- [x] Phase 24 semantic expected-concept, claim-support, completeness, redundancy, and unsupported-response evaluation
- [x] bounded adaptive retrieval with one deterministic rewrite and at most two passes
- [x] protected Phase 26 adaptive-retrieval evaluation, including its negative result
- [x] opt-in scope-qualifier safeguard and separately authored held-out evaluation
- [x] opt-in LangGraph controller, LangChain reranked retriever adapter, and adaptive-retrieval observability
- [x] Phase 32 edge-runtime benchmark schema, runner, JSON/Markdown artifacts, and measured MPS results
- [x] Apple-Silicon MLX structured-generation transport with strict JSON validation and live smoke coverage
- [x] Phase 34 controlled MLX affine 4-bit versus Transformers MPS float16 comparison, including versioned JSON/Markdown artifacts and explicit interpretation limits

Next:

- [ ] Phase 35 multimodal technical-report retrieval design and baseline evaluation

Future:

- [ ] broader MLX API/CLI provider integration only if a separately scoped evaluation justifies it

- [ ] larger protected evaluation set
- [ ] conflicting and partial evidence studies
- [ ] multiple human assessors and inter-annotator agreement
- [ ] multimodal technical-report retrieval

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

- [x] formal 80% coverage threshold
- [x] pre-commit quality and frozen-evidence hooks

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
- [x] rollback runbook and measurable triggers
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
- [x] backup / restore runbook with staging verification
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

# Phase 25 — Bounded adaptive retrieval — COMPLETE

Implemented:

- [x] at most two retrieval passes
- [x] one deterministic query rewrite
- [x] preserved retrieval and evidence provenance
- [x] grounded refusal after a second insufficient pass
- [x] CLI and API opt-in controls
- [x] frozen Phase 24 baseline protection

The native bounded controller remains the default. The project does not treat this as unrestricted autonomous behavior.

---

# Phase 26 — Adaptive-retrieval evaluation — COMPLETE

The protected paired evaluation reproduced the frozen single-pass baseline, then compared it with the opt-in bounded-adaptive policy.

| Metric | Single pass | Bounded adaptive |
|---|---:|---:|
| Answerability accuracy | 91.67% | 83.33% |
| Unsupported refusal | 83.33% | 66.67% |

The result is preserved as a negative result. No protected thresholds, policy settings, data, or artifacts were tuned after observing it. The adaptive policy remains opt-in.

---

# Phase 27 — Scope-qualifier safeguard — COMPLETE / OPT-IN

The Phase 26 diagnosis showed that topically related evidence could be treated as support for overly broad claims, such as universal coverage, permanent replacement, or zero risk.

Implemented:

- [x] separately authored unsupported-scope development challenge
- [x] opt-in v0.3.0 scope-qualifier checking
- [x] regression coverage
- [x] no modification of protected Phase 26 data, settings, or artifacts

The safeguard is not treated as a general claim of universal correctness; it is a bounded, measured response to a specific observed failure mode.

---

# Phase 28 — Scope-qualifier held-out evaluation — COMPLETE

A separately versioned held-out benchmark evaluated the opt-in Phase 27 safeguard without reusing the Phase 26 protected evaluation.

| Metric | Bounded adaptive | Bounded adaptive + scope safeguard |
|---|---:|---:|
| Answerability accuracy | 50.00% | 92.86% |
| Unsupported-query refusal | 40.00% | 100.00% |

No thresholds or policy settings were tuned after observing the held-out result.

---

# Phase 29 — Evaluation maturity — ONGOING

Completed:

- [x] retrieval and generation evaluation
- [x] protected local-model baseline
- [x] Base / LoRA and four-way system studies
- [x] negative-result preservation
- [x] structured-generation regression tests
- [x] semantic expected-concept evaluation
- [x] claim-evidence support adjudication
- [x] answer-to-claim completeness
- [x] unsupported-response taxonomy
- [x] within-answer claim redundancy
- [x] bounded-adaptive and scope-qualifier evaluation
- [x] edge-runtime measurement artifacts

Future:

- [ ] larger protected set
- [ ] conflicting and partial evidence
- [ ] multiple human assessors
- [ ] inter-annotator agreement
- [ ] confidence intervals

---

# Phase 30 — Releases and reproducibility — ONGOING

The repository preserves both successful and negative experiments, including:

```text
retrieval baseline
generation baseline
local Qwen baseline
LoRA training and failure analysis
corrected four-way system study
Phase 24 consolidated quality report
adaptive-retrieval regression
scope-qualifier development and held-out results
edge-runtime benchmark schema and measurements
MLX structured-transport smoke validation
```

Release labels follow completed, reproducible evidence rather than a fixed schedule.

---

# Phase 31 — Adaptive-retrieval interoperability and observability — COMPLETE

Implemented:

- [x] opt-in LangGraph controller with native-controller parity
- [x] LangChain `BaseRetriever` adapter for reranked hits
- [x] preserved source and retrieval provenance at the framework boundary
- [x] selected adaptive-retrieval orchestrator in answer metadata
- [x] bounded-retrieval safety invariants and recovery tests

The native bounded controller remains the default. Framework integrations are optional and do not replace the project’s bounded retrieval policy.

---

# Phase 32 — Edge-runtime benchmarking — COMPLETE

The benchmark compares fixed structured-generation workloads on one Apple-Silicon host. Each case uses one warm-up iteration and three measured iterations; model loading is excluded from per-request latency, and accelerator work is synchronized at timing boundaries.

| Case | Mean latency | Output throughput |
|---|---:|---:|
| Base CPU float32 | 1189.29 ms | 23.54 tok/s |
| Base MPS float32 | 1015.00 ms | 27.59 tok/s |
| Base MPS float16 | **695.43 ms** | **40.26 tok/s** |
| LoRA MPS float16 | 1146.71 ms | 34.01 tok/s |

The LoRA condition generated more output tokens than the Base conditions, so raw latency is not treated as an identical-workload comparison.

Tracked artifacts:

```text
configs/edge_runtime_benchmark_v0_1.yaml
docs/edge-runtime-benchmark-v0_1.md
reports/edge_runtime_benchmark_v0_1.json
reports/edge_runtime_benchmark_v0_1.md
scripts/run_edge_runtime_benchmark_v0_1.py
```

---

# Phase 33 — MLX structured-generation transport — COMPLETE

Implemented:

- [x] optional `mlx` dependency extra for macOS arm64
- [x] versioned MLX runtime configuration
- [x] Qwen-compatible chat templating with thinking disabled by default
- [x] deterministic sampling and prompt-budget checks
- [x] strict JSON-object parsing and token-usage reporting
- [x] unit tests for plain/fenced JSON, configuration, token budgets, and stdout hygiene
- [x] live Apple-Silicon structured-generation smoke test
- [x] local model artifacts ignored by Git

The transport is intentionally provider-neutral and benchmark-oriented. It is not yet an API or CLI runtime mode.

---

# Phase 34 — Controlled MLX 4-bit versus MPS float16 evaluation — COMPLETE

Question:

> **On the same Apple-Silicon host and fixed structured-generation workload, what trade-offs does a genuine MLX 4-bit Qwen runtime make relative to the measured Transformers MPS float16 baseline?**

Implemented controls:

- [x] same structured prompt and JSON schema
- [x] 2,048-token input cap and 96-token output cap
- [x] one warm-up and three measured iterations per runtime
- [x] deterministic Transformers MPS float16 greedy decoding and deterministic MLX affine 4-bit sampling
- [x] recorded model, artifact, runtime, Python, PyTorch, and MLX versions
- [x] explicit MPS and MLX synchronization at timing boundaries
- [x] model construction and loading excluded from per-request latency

Results:

| Runtime | Valid JSON | Mean latency | P50 latency | P95 latency | Output tok/s | Artifact size |
|---|---:|---:|---:|---:|---:|---:|
| Transformers MPS float16 | 3/3 | 715.11 ms | 699.42 ms | 742.58 ms | 39.15 | 1448.83 MiB |
| MLX affine 4-bit, group size 128 | 3/3 | 278.43 ms | 277.85 ms | 280.47 ms | 122.11 | 313.10 MiB |

The report records total token counts across the three measured runs: 186 input and 84 output tokens for Transformers, and 423 input and 102 output tokens for MLX. The differing totals are reported rather than normalized away.

Tracked artifacts:

```text
configs/mlx_mps_runtime_comparison_v0_1.yaml
reports/mlx_mps_runtime_comparison_v0_1.json
reports/mlx_mps_runtime_comparison_v0_1.md
scripts/run_mlx_mps_runtime_comparison_v0_1.py
src/aeroragx/generation/mlx_mps_runtime_comparison.py
tests/test_mlx_mps_runtime_comparison.py
```

Interpretation limits:

- The result is limited to this one Apple-Silicon host and measured software environment.
- It is not a Qualcomm QNN, Hexagon, or device-deployment measurement.
- Latency and throughput do not establish output-quality equivalence.
- The evaluation does not silently repair malformed output or weaken the structured JSON contract.

---

# Phase 35 — Multimodal technical reports — IN PROGRESS

Completed foundation:

- [x] page-linked figure/table provenance contract and validation
- [x] versioned manually verified evaluation slice with five visual assets
- [x] checksum-verified whole-page PNG rendering for linked source pages
- [x] deterministic `PageRenderRecord` JSONL manifest and local runner
- [x] deterministic independent-review task and response contracts
- [x] versioned five-task multimodal annotation-task set

Next:

- [ ] obtain two independently completed, versioned review response sets
- [ ] report agreement and disagreements without overstating reliability
- [ ] larger versioned multimodal corpus with independent annotation review
- [ ] automatic figure/table detection and caption association
- [ ] table extraction and structured tables
- [ ] image retrieval and citations
- [ ] table citations
- [ ] multimodal evaluation
- [ ] OCR fallback

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

Phase 34 completed the controlled local comparison between the established Transformers MPS float16 baseline and a genuine MLX affine 4-bit Qwen artifact. It recorded valid structured JSON in every measured run, timing, throughput, artifact size, token totals, runtime versions, and explicit interpretation limits.

The next question is:

> **How can AeroRAG-X retrieve and cite figures and tables from aerospace technical reports while preserving page-level provenance and measurable evaluation?**

Phase 35 has established page-linked provenance, a manually verified five-asset
slice, checksum-verified rendering, a deterministic render manifest, and a
deterministic independent-review task set. The text-only baseline remains protected.

Sequence:

```text
freeze the current text-only corpus and retrieval baseline
        ↓
define page-linked figure and table provenance requirements
        ↓
create a small, versioned multimodal evaluation slice
        ↓
render linked pages and write a deterministic provenance manifest
        ↓
define and independently complete versioned annotation tasks
        ↓
expand the candidate corpus and measure reviewer agreement
        ↓
implement figure/table detection with explicit source-page linkage
        ↓
evaluate text, figure, and table retrieval separately
        ↓
add OCR fallback only for measured extraction gaps
```

Hard constraints:

```text
no model-weight commits
no changes to protected retrieval or generation evaluation data
no citation without a source page and document identifier
no claim of multimodal quality without a separately versioned evaluation
no speculative hardware or provider-integration work without a measured need
```

<!-- phase35-review-evidence-v0_1 -->
## Phase 35 review-evidence gate status

- [x] strict complete-review validation contract
- [x] deterministic finalization script
- [x] regression tests preventing partial-overlap evidence claims
- [x] documented pre-review adjudication policy
- [ ] reviewer A completes every frozen v0.1 task
- [ ] reviewer B independently completes every frozen v0.1 task
- [ ] raw exact agreement is finalized
- [ ] real disagreements, if any, are adjudicated separately
- [ ] reviewed v0.1 evidence package is frozen

Automatic figure/table detection, OCR, visual indexing, and multimodal
retrieval remain downstream of the completed review-evidence gate.

<!-- phase36-agent-tool-contracts-v0_1 -->
# Phase 36 — Bounded agent tool contracts

- [x] typed tool input/output contracts
- [x] provenance-preserving hybrid retrieval boundary
- [x] authoritative source-context boundary
- [x] evidence-sufficiency tool boundary
- [x] deterministic citation-validation tool
- [x] structured multi-source comparison boundary
- [x] explicit allowed-tool registry
- [x] bounded agent state contract
- [x] tool/step/retrieval budgets
- [x] structured backend-failure records
- [x] focused contract/state/tool tests

Next: Phase 37 implements dynamic stateful LangGraph routing over these bounded
tools. Phase 36 alone is not an autonomous-agent claim.

<!-- phase37-stateful-agent-graph-v0_1 -->
# Phase 37 — Stateful tool-using agent graph

- [x] schema-constrained planner decisions
- [x] dynamic tool routing
- [x] registered-tool execution only
- [x] bounded graph steps and tool calls
- [x] grounded generation and citation-validation route
- [x] explicit terminal reasons
- [x] inspectable trajectory records
- [ ] persistent checkpoint/resume
- [ ] human-review decision persistence

Next: Phase 38 checkpointing and human-in-the-loop resumption.

<!-- phase38-checkpointing-hitl-v0_1 -->
# Phase 38 — Checkpointing and HITL

- [x] immutable versioned state checkpoints
- [x] latest-checkpoint recovery
- [x] graph-state checkpoint observer
- [x] human-review request/response contracts
- [x] approve/reject/edit resume semantics
- [x] original paused state preserved
- [ ] injected dependency failure policy
- [ ] recovery benchmark

Next: Phase 39 failure recovery and fault injection.

<!-- phase39-agent-failure-recovery-v0_1 -->
# Phase 39 — Failure recovery and fault injection

- [x] typed failure classes
- [x] per-tool bounded retry policy
- [x] deterministic fault injection
- [x] structured retry classification
- [x] unrecoverable-failure safe termination
- [x] regression tests for no-evidence degradation
- [ ] frozen trajectory benchmark

Next: Phase 40 evaluates agent trajectories and recovery behavior.

<!-- phase40-agent-trajectory-benchmark-v0_1 -->
# Phase 40 — Agent trajectory benchmark

- [x] frozen-case schema
- [x] observation schema
- [x] termination/tool/budget/refusal metrics
- [x] latency metrics
- [x] orchestrator-comparison contract
- [x] synthetic contract fixtures
- [ ] curate 40–60 real frozen domain cases
- [ ] record deterministic baseline
- [ ] record bounded-adaptive baseline
- [ ] record stateful-agent baseline
- [ ] publish measured comparison

The harness is complete; performance claims remain blocked on real frozen data.

<!-- phase41-service-contracts-v0_1 -->
# Phase 41 — Microservice contracts

- [x] cross-service request context
- [x] retrieval request/response contracts
- [x] inference request/response contracts
- [x] Agent API contracts
- [x] structured service errors
- [x] health contract
- [x] typed async HTTP clients
- [ ] independent containers
- [ ] Docker Compose orchestration

Next: Phase 42 distributed runtime.

<!-- phase42-distributed-runtime-v0_1 -->
# Phase 42 — Distributed runtime

- [x] Agent API process
- [x] Retrieval Service process
- [x] Inference Service process
- [x] separate Dockerfiles
- [x] Docker Compose topology
- [x] liveness/readiness endpoints
- [x] cross-service async contracts
- [x] citation identity check at Agent API boundary
- [ ] real backend adapters in deployment environment
- [ ] distributed tracing and retry/degradation instrumentation

Next: Phase 43 distributed reliability.

<!-- phase43-distributed-reliability-v0_1 -->
# Phase 43 — Distributed reliability

- [x] bounded async service retries
- [x] retry classification for timeout/server errors
- [x] OpenTelemetry propagation helpers
- [x] Prometheus service metrics
- [x] safe no-answer degradation contract
- [x] reliability regression tests
- [ ] measured concurrent-load benchmark
- [ ] measured fault-injection benchmark

Next: Phase 44 distributed reliability benchmark.

<!-- phase44-distributed-reliability-benchmark-v0_1 -->
# Phase 44 — Distributed reliability benchmark

- [x] concurrent request harness
- [x] per-request observation schema
- [x] success/timeout/recovery metrics
- [x] safe-refusal and unsafe-answer metrics
- [x] p50/p95 latency metrics
- [x] scenario configuration
- [ ] run healthy baseline
- [ ] run retrieval fault scenarios
- [ ] run inference fault scenarios
- [ ] run vector-store fault scenario
- [ ] freeze measured report

No SLO or reliability claim is complete until measured runs are frozen.

<!-- phase45-grpo-reward-harness-v0_1 -->
# Phase 45 — GRPO reward harness

- [x] grounded training-case contract
- [x] multi-objective reward weights
- [x] refusal/citation/evidence/tool-efficiency rewards
- [x] reward-hacking regression tests
- [x] training/evaluation leakage guard
- [x] reproducible experiment config
- [ ] execute GRPO training
- [ ] evaluate trained policy on frozen held-out set

Next: Phase 46 bounded grounded-agent GRPO experiment.

<!-- phase46-grpo-grounded-agent-v0_1 -->
# Phase 46 — Grounded-agent GRPO experiment

- [x] stateful tool-use training environment
- [x] bounded tool surface
- [x] environment-owned reward integration
- [x] lazy TRL trainer integration
- [x] validation-only/default-safe training CLI
- [x] synthetic format fixtures
- [x] free Kaggle P100 Pascal-compatible fp16 LoRA configuration and notebook
- [x] resumable checkpoints and hashed run receipt
- [x] real-case quality and near-duplicate leakage validation
- [x] hashed train/protected-evaluation dataset manifest
- [ ] prepare real versioned training set
- [ ] verify disjoint protected evaluation IDs
- [ ] execute training on suitable hardware
- [ ] freeze model/config/data hashes

Next: Phase 47 held-out Base vs LoRA vs GRPO ablation.

<!-- phase47-grpo-agent-ablation-v0_1 -->
# Phase 47 — Base vs LoRA/SFT vs GRPO ablation

- [x] common held-out observation schema
- [x] identical-case-set enforcement
- [x] task/refusal/citation/evidence metrics
- [x] tool-selection and efficiency metrics
- [x] latency metrics
- [x] non-prescriptive report template
- [x] reproducibility metadata contract and measured-report freezer
- [ ] record Base results
- [ ] record LoRA/SFT results
- [ ] record GRPO results
- [ ] freeze final measured ablation

The applied-RL gap is closed only after a genuine GRPO run and held-out
comparison are recorded; the harness alone is not an RL performance result.
