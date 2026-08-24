# AeroRAG-X

**An evaluation-first, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.**

AeroRAG-X is an independent engineering project built around public NASA Technical Reports Server (NTRS) material. It treats corpus construction, retrieval, reranking, grounding, generation, citations, model adaptation, distributed training, high-throughput serving, evaluation, and deployment as separately measurable engineering problems.

---

## Results at a glance

| Question | Measured result |
|---|---|
| Can the corpus preserve source identity? | Built 3,233 citation-preserving chunks with document, page, URL, and checksum provenance |
| Does grounding improve the reliability boundary? | Grounded Base and LoRA both reached 1.000 answerability, unsupported refusal, and citation coverage; closed-book answerability was 0.7812 and strict refusal was 0.4167 |
| What did LoRA change? | Expected-concept coverage rose from 38.16% to 51.32% and answer-to-claim capture from 10.00% to 45.00%; claim support remained similar and three contradicted claims remained |
| Did every policy help? | No. Adaptive retrieval reduced answerability from 91.67% to 83.33% and refusal from 83.33% to 66.67%, so the negative result was retained |
| Could a narrower safeguard help? | On a separate held-out set, the scope-qualifier safeguard raised answerability from 50.00% to 92.86% and refusal from 40.00% to 100.00% |
| Are the FSDP and vLLM studies complete? | The controlled trainers, serving transport, benchmark harnesses, and preregistered reports are implemented; CUDA measurements remain pending and are not presented as results |

These results come from different frozen experiments and are not pooled into a
single score. Their sample sizes, policies, and limitations remain in the
linked evaluation reports.

## System

```text
Hybrid retrieval → reranking → evidence gate → bounded agent → generation → validation
```

## Project origin

The idea for AeroRAG-X grew out of questions I became interested in while working on **HERO**, a Georgia Tech Grand Challenge project sponsored by **Delta Air Lines**.

AeroRAG-X developed from that interest as an independent project and is not a HERO or Delta Air Lines deliverable.

> **Can a language-model system help navigate aerospace technical literature while making provenance, evidence sufficiency, citations, model behavior, adaptation effects, and failure modes measurable?**

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
    L --> PL["vLLM OpenAI-compatible server"]

    M --> Q["Structured grounded response"]
    N --> Q
    O --> Q
    P --> Q
    PL --> Q

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

Closed-book Base and LoRA evaluation is implemented separately from the grounded RAG path so model adaptation can be studied without introducing artificial retrieval or citation fields.

---

# How the system works

## Corpus and provenance

- public NASA NTRS technical material
- **3,233 citation-preserving chunks**
- document identifiers
- page identifiers and page ranges
- source URLs
- NASA citation URLs
- source-document SHA-256 checksums
- reproducible manifests
- versioned processing artifacts

## Retrieval

- BM25 lexical retrieval
- `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- exact NumPy cosine retrieval
- PostgreSQL + pgvector
- runtime-selectable dense backends
- Reciprocal Rank Fusion
- `cross-encoder/ms-marco-MiniLM-L6-v2`
- deterministic facet-aware evidence retrieval
- bounded adaptive retrieval with preserved provenance
- opt-in LangGraph control and a LangChain retriever adapter

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
- scope-qualifier safeguard evaluated on a separately versioned held-out set

## Generation

Supported application runtime modes:

```text
local
openai
transformers
vllm
sglang
tensorrt-llm
```

Current local model:

```text
Qwen/Qwen3-0.6B
```

Transformers generation can run as:

```text
Base Qwen
Qwen + PEFT / LoRA adapter
```

An additional Apple-Silicon MLX-LM structured transport is available for controlled local low-bit experiments. It is intentionally separate from the application runtime selector until it has been compared against the established Transformers MPS baseline.

The vLLM transport implements the same structured generation contract as the
Transformers backend. Retrieval, RRF, cross-encoder reranking, evidence
sufficiency, prompt hardening, and response validation remain fixed, allowing a
controlled serving comparison instead of a different RAG pipeline. The serving
study measures concurrency 1, 8, 16, and 32 under normal and repeated
moderation-policy-prefix workloads. See
[`reports/vllm_serving_v0_1.md`](reports/vllm_serving_v0_1.md).

```bash
vllm serve Qwen/Qwen3-4B-Instruct-2507 --enable-prefix-caching

