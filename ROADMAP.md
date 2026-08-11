# AeroRAG-X Roadmap

AeroRAG-X is an independent, evaluation-first engineering project exploring evidence-grounded language-model systems for aerospace technical knowledge.

> **Add capability only when its behavior can be measured against an existing baseline.**

## Origin

The questions behind AeroRAG-X grew out of my experience working on **HERO**, a Georgia Tech Grand Challenge project sponsored by **Delta Air Lines**. AeroRAG-X is an independent continuation of that technical curiosity and is not a HERO or Delta Air Lines deliverable.

## Development sequence

```text
NASA corpus → provenance-preserving processing → BM25/dense retrieval
→ Hybrid RRF → reranking → evidence sufficiency → grounded generation
→ FastAPI/Docker/observability → private Cloud Run → pgvector
→ local Qwen → PEFT/LoRA → failure analysis → structured hardening
→ Base+RAG vs LoRA+RAG → closed-book Base/LoRA → canonical refusal normalization
→ corrected four-way study → semantic evaluation → bounded adaptive retrieval
→ adaptive-retrieval evaluation → efficient inference → multimodal reports
```

## Current status

Completed:
- [x] NASA NTRS corpus, 3,233 citation-preserving chunks
- [x] BM25, dense retrieval, Hybrid RRF, cross-encoder reranking
- [x] NumPy exact cosine and PostgreSQL + pgvector
- [x] facet-aware retrieval and evidence-sufficiency gating
- [x] deterministic, OpenAI, and Transformers generation
- [x] application-side citation resolution
- [x] FastAPI, Docker, Prometheus, OpenTelemetry
- [x] private Cloud Run validation
- [x] protected evaluation
- [x] Qwen3-0.6B baseline
- [x] PEFT / LoRA training and best-checkpoint selection
- [x] LoRA failure analysis and structured-generation hardening
- [x] Base+RAG and LoRA+RAG final benchmark
- [x] closed-book Base / LoRA evaluator
- [x] raw closed-book v0.1 benchmark and failure diagnosis
- [x] canonical-refusal normalization
- [x] normalized closed-book v0.2 benchmark
- [x] corrected four-way Base / LoRA system study

Current:
- [ ] semantic and claim-level evaluation

Next:
- [ ] semantic expected-concept matching
- [ ] claim-evidence entailment
- [ ] answer-to-claim completeness
- [ ] unsupported-response taxonomy
- [ ] targeted human review
- [ ] bounded adaptive retrieval
- [ ] adaptive-retrieval evaluation
- [ ] efficient inference
- [ ] multimodal technical-report retrieval

---

# Phases 1–18 — Foundation and grounded system — COMPLETE

Completed work includes repository foundation, NASA corpus acquisition, provenance-preserving processing, BM25 and dense baselines, retrieval evaluation, Hybrid RRF, cross-encoder reranking, grounded generation, evidence sufficiency, facet-aware retrieval, provider hardening, generation evaluation, FastAPI, Docker, observability, private Cloud Run, persistent pgvector infrastructure, and local Qwen generation.

Key measured retrieval result:

```text
3,233 chunks
384 dimensions
8/8 exact NumPy/pgvector top-10 matches
mean overlap@10 = 1.0
```

---

# Phase 19 — Untuned local grounded baseline — COMPLETE

```text
Queries: 32
Answerable: 20
Unsupported: 12
Completed: 32/32
Failures: 0
Answerability: 1.0000
Unsupported refusal: 1.0000
Citation coverage: 1.0000
Citation validity: 1.0000
Source coverage: 1.0000
Structural validity: 1.0000
Expected-term recall: 0.9138
```

---

# Phase 20 — PEFT / LoRA training — COMPLETE

```text
Model: Qwen/Qwen3-0.6B
Training examples: 106
Development examples: 12
Epochs: 3
LoRA rank: 16
alpha: 32
dropout: 0.05
targets: q_proj, k_proj, v_proj, o_proj
Best checkpoint: Epoch 2
```

The adapter remains local and gitignored.

---

# Phase 21 — LoRA failure analysis — COMPLETE

The first protected LoRA + RAG run exposed:

```text
truncated JSON
supported response with zero formal claims
duplicate evidence IDs
```

The failures were preserved, reproduced, and used to harden the structured-generation path.

---

# Phase 22 — Final Base+RAG vs LoRA+RAG — COMPLETE

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Completed | 32/32 | 32/32 |
| Failures | 0 | 0 |
| Answerability | 1.0000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Citation coverage | 1.0000 | 1.0000 |
| Citation validity | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 |
| Formal claims | 32 | 53 |
| Claims / answerable query | 1.600 | 2.650 |
| Citation references | 40 | 96 |

LoRA increased formal-claim count by **65.625%** while the measured reliability metrics remained unchanged.

---

# Phase 23 — Four-way Base / LoRA system study — COMPLETE

