# AeroRAG-X

[Portfolio case study](https://triasha72.github.io/Portfolio/case-aerorag.html)

AeroRAG-X helps a reader navigate public NASA technical reports while keeping
the source trail visible. It is a retrieval-augmented generation system, but the
main engineering question is broader: when should the system answer, when should
it refuse, and can a reviewer trace each answer back to evidence?

## Project story

**Situation.** Aerospace reports are long, specialized, and spread across many
documents. A language model can summarize them quickly, but fluent text is not
useful if the evidence is missing or the citation points to the wrong source.

**Task.** I wanted to build a research assistant whose retrieval, grounding,
generation, adaptation, and serving choices could be evaluated separately.

**Action.** I assembled 3,233 citation-preserving chunks from public NASA NTRS
material, combined BM25 and dense retrieval, added reranking and an evidence
sufficiency gate, and required structured source IDs before citations are
resolved. I compared closed-book, grounded, Base, and LoRA conditions on frozen
queries and retained policy changes that made performance worse.

**Result.** Grounded Base and LoRA both reached `1.000` answerability,
unsupported-query refusal, and citation coverage on the reported benchmark.
LoRA increased expected-concept coverage from `38.16%` to `51.32%`, but three
contradicted claims remained. Adaptive retrieval also produced a negative
result, reducing answerability from `91.67%` to `83.33%`. CUDA serving and GRPO
results remain pending and are not inferred from the implemented harnesses.

---

## Results at a glance

| Question | Measured result |
|---|---|
| Can the corpus preserve source identity? | Built 3,233 citation-preserving chunks with document, page, URL, and checksum provenance |
| Does grounding improve the reliability boundary? | Grounded Base and LoRA both reached 1.000 answerability, unsupported refusal, and citation coverage; closed-book answerability was 0.7812 and strict refusal was 0.4167 |
| What did LoRA change? | Expected-concept coverage rose from 38.16% to 51.32% and answer-to-claim capture from 10.00% to 45.00%; claim support remained similar and three contradicted claims remained |
| Did every policy help? | No. Adaptive retrieval reduced answerability from 91.67% to 83.33% and refusal from 83.33% to 66.67%, so the negative result was retained |
| Could a narrower safeguard help? | On a separate held-out set, the scope-qualifier safeguard raised answerability from 50.00% to 92.86% and refusal from 40.00% to 100.00% |
| What happened as retrieval grew? | Real NASA-text BM25 measured Recall@10/NDCG@10 of 0.2275/0.2793 at 10K, 0.2136/0.2476 at 100K, and 0.0467/0.0721 in a 1M fine-segment load snapshot; the 1M result exposed rank crowding and is not a corpus-breadth claim |
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

# The engineering story

## The project did not begin with a model

AeroRAG-X began with a reliability problem, not a decision to use Qwen, LoRA,
or a vector database. Aerospace reports contain exact measurements, operating
conditions, qualifications, and conclusions whose meaning depends on their
source. A fluent answer is not enough if the system cannot show which NASA
document and page support it.

The first engineering question was therefore not *Which LLM should be used?*
It was *Can the source library be made reproducible and traceable?* The project
started with a deliberately bounded NASA NTRS domain instead of downloading all
of NTRS. A smaller corpus made it possible to inspect failures, annotate
retrieval results, and freeze repeatable experiments. Downloading everything
would have created more scale before there was evidence that the basic
retrieval and citation design worked.

The NTRS client collects document metadata and downloads available PDFs. Each
download receives a SHA-256 checksum. Text is extracted page by page and split
into overlapping chunks, but a chunk never becomes anonymous text: it retains
its document ID, page range, NASA URL, source URL, and source-file checksum. The
result was a reproducible library of 3,233 citation-preserving chunks. This
decision later made application-controlled citations possible; without
provenance at ingestion, citation repair at generation time would only be a
guess.

## Retrieval was built as a sequence of measured decisions

The next question was how to find the right passage. BM25 was selected first
because aerospace language contains exact identifiers and specialist terms
such as *thermal runaway*, *state of charge*, and program names. BM25 is strong
when the query and report use the same words, but it can miss paraphrases.

Dense retrieval with `all-MiniLM-L6-v2` was added to recover passages with
similar meaning but different wording. Dense retrieval alone was rejected as
the only search method because semantic similarity can overlook an exact
technical qualifier. The project therefore kept both and combined their ranks
with Reciprocal Rank Fusion. Raw-score addition was rejected because BM25 and
cosine-similarity scores do not share a meaningful numerical scale.

Fast retrieval creates candidates; it does not prove that the first candidate
is best. A cross-encoder was added to inspect the query and each candidate
together. Running that cross-encoder across the entire corpus was rejected as
unnecessarily expensive, so the design became a funnel: inexpensive retrieval
first, expensive reranking over a bounded pool second.

At 3,233 chunks, exact NumPy cosine search and pgvector returned identical top
10 results for all eight measured queries. NumPy was faster locally—7.121 ms
versus 20.517 ms—so NumPy remained the default. pgvector was retained because
transactions, persistence, filtering, and approximate indexes become valuable
as the corpus grows. This was a measured crossover decision, not a claim that
one backend is always superior.

## The system learned when not to call the LLM

Finding related text does not mean the text contains enough information to
answer. A retrieved passage might mention temperature without containing the
requested measurement. Sending weak evidence to a language model invites a
plausible completion.

For that reason, AeroRAG-X placed an evidence-sufficiency gate before
generation. The gate checks evidence amount, query coverage, anchors, numbers,
and qualifiers. If the evidence is insufficient, the system returns a grounded
refusal and does not call the model. This decision improved the reliability
boundary while also avoiding unnecessary inference.

A bounded adaptive-retrieval policy was tested as an alternative. The
hypothesis was that a deterministic query rewrite and a second retrieval pass
could recover missed evidence. The result was negative: answerability fell from
91.67% to 83.33%, unsupported refusal fell from 83.33% to 66.67%, and latency
increased. The policy was rejected and preserved as an `integrity_regression`
rather than hidden. The failure suggested that some questions needed a clearer
scope boundary, not more searching. A narrower scope-qualifier safeguard was
then evaluated separately and improved its held-out boundary results.

## Generation was intentionally made the last knowledge step

Only after retrieval and sufficiency were working was Qwen3-0.6B added. The
model is not expected to remember the NASA corpus. It receives the question and
a bounded set of evidence and converts them into a structured answer. A small
local model was chosen because retrieval supplies the facts, while local
inference offers privacy, cost control, and a tractable adaptation experiment.
A larger hosted model remains a valid alternative, but it would need to be
compared on grounding, refusal, cost, and latency rather than assumed better.

The model returns claims linked to evidence IDs such as `E1`; it does not write
authoritative NASA citations. The application resolves each ID back to the
trusted chunk record. Allowing the model to invent URLs, page numbers, or report
identifiers was rejected because language models can produce convincing but
nonexistent citations. Output JSON, evidence IDs, duplicates, and required
fields are validated before the response is accepted.

## LoRA answered a narrower research question

LoRA was not introduced to store NASA facts in the model. It tested whether a
small adapter could improve structured technical decomposition while the RAG
pipeline continued to control factual reliability. The matched experiment used
Qwen3-0.6B, 106 training examples, 12 development examples, and a rank-16 LoRA
adapter; epoch 2 produced the selected checkpoint.

Grounded Base and grounded LoRA both reached 1.000 answerability, unsupported
refusal, citation coverage, citation validity, and structural validity on the
protected 32-query study. LoRA's measurable effect was different: it produced
53 formal claims compared with Base's 32. That added decomposition also raised
output tokens from 3,314 to 5,182 and p50 provider latency from 8.88 seconds to
14.87 seconds.

The project therefore does not claim that LoRA made the system factual. The
evidence supports a narrower conclusion: grounding supplied the measured
reliability boundary, while LoRA changed answer structure and granularity.

## Token reduction followed the measurements

Base + RAG and LoRA + RAG used the same 51,289 input tokens in the protected
comparison. The LoRA-specific cost increase was therefore not caused by
retrieved context; it came from longer output. Reducing evidence from five
passages to one was rejected as the first optimization because it would save
input tokens by weakening the part of the system responsible for grounding.
Sharply reducing `max_new_tokens` was also rejected because incomplete JSON had
already been observed as a failure mode.

The first controlled change reduced `max_claims` from six to four. It directly
targeted measured verbosity while preserving retrieval coverage and enough
generation space to close the structured response. The completed protected
rerun showed that this constraint alone is not sufficient: LoRA still averaged
212.25 output tokens per provider call versus 142.48 for Base and produced 44
claims versus 26. It remains a safety bound, not the complete token solution.

The context budget no longer has to rely on the stored character-derived token
estimate when Transformers or MLX is the provider. The structured provider now
exposes the exact runtime tokenizer, evidence is truncated against it, and
each evidence record reports whether its count came from `runtime_tokenizer` or
`stored_estimate`. The pinned Qwen weights are now local with SHA-256
`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`,
and the missing adapter has now been reconstructed by the full three-epoch MPS
treatment. Epoch 2 was selected by development loss, the saved adapter reloaded
with a zero loss difference, and its SHA-256 is
`13df5eb8449d5b204c2d740b0c194b7712969f15258c42b26a336febeb27c717`.

The first protected validation attempt revealed a different systems problem.
The 16-GB Apple-Silicon host held the dense encoder, cross-encoder reranker, and
Qwen generator in unified memory at once; macOS killed the process with signal
9 (exit 137) after every artifact-integrity gate had passed. Reducing the query
set, replacing the model, or lowering the scientific token limits was rejected
because each would change the promised comparison. Moving the whole run to CPU
was rejected for the same reason: this milestone is the original MPS treatment.

The selected fix changes scheduling, not the experiment. The validation runner
now retrieves and reranks all 32 frozen queries first, holds their exact top-five
hits in a closed in-memory index, releases both retrieval models and the MPS
cache, and only then loads Qwen. Base and LoRA still run in separate processes
with the same corpus, queries, candidate top-k, evidence top-k, tokenizer,
prompts, and generation limits. This lowers peak unified memory while making the
retrieval boundary explicit and reproducible. The fail-closed
`scripts/run_original_mps_claim4_validation_only.sh` performs this validation
without retraining or accepting stale reports. It completed on August 31, 2026;
the checksummed results are in
[`reports/claim4_actual_checkpoint_validation_v0_1.md`](reports/claim4_actual_checkpoint_validation_v0_1.md).

## Scaling preserves the same reliability boundary

Growing the library must not mean sending thousands of passages to the model.
The scaling design keeps corpus size and prompt size independent:

```text
10K / 100K / 1M indexed chunks
          ↓
100 retrieval candidates
          ↓
20 cross-encoder candidates
          ↓
overlap removal + document diversity
          ↓
at most 5 evidence passages
          ↓
bounded LoRA generation
```

Evaluation scale now has two deliberately separate layers. The 32-query set
remains the protected generation-quality benchmark. A new source-grounded set
contains 512 distinct chunk-recovery cases across all 94 frozen NASA documents,
with source pages, qrels, checksums, and a 512-row independent-review template.
Its actual exact-BM25 run achieved Recall@10 1.0000, NDCG@10 0.9764, 1.066 ms
P50, and 1.330 ms P95 over 3,233 chunks. Because its query terms were selected
from the relevant chunks, this is honestly reported as a lexical retrieval/load
diagnostic—not evidence of natural-question or generation quality. See
[`reports/source_grounded_eval_512_v0_1.md`](reports/source_grounded_eval_512_v0_1.md).

`scripts/finalize_source_grounded_eval_512.py` enforces promotion: two distinct
reviewers must cover every case, all decisions must agree or be adjudicated,
fields and decisions must be internally consistent, and at least 500 cases must
be accepted. Until then, the manifest keeps the set labeled as a candidate.

All 512 cases have also completed the frozen neural retrieval stack. Dense
retrieval reached Recall@10 0.3262/NDCG@10 0.2124; Hybrid RRF reached
0.6523/0.4550; and the cross-encoder reranker reached 0.9355/0.8385 after
scoring 10,240 pairs. These are complete source-recovery measurements, while the
human-review limitation remains unchanged.

The pgvector path now supports HNSW for approximate search. Exact NumPy remains
the small-corpus control. Checksum-based incremental updates reuse embeddings
for unchanged chunks and encode only added or changed material. Overlapping
passages are removed before prompting, and no more than two final passages may
come from one document. These choices reduce redundant computation without
creating new evidence.

The 10K, 100K, and 1M snapshot harness records Recall@10, NDCG@10, p50/p95
latency, and a report checksum. Synthetic distractor replication was considered
and rejected for the reported milestones: duplicated text could create a large
file, but it would not establish behavior on real technical language. HNSW
becomes the default only after a measured quality/latency crossover; its
presence in configuration is not itself evidence that it is better.

On the eight frozen retrieval queries and `qrels_v0_2`, exact BM25 produced the
following real-text checkpoints:

| Snapshot | Construction | Recall@10 | NDCG@10 | p50 | p95 |
|---|---|---:|---:|---:|---:|
| 10,060 | 358 unique NASA PDFs, page-linked chunks | 0.2275 | 0.2793 | 7.05 ms | 11.39 ms |
| 100,614 | broader real NTRS collection, frozen prefix | 0.2136 | 0.2476 | 31.63 ms | 71.15 ms |
| 1,000,000 | 32-word segments from the real 100K text snapshot | 0.0467 | 0.0721 | 32.93 ms | 106.15 ms |

The 100K result is the corpus-breadth checkpoint. Its moderate quality decline
and larger tail latency justify metadata filtering, bounded candidate pools,
and reranking before adopting ANN as a default. The 1M result answers a
different question: what happens when one million fine-grained, overlapping
real-text segments compete for ten ranks? It is a load-scale experiment, not a
claim of broader source coverage. Its sharp quality drop shows rank crowding:
multiple fragments from the same parent passage consume the top ten. That
failure makes parent-level deduplication and hierarchical retrieval measurable
requirements rather than speculative features.

That intervention has now been measured on the same 1M snapshot. Collapsing to
the best child segment per parent before top-10 selection raised Recall@10 from
0.0467 to 0.0650 and NDCG@10 from 0.0721 to 0.0903. The pure-Python exact
implementation also raised p50 latency from 32.99 ms to 55.46 ms and p95 from
108.12 ms to 170.78 ms. The policy is therefore enabled in hierarchical
evidence selection, but the benchmark implementation is not presented as a
production latency solution; index-native collapse remains necessary.

The metadata-filter contract now covers publication-year bounds, subject
categories, document type, program, and report family in addition to document,
checksum, and page constraints. A real 101,622-row audit found 100% document
coverage for year, subject category, document type, and report family, but only
66.64% document coverage for program metadata. Program filtering therefore
remains opt-in and must treat missing values as exclusion, not as evidence that
a report is outside a program.

The frozen hashes are `73dd8e735de70fcbb331bd63d2413391aef45ab60342ddaf2b5ef493b0a97efe`
for 10K, `7744c8a8f217710acb5ab32afaea3fde4846c623c6a20a6706d518bee25be3a5`
for the exact 100K prefix, and
`c4fbe18f16f316f9d5f220eccbb3a063d198eb14e940a3043eb7b752987f158e`
for the normalized 1M snapshot. These measurements do not claim dense, hybrid,
reranker, or HNSW quality.

Larger real snapshots are built with
`scripts/build_real_ntrs_scale_corpus.py`. The builder paginates NASA search,
deduplicates document IDs, downloads the authoritative PDF, records its SHA-256,
extracts page text, attaches NTRS metadata, writes chunks incrementally, and can
delete the local PDF after processing. Receipts make interrupted builds
resumable. Stream-and-delete was chosen for the breadth build because the
development machine had only 5.1 GiB free; retaining every source PDF and
float32 embedding would exceed that limit. When external breadth expansion
could not progress reliably, `scripts/build_real_segment_scale_snapshot.py`
created the 1M load snapshot as compact segments with parent references instead
of repeating full metadata. That preserved real source text and honest
provenance while staying within the storage constraint.

## What the project has established

The research story is cumulative. Provenance made trustworthy citations
possible. Hybrid retrieval improved the ways evidence could be found. Reranking
made the candidate order more precise. The sufficiency gate created a refusal
boundary. Application-side citation resolution removed citation authority from
the model. The four-way Base/LoRA and closed-book/grounded comparison separated
adaptation effects from system effects. Negative adaptive-retrieval results
prevented an appealing but harmful policy from being shipped. The new scaling
work preserves those decisions instead of replacing them with an unmeasured
large-corpus architecture.

The sections below provide the implementation details, commands, frozen
results, and limitations behind that story.

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

### Reducing LoRA + RAG token use

The Transformers generation config sets `max_claims: 4`, reduced from 6 as the
first controlled LoRA + RAG token optimization. The protected comparison showed
that Base + RAG and LoRA + RAG consumed the same 51,289 input tokens, so
retrieved context was not the source of the LoRA-specific increase. The
difference was in generation: LoRA produced 5,182 output tokens and 53 formal
claims, compared with 3,314 tokens and 32 claims for Base.

Reducing the claim ceiling directly targets that measured output verbosity while
preserving `evidence_top_k: 5`, the 12,000-character evidence budget, citation
validation, and refusal behavior. It is safer as a first step than discarding
retrieved evidence or sharply lowering `max_new_tokens`, which could weaken
grounding or truncate the required JSON response.

The protected 32-query rerun is complete. Four claims lowered LoRA aggregate
output from the historical 5,182 tokens to 4,245, but Base used only 2,992 in
the new run. Because Base completed 31 queries and LoRA completed 30, aggregate
totals are not an equal-call comparison. Per provider call, Base generated
142.48 output tokens and LoRA generated 212.25. Citation coverage and validity
remained 1.0, while LoRA had more failures and lower answerability,
expected-term recall, and structural validity. Four claims therefore remains an
upper bound; the next optimization targets response-schema verbosity on matched
successful queries rather than removing evidence.

### Scaling to larger corpora

Corpus growth is kept separate from prompt growth. The large-corpus funnel is
configured in `configs/retrieval_scale_v0_1.yaml` as 100 retrieval candidates,
20 reranked candidates, and at most 5 evidence passages. The final selection
removes highly overlapping passages and permits at most two chunks from one
document, preventing one long report from crowding out other relevant sources.
The Transformers generation config additionally enforces a 3,000-token
estimated context ceiling and a 750-token per-passage ceiling.

`aeroragx.retrieval.scaling` provides the shared scaling controls:

- authoritative document/checksum/page metadata filtering;
- document-first, child-chunk evidence diversity;
- word-shingle overlap deduplication before prompting;
- exact-token truncation when supplied with the active tokenizer's counter;
- checksum-based incremental index plans that re-embed only added or changed
  documents and identify deleted documents;
- frozen Recall@K, NDCG@K, p50, and p95 scale measurements with a report
  checksum.

The pgvector configuration now uses an HNSW cosine index (`m: 16`,
`ef_construction: 64`, `ef_search: 40`) for approximate nearest-neighbor search.
These values are starting points, not universal optima. Run the scale harness at
10K, 100K, and 1M chunks and compare it with exact NumPy retrieval before
choosing the crossover point:

```bash
python scripts/benchmark_retrieval_scale.py \
  --queries data/evaluation/queries_v0_1.jsonl \
  --qrels data/evaluation/qrels_v0_2.jsonl \
  --results artifacts/evaluation/retrieval_results_100k.json \
  --corpus-chunks 100000 \
  --output artifacts/evaluation/retrieval_scale_100k.json
```

Scale acceptance requires retrieval quality to remain inside the frozen
tolerance while latency and memory improve. Increasing the corpus must not
increase the five-passage generation boundary. Subject, year, program, and
document-type filters should be added to chunk metadata when those fields are
available in the ingestion manifest; checksum and document/page filters work
with the current corpus schema.

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
The post-merge research program now also pins two external NASA IMPACT
benchmarks and separates their evidentiary roles: 219 expert queries can test
independent NASA software-discovery generalization, while the 176,901-query SDE
benchmark can test scale but remains model-generated evidence. Acquisition,
reviewer alternatives, the pgvector execution receipt, claim audit, and release
gate are documented in
[`docs/post_merge_evidence_plan.md`](docs/post_merge_evidence_plan.md). Public
numbers are mapped for independent verification in
[`docs/public_claim_audit_v0_1.csv`](docs/public_claim_audit_v0_1.csv).

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

# Original six-claim runtime trade-off (historical baseline)

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

## Actual four-claim checkpoint validation

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Frozen queries | 32 | 32 |
| Completed queries | 31 | 30 |
| Generation failures | 1 | 2 |
| Answerability accuracy | 0.9063 | 0.8750 |
| Expected-term recall | 0.8966 | 0.8448 |
| Structural validity | 0.9688 | 0.9375 |
| Citation coverage / validity | 1.0000 / 1.0000 | 1.0000 / 1.0000 |
| Provider input tokens | 47,339 | 45,443 |
| Provider output tokens | 2,992 | 4,245 |
| Mean output tokens per call | 142.48 | 212.25 |
| Total provider tokens | 50,331 | 49,688 |

The 643-token aggregate difference is not evidence that LoRA is cheaper: LoRA
made one fewer successful provider call and had one additional failure. On the
fairer per-call output measure, LoRA used about 49.0% more output tokens.

The follow-up paired analysis removes that failure-count confound. Among 19
queries with token-observed provider calls in both conditions, LoRA averaged
210.89 output tokens versus Base's 140.89: exactly +70 tokens, or +49.68%.
LoRA was longer on 16 of 19 paired calls and its mean repeated-word fraction was
0.2748 versus 0.1184. The checksummed analysis is generated by
`scripts/analyze_paired_generation_efficiency.py` and recorded in
[`reports/generation_claim4_paired_efficiency_v0_1.md`](reports/generation_claim4_paired_efficiency_v0_1.md).

This evidence motivated `grounded-json-v0.3-compact`. The candidate removes the
duplicated schema from the user payload, serializes evidence JSON compactly,
requires a one-sentence answer and short non-overlapping claims, and lowers the
generation safety ceiling from 512 to 384 tokens—still above the largest
successful LoRA output observed in v0.1 (294 tokens). An exact pinned-Qwen
tokenizer check on a representative five-evidence prompt reduced input from
1,597 to 1,469 tokens (128 tokens, 8.02%) without dropping evidence. This is an
implemented prompt-budget result, not yet a generation-quality result. The full
32-query Base/LoRA candidate is run with
`scripts/run_compact_mps_claim4_validation.sh`; it writes new artifacts and
cannot overwrite the historical checkpoint reports.

The runner also compares compact LoRA directly with original LoRA on matched
successful calls and invokes a fail-closed promotion gate. Promotion requires
at least 15 paired calls, at least 15% output-token reduction, no additional
generation failures, the same 32-query contract, and no quality-rate regression
greater than one query out of 32. Saving tokens by failing or refusing more
often is therefore rejected.

Local failure telemetry is bounded but actionable. It records the failure
stage, output-token count, whether the ceiling was reached, JSON error position,
output character count, and a SHA-256 fingerprint. Raw generated text and
prompts are not copied into telemetry, avoiding a new sensitive-data sink.

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