python scripts/benchmark_vllm_serving.py \
  --input data/evaluation/vllm_policy_prefix_v0_1.jsonl \
  --output artifacts/evaluation/vllm_serving_v0_1.json
```

## Distributed training

The matched training study compares the same Qwen assistant-only objective on a
single non-sharded GPU and two GPUs with PyTorch FSDP. It includes bf16 mixed
precision, gradient checkpointing, deterministic distributed samplers,
rank-aware seeds and metrics, full parameter/gradient/optimizer sharding,
sharded checkpoints, and resume-from-checkpoint.

```bash
# One-GPU control
python distributed_training/train_fsdp.py --no-fsdp

# Two-GPU treatment
torchrun --standalone --nproc_per_node=2 distributed_training/train_fsdp.py
```

The experiment records training and validation loss, tokens/s, samples/s, step
time, peak GPU memory per rank, checkpoint size/save time, and restart status.
Final parity means bounded protected-evaluation differences, not byte-identical
weights. The study design and pending result table are in
[`reports/fsdp_scaling_v0_1.md`](reports/fsdp_scaling_v0_1.md).

### Additional controlled framework treatments

DeepSpeed ZeRO-3 uses the same Transformers model, assistant-only tokenization,
train/dev split, and optimizer settings:

```bash
deepspeed --num_gpus 2 distributed_training/train_deepspeed.py
```

The Megatron-LM launcher validates a pinned upstream checkout and emits the full
tensor/sequence-parallel command before execution:

```bash
MEGATRON_LM_ROOT=/path/to/Megatron-LM \
  python distributed_training/launch_megatron.py
```

SGLang and TensorRT-LLM use their OpenAI-compatible servers behind the same
structured provider boundary as vLLM. Their configs live in `configs/`; the
retrieval, evidence, and output-validation path is unchanged. The controlled
comparison and hardware limits are recorded in
[`reports/framework_comparison_v0_1.md`](reports/framework_comparison_v0_1.md).
The remaining GPU, human-review, GRPO, and upstream steps are tracked with
evidence gates in the [manual completion checklist](docs/manual-completion-checklist.md).

## Serving and operations

- FastAPI
- Docker
- private Google Cloud Run Gen2 validation
- structured logging
- request IDs
- configurable request-size and process-local query-rate limits
- Prometheus
- OpenTelemetry
- provider latency telemetry
- token telemetry
- provider call/bypass telemetry
- adaptive-retrieval orchestrator metadata
- GitHub Actions CI
- frozen-evidence release-readiness checks

Deployment boundaries, rollback triggers, and pgvector backup/restore are documented in
[the release-readiness runbook](docs/release-readiness.md).

# Engineering principles

AeroRAG-X is organized around measurable questions.

1. Can the source corpus be reproduced?
2. Can every retrieved chunk preserve authoritative provenance?
3. Can lexical, dense, hybrid, and reranked retrieval be evaluated independently?
4. Can unsupported questions be rejected before model inference?
5. Can different language models use the same grounded interface?
6. Can citations remain application-controlled rather than model-authored?
7. Can invalid model outputs be detected instead of silently accepted?
8. Can negative experiments be preserved and diagnosed?
9. Can model-adaptation effects be separated from full-system effects?
10. Can evaluation distinguish semantic behavior from response-schema compliance?
11. Can future adaptive workflows remain bounded and observable?

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
negative-result preservation
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

Embedding dimension:

```text
384
```

Available dense backends:

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
- retrieval scores
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

pgvector is retained for requirements involving:

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

The gate therefore acts as both:

```text
grounding control
+
inference-cost control
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

This keeps citation authority on the application side.

---

# Local language-model generation

The primary local generation path uses `Qwen/Qwen3-0.6B` through Hugging Face Transformers.

The Transformers runtime supports:

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
- optional PEFT adapter loading
- token telemetry
- latency telemetry

The same Transformers transport is reused for the Base and LoRA conditions.

## Experimental Apple Silicon MLX transport

AeroRAG-X also includes an opt-in `MLXStructuredModelTransport` for Apple-Silicon local inference with MLX-LM.