Conditions:

| Condition | LoRA | Grounded RAG |
|---|---|---|
| Base closed-book | No | No |
| LoRA closed-book | Yes | No |
| Base + RAG | No | Yes |
| LoRA + RAG | Yes | Yes |

Raw Base v0.1 produced 27/32 completed queries and five response-validation failures. Raw-payload inspection showed those five were semantic refusal attempts outside the strict response contract. A narrow canonical-refusal normalizer was added for v0.2; unrelated malformed outputs remain invalid.

Corrected v0.2 results:

| Metric | Base closed-book | LoRA closed-book | Base + RAG | LoRA + RAG |
|---|---:|---:|---:|---:|
| Completed | 32/32 | 32/32 | 32/32 | 32/32 |
| Failures | 0 | 0 | 0 | 0 |
| Answerability | 0.7812 | 0.7812 | 1.0000 | 1.0000 |
| Strict refusal | 0.4167 | 0.4167 | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Formal claims | 21 | 33 | 32 | 53 |

Primary conclusions:
1. LoRA does not change normalized closed-book reliability on this benchmark.
2. LoRA increases structured technical decomposition in both closed-book and grounded conditions.
3. The full grounded evidence pipeline provides the strongest unsupported-query reliability boundary.
4. Lexical expected-term recall cannot distinguish systems whose behavior differs substantially.
5. Semantic and claim-level evaluation is the next required layer.

---

# Phase 24 — Semantic and claim-level evaluation — CURRENT

Primary question:

> **Does increased formal claim decomposition correspond to genuinely better technical content?**

Planned metrics:
- [ ] semantic expected-concept coverage
- [ ] claim-evidence entailment
- [ ] claim support
- [ ] answer-to-claim completeness
- [ ] unsupported-response semantic taxonomy
- [ ] redundancy
- [ ] answer relevance
- [ ] targeted human review

Unsupported-response categories:

```text
EXPLICIT_REFUSAL
CORRECTIVE_DENIAL
UNSUPPORTED_ASSERTION
STRUCTURAL_FAILURE
```

---

# Phase 25 — Bounded adaptive retrieval — PLANNED

Goal: determine whether one bounded recovery step can improve questions where initial evidence is weak.

```text
QUESTION → RETRIEVE → ASSESS
                    ├─ sufficient → GENERATE
                    └─ insufficient → REWRITE → RETRIEVE ONCE MORE → ASSESS
                                                       ├─ sufficient → GENERATE
                                                       └─ insufficient → GROUNDED REFUSAL
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

---

# Phase 26 — Adaptive-retrieval evaluation — PLANNED

Metrics will include difficult-query recovery, answerability, unsupported refusal, semantic claim support, citation validity, unnecessary second retrievals, retrieval attempts/query, invalid transitions, termination failures, latency overhead, and token overhead.

---

# Phase 27 — Efficient local inference — PLANNED

Measure model-load time, peak memory, generation latency, P50/P95, tokens/second, structured-output validity, and grounding preservation. Hardware-specific claims require measurements on that hardware.

---

# Phase 28 — Multimodal technical reports — FUTURE

Potential work: figure detection/captions, table extraction, page linkage, image/table retrieval, citations, multimodal evaluation, OCR fallback.

---

# Phase 29 — Evaluation maturity — ONGOING

Completed: retrieval evaluation, generation evaluation, protected benchmark, local-model baseline, LoRA benchmark, negative-result preservation, failure categorization, regression tests, provider telemetry, backend comparison, four-way system evaluation, raw vs normalized contract analysis.

Current: semantic expected-concept evaluation, claim-evidence entailment, unsupported-response taxonomy, answer-to-claim completeness, targeted human review.

---

# Phase 30 — Releases and reproducibility — ONGOING

Repository history preserves retrieval/generation baselines, OpenAI reference, local Qwen baseline, pgvector comparison, LoRA training, failed LoRA evaluation, failure diagnosis, structured-output hardening, Base+RAG / LoRA+RAG evaluation, raw closed-book v0.1, canonical-refusal normalization, normalized closed-book v0.2, and the corrected four-way study.

---

# Explicit non-priorities

The project will not add technologies purely for stack breadth. Current non-priorities include Kubernetes, Redis, additional vector databases, unrestricted autonomous agents, reinforcement learning without a measured need, HNSW at the current corpus scale, multiple orchestration frameworks, additional cloud providers, speculative hardware optimization, and frontend redesign.

---

# Immediate next milestone

> **Does LoRA's increase in formal technical claims correspond to better semantic coverage and stronger evidence support?**

```text
freeze corrected four-way results
→ semantic expected-concept evaluation
→ claim-evidence entailment
→ answer-to-claim completeness
→ unsupported-response taxonomy
→ targeted human audit
→ freeze semantic evaluation baseline
→ begin bounded adaptive retrieval
```