- The optional `mlx` dependency extra is limited to macOS arm64.
- Qwen chat prompts are built with the model tokenizer and `enable_thinking: false`.
- Prompt and output budgets are validated before generation.
- Sampling is deterministic by default.
- The transport accepts only a JSON object (plain or fenced) and reports token usage.
- Generated content is not printed to stdout.
- Local MLX model artifacts remain untracked and ignored by Git.

The live smoke test used a local affine 4-bit Qwen3-0.6B MLX artifact with group size 128 and returned valid structured JSON plus usage telemetry.

The transport remains a provider-neutral benchmark foundation. It is not exposed as an application API or CLI runtime mode.

## Controlled MLX 4-bit versus Transformers MPS float16 comparison

Phase 34 compared the local MLX affine 4-bit, group-size-128 Qwen artifact with the established Transformers MPS float16 baseline on the same Apple-Silicon host. Both conditions used the same structured prompt and JSON schema, a 2,048-token input cap, a 96-token output cap, one warm-up iteration, and three measured iterations. Model construction and loading were excluded from per-request timing, and each backend was synchronized at timing boundaries.

| Runtime | Valid JSON | Mean latency | P50 latency | P95 latency | Output tok/s | Artifact size |
|---|---:|---:|---:|---:|---:|---:|
| Transformers MPS float16 | 3/3 | 715.11 ms | 699.42 ms | 742.58 ms | 39.15 | 1448.83 MiB |
| MLX affine 4-bit, group size 128 | 3/3 | 278.43 ms | 277.85 ms | 280.47 ms | 122.11 | 313.10 MiB |

The report records total token counts across measured iterations: 186 input and 84 output tokens for Transformers, and 423 input and 102 output tokens for MLX. Those totals reflect runtime-specific tokenization and returned lengths; they do not establish output-quality equivalence.

These are one-host local measurements, not Qualcomm QNN, Hexagon, or device-deployment measurements. Latency and throughput are not used as a quality claim. The full configuration, per-iteration samples, environment metadata, and interpretation limits are recorded in [the MLX/MPS comparison report](reports/mlx_mps_runtime_comparison_v0_1.md).

## Edge runtime benchmark

The completed Apple-Silicon benchmark uses a fixed structured-generation request with one warm-up iteration and three measured iterations per case. Model loading is excluded from per-request latency, and MPS work is synchronized at timing boundaries.

| Configuration | Mean latency | Output throughput |
|---|---:|---:|
| CPU float32 | 1189.29 ms | 23.54 tok/s |
| MPS float32 | 1015.00 ms | 27.59 tok/s |
| MPS float16 | **695.43 ms** | **40.26 tok/s** |
| LoRA MPS float16 | 1146.71 ms | 34.01 tok/s |

On this host, Base MPS float16 reduced mean latency by approximately 41.5% and raised output throughput by approximately 71.0% relative to Base CPU float32. The LoRA case produced more output tokens, so its raw latency is not an identical-workload comparison.

The complete methodology, samples, and limitations are recorded in [the edge-runtime benchmark report](docs/edge-runtime-benchmark-v0_1.md).

The controlled follow-on MLX comparison is complete and is documented in [the MLX/MPS comparison report](reports/mlx_mps_runtime_comparison_v0_1.md).

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

Best checkpoint:

```text
Epoch 2
```

The adapter weights remain local and are not committed to the repository.

---

# Why negative results are preserved

AeroRAG-X keeps failed experiments when they expose meaningful system behavior.

The first full LoRA + RAG evaluation exposed:

```text
truncated JSON
supported response without formal claims
duplicate evidence references
```

Those failures were reproduced rather than discarded.

The investigation led to:

- a larger but still bounded output budget
- explicit complete-JSON instructions
- more concise structured-output guidance
- explicit claim requirements
- evidence-reference uniqueness guidance
- deterministic duplicate-reference normalization
- regression testing of unknown evidence IDs

The first closed-book Base study exposed a different issue.

Five responses were initially classified as response-validation failures. Raw-payload inspection showed:

```text
4 canonical refusals
+ explanatory claims

1 canonical refusal
+ missing insufficient_knowledge field
```

A narrow normalization layer was introduced for the corrected v0.2 evaluation.

Only the exact canonical refusal representation is normalized.

The original v0.1 artifacts remain preserved as raw response-contract-compliance evidence.

These experiments reinforce:

```text
training success
!=
system reliability
```

and:

```text
semantic behavior
!=
response-schema compliance
```

---

# Protected evaluation set

The current controlled generation benchmark contains:

```text
32 queries

20 expected-answerable
12 unsupported controls
```

The protected set remains separated from LoRA training.

The four-way study uses the same question set for:

```text
Base closed-book
LoRA closed-book
Base + grounded RAG
LoRA + grounded RAG
```

The grounded conditions additionally include retrieval, reranking, evidence sufficiency, grounded prompting, evidence references, and citation validation.

Cross-system comparisons should therefore be interpreted as **system-level ablations**, not as the isolated effect of retrieval alone.

---

# Final Base + RAG vs LoRA + RAG

## Reliability

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

Formal-claim count increased by:

```text
65.625%
```

Across the 20 answerable questions:

```text
16 showed more formal claims with LoRA
2 showed fewer formal claims
2 were unchanged
```

This supports the narrower conclusion:

> **LoRA substantially increased structured technical decomposition on this benchmark while preserving the measured system-level reliability properties.**

---

# Corrected four-way Base / LoRA system study

The completed v0.2 study compares model adaptation with and without the full grounded evidence pipeline.

| Metric | Base closed-book | LoRA closed-book | Base + grounded RAG | LoRA + grounded RAG |
|---|---:|---:|---:|---:|
| Completed | 32 / 32 | 32 / 32 | 32 / 32 | 32 / 32 |
| Generation failures | 0 | 0 | 0 | 0 |
| Answerability accuracy | 0.7812 | 0.7812 | 1.0000 | 1.0000 |
| Answerable completion | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Strict unsupported refusal | 0.4167 | 0.4167 | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Formal answerable claims | 21 | 33 | 32 | 53 |
| Claims / answerable query | 1.050 | 1.650 | 1.600 | 2.650 |

## LoRA effect in closed-book generation

After canonical-refusal normalization, Base and LoRA have the same benchmark-level:

```text
completion
generation failures
answerability accuracy
strict refusal
expected-term recall
structural validity
```

The main measured difference is response decomposition:

```text
Base closed-book: 21 claims
LoRA closed-book: 33 claims
```

Increase:

```text
57.1%
```

This supports:

> **The LoRA adapter primarily increased structured technical decomposition rather than benchmark-level closed-book refusal behavior.**

## Grounded-system effect

Closed-book:

```text
answerability accuracy = 0.7812
strict unsupported refusal = 0.4167
```

Grounded RAG:

```text
answerability accuracy = 1.0000
strict unsupported refusal = 1.0000
```

The grounded condition includes:

```text
BM25
+
dense retrieval
+
RRF
+
cross-encoder reranking
+
facet-aware retrieval
+
evidence-sufficiency assessment
+
grounded structured generation
+
evidence-ID validation
+
citation resolution
```

The system-level conclusion is:

> **The grounded evidence pipeline provides a stronger unsupported-query reliability boundary than model adaptation alone on this protected benchmark.**

---

# Strict refusal versus semantic behavior

The strict refusal metric counts responses represented as:

```text
insufficient_knowledge = true
```

It is not a complete hallucination metric.

Some unsupported closed-book responses reject a false premise while still being represented as ordinary answers.

The semantic evaluation separates unsupported-query behavior into:

```text
EXPLICIT_REFUSAL
CORRECTIVE_DENIAL
UNSUPPORTED_ASSERTION
STRUCTURAL_FAILURE
```

---

# Query-level limitations

Aggregate metrics do not tell the entire story.

In the final Base + RAG versus LoRA + RAG comparison:

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

Increased response decomposition therefore does not guarantee improved concept coverage on every question.

The expected-term metric is a lexical coverage proxy rather than a semantic entailment metric.

The limitation is especially visible in the corrected four-way study:

```text
Base closed-book       0.9310
LoRA closed-book       0.9310
Base + grounded RAG    0.9310
LoRA + grounded RAG    0.9310
```

The systems behave differently, yet the lexical metric cannot distinguish them.

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

Longer output is not treated as automatically better.

---

# Evaluation philosophy

Retrieval, model behavior, grounding, and serving are evaluated separately wherever possible.

Current evaluation includes:

- Recall@5
- Recall@10
- MRR@10
- NDCG@10
- BM25 comparison
- dense retrieval comparison
- Hybrid RRF comparison
- reranker comparison
- NumPy / pgvector equivalence
- answerability
- unsupported controls
- grounded refusal
- strict closed-book refusal
- citation coverage
- citation-reference validity
- source-document coverage
- lexical expected-term recall
- formal claim decomposition
- structural validity
- generation-failure categories
- provider-call policy
- latency
- token usage
- external API cost
- raw response-contract analysis
- normalized behavioral evaluation
- controlled four-way model/system study

The completed semantic extension now includes:

- versioned semantic expected concepts
- hard-negative similarity calibration
- NLI-verifier calibration
- preservation of failed automatic matcher experiments
- frozen four-way expected-concept adjudication
- lower/upper semantic-coverage bounds

Claim-level evaluation also measures:

- claim-evidence entailment
- answer-to-claim completeness
- unsupported-response taxonomy
- redundancy
- targeted independent human audit

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

Start:

```bash
docker compose \
  -f docker-compose.vector.yml \
  up -d
```

Configure:

```bash
export AERORAGX_VECTOR_DATABASE_URL="postgresql://aeroragx:aeroragx@localhost:5432/aeroragx"
```

Load embeddings:

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

Local Transformers language-model support:

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

Apple-Silicon MLX structured-transport support (macOS arm64 only):

```bash
python -m pip install -e ".[dev,mlx]"
```

Complete local development environment on Apple Silicon:

```bash
python -m pip install -e ".[dev,vector,llm,training,agentic,mlx]"
```

The MLX extra does not download model weights. Real-model evaluations require a separately available local model artifact and remain opt-in.

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

# How the system was deployed

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

# What the experiments showed

Phase 24 semantic and claim-level evaluation is complete. On the protected grounded benchmark, LoRA + RAG increased conservative expected-concept coverage from **38.16%** to **51.32%** and full answer-to-claim capture from **10.00%** to **45.00%**, while strict claim-to-evidence support remained broadly similar (**65.62%** Base + RAG versus **67.92%** LoRA + RAG). The result remains qualified: LoRA also increased partial overlap and retained three contradicted claims under the frozen policy.

The frozen consolidated report is:

```text
reports/phase24_quality_v0_1.md
```

The bounded adaptive-retrieval implementation and protected paired evaluation are also complete. The evaluation recorded a negative result: the opt-in adaptive policy reduced answerability from **91.67%** to **83.33%** and unsupported refusal from **83.33%** to **66.67%** on the frozen Phase 26 comparison. That result is preserved rather than tuned away.

A separate opt-in scope-qualifier safeguard was then evaluated on its own held-out set. It improved answerability from **50.00%** to **92.86%** and unsupported-query refusal from **40.00%** to **100.00%**, without changing the protected Phase 26 data or policy.

The controlled MLX 4-bit versus Transformers MPS float16 comparison is complete.
Phase 35 now establishes a bounded multimodal-report foundation: page-linked
visual-asset provenance, checksum-verified whole-page rendering, a deterministic
render manifest, and deterministic independent-review tasks for the five-record
v0.1 slice.

The multimodal-report work stops at a provenance, rendering, and review-task
contract. It contains no independent review responses and therefore supports no
OCR, detection, retrieval, or model-quality conclusion.

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

<!-- phase35-review-evidence-v0_1 -->
# Bounded agent and distributed runtime

## Review-evidence gate

The multimodal foundation includes a strict complete-review
evidence gate. The existing raw agreement helper remains available for
shared-task analysis, but final review evidence requires both independent
reviewers to cover every frozen task exactly once before an agreement artifact
can be generated. No genuine independent review-response sets are included, so
the project makes no automatic figure or table detection claim.

<!-- phase36-agent-tool-contracts-v0_1 -->
## Agent-tool foundation

AeroRAG-X uses a typed tool boundary for agent execution. The
registry exposes hybrid retrieval, authoritative source-context lookup,
evidence-sufficiency assessment, deterministic citation validation, and
structured multi-source comparison. Explicit agent state budgets track graph
steps, tool calls, retrieval attempts, evidence identity, failures, and terminal
reasons. This keeps tool access auditable without treating the agent as
unrestricted automation.

<!-- phase37-stateful-agent-graph-v0_1 -->
## Stateful tool-using graph

A dynamically routed
LangGraph agent composes the bounded tool contracts. Planner decisions are schema-constrained, tools remain
explicitly registered, graph/tool budgets are enforced, and every run terminates
with an inspectable reason.

<!-- phase38-checkpointing-hitl-v0_1 -->
## Agent checkpointing and human review

Agent state is persisted as immutable checkpoints and can be resumed after a
bounded human-review interruption. Review decisions are explicit and the
pre-review state remains unchanged. The checkpoint store is a local development
implementation, not a distributed persistence system.

<!-- phase39-agent-failure-recovery-v0_1 -->
## Failure recovery

Explicit per-tool retry rules, deterministic fault injection,
and safe degradation for unrecoverable dependency failures. Retries are bounded;
dependency failure cannot be promoted into unsupported generation.

<!-- phase40-agent-trajectory-benchmark-v0_1 -->
## Trajectory evaluation

Typed frozen-case and observation contracts support deterministic
metrics for terminal correctness, required/forbidden tool behavior, budget
compliance, safe refusal, tool-call efficiency, and latency. The checked-in
cases are synthetic contract fixtures only; domain benchmark claims require a
separately curated frozen evaluation set and recorded runs.

<!-- phase41-service-contracts-v0_1 -->
## Service contracts

Typed Agent, Retrieval, and Inference service boundaries carry propagated
request, trace, and thread IDs with provenance-preserving evidence
records. Async clients validate network responses before they enter agent
state.

<!-- phase42-distributed-runtime-v0_1 -->
## Distributed runtime

The Agent API, Retrieval, and Inference services are separately containerized
with Docker Compose wiring, health endpoints,
typed async clients, and citation-preserving cross-service orchestration.
Unconfigured backends report not-ready rather than pretending to succeed.

<!-- phase43-distributed-reliability-v0_1 -->
## Distributed reliability

Cross-service operations use bounded async retries, OpenTelemetry context
propagation, Prometheus service-call metrics, and explicit safe degradation.
Required dependency failure returns no generated answer and no citations.

<!-- phase44-distributed-reliability-benchmark-v0_1 -->
## Reliability benchmark

A reproducible concurrent-request harness reports deterministic
metrics for latency, timeout, recovery, safe-refusal, and unsafe-answer behavior.
The checked-in report is intentionally a measurement template; results must
come from actual scenario runs.

<!-- phase45-grpo-reward-harness-v0_1 -->
## Grounded post-training contracts

Transparent multi-objective reward contracts cover grounded
post-training, anti-reward-hacking regression tests, and a hard disjoint-case
guard between training and frozen evaluation. The repository contains the
experiment harness only; no executed RL improvement result is claimed.

<!-- phase46-grpo-grounded-agent-v0_1 -->
## Tool-using GRPO environment

A stateful TRL-compatible environment exposes bounded
retrieve, sufficiency, submit, and refusal tools plus an explicit
validation-only training command. A Kaggle P100 notebook now runs the bounded
experiment with Pascal-compatible PyTorch and fp16 LoRA, saves resumable checkpoints, and writes a receipt
with configuration and data hashes; see [the Kaggle runbook](docs/KAGGLE_GRPO.md).
The checked-in training rows remain synthetic format fixtures, so no
model-improvement claim is made without a real run and held-out evaluation.
The [real-result protocol](docs/REAL_GRPO_RESULT.md) adds dataset-quality and
near-duplicate leakage checks, frozen split manifests, required model/adapter
metadata, and hash-bound measured reports.

<!-- phase47-grpo-agent-ablation-v0_1 -->
## Base, LoRA/SFT, and GRPO comparison contract

A controlled held-out ablation contract requires identical
case IDs across Base, LoRA/SFT, and GRPO variants. The report template tracks
task success, refusal, citations, evidence support, tool selection, efficiency,
and latency without assuming GRPO wins.

# License

MIT
