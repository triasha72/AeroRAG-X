# AeroRAG-X

[![CI](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml/badge.svg)](https://github.com/triasha72/AeroRAG-X/actions/workflows/ci.yml)

A production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is built around a curated NASA Technical Reports Server (NTRS) corpus. It combines reproducible document acquisition, citation-preserving processing, lexical and semantic retrieval, reciprocal-rank fusion, cross-encoder reranking, deterministic facet-aware evidence selection, evidence-sufficiency gating, hardened structured LLM generation, claim-level citation resolution, and benchmarked provider telemetry.

Every generated claim is tied back to retrieved evidence whose document ID, page range, NASA citation URL, source URL, and source-document checksum are preserved through the pipeline.

---

## Current status

AeroRAG-X now implements an end-to-end text RAG pipeline:

```text
NASA NTRS metadata
        |
        v
Versioned corpus manifest
        |
        v
PDF acquisition + checksum validation
        |
        v
Page-level text extraction
        |
        v
Citation-preserving overlapping chunks
        |
        +-------------------------+
        |                         |
        v                         v
BM25 lexical retrieval     Dense semantic retrieval
        |                         |
        +------------+------------+
                     |
                     v
           Reciprocal Rank Fusion
                     |
                     v
            Hybrid candidates
                     |
                     v
         Cross-encoder reranking
                     |
                     v
      Optional facet-aware retrieval
                     |
                     v
        Evidence-sufficiency gate
                     |
          +----------+----------+
          |                     |
          v                     v
   sufficient evidence    insufficient evidence
          |                     |
          v                     v
 Structured LLM provider   grounded refusal
          |
          v
  Prompt/response guardrails
          |
          v
 Claim-level citation resolution
          |
          v
 Source-document summaries
          |
          v
 Evaluation + provider telemetry
```

The current text corpus contains **3,233 citation-preserving NASA report chunks**.

### Implemented capabilities

- NASA NTRS metadata search
- reproducible corpus configuration
- versioned document manifests
- streamed PDF acquisition
- checksum validation and acquisition receipts
- page-level PDF extraction
- citation-preserving overlapping chunks
- BM25 lexical retrieval
- Sentence Transformer dense retrieval
- persistent NumPy embedding indexes
- exact cosine-similarity dense search
- reciprocal-rank-fusion hybrid retrieval
- cross-encoder reranking
- preserved BM25, dense, hybrid, and reranker provenance
- pooled retrieval evaluation
- deterministic facet-aware evidence retrieval for supported synthesis patterns
- deterministic evidence-sufficiency assessment
- morphology-aware query normalization
- numeric-support checks
- named-anchor checks
- claim-qualifier checks
- insufficient-evidence refusal before provider invocation
- provider-agnostic generation interface
- deterministic local generation provider
- OpenAI Responses API structured provider adapter
- versioned provider configuration
- prompt versioning and evidence delimiters
- prompt-injection heuristics
- structured provider-response validation
- retry and timeout handling
- token, latency, retry, and estimated-cost telemetry
- authoritative application-side citation resolution
- claim, citation, source-document, and answer schemas
- generation v0.3 benchmark with 32 labeled queries
- Typer command-line interface
- Ruff, pytest, strict mypy, coverage, and GitHub Actions

---

## Generation v0.3 final benchmark

The final benchmark contains:

```text
20 expected-answerable queries
12 unsupported queries
32 total queries
```

The final system uses:

```text
Sufficiency v0.2.1
+
Facet Retrieval v0.1
+
OpenAI Responses API provider
```

### Final generation results

| Metric | Baseline | Final |
|---|---:|---:|
| Answerability accuracy | 0.9375 | **1.0000** |
| Answerable completion | 0.9000 | **1.0000** |
| Unsupported refusal | 1.0000 | **1.0000** |
| Claim citation coverage | 1.0000 | **1.0000** |
| Citation-reference validity | 1.0000 | **1.0000** |
| Expected-term recall | 0.9138 | **0.9310** |
| Structural validity | 1.0000 | **1.0000** |

### Provider-routing results

| Metric | Baseline | Final |
|---|---:|---:|
| Provider calls | 22 | **20** |
| Provider bypasses | 10 | **12** |
| Provider call-policy accuracy | 0.8750 | **1.0000** |
| Total tokens | 63,638 | **58,915** |
| Estimated benchmark cost | $0.105733 | **$0.103745** |

Final measured latency:

```text
P50 provider latency: 5.6394 s
P95 provider latency: 7.6947 s
Provider retry rate: 0.0
```

The final benchmark produced **zero answerability failures**.

These results are an engineering benchmark over the current 32-query dataset, not evidence of general-purpose RAG correctness or universal answer faithfulness.

Tracked reports:

```text
artifacts/evaluation/generation_deterministic_v0_3.json
artifacts/evaluation/generation_deterministic_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3.json
artifacts/evaluation/generation_openai_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3_final.json
artifacts/evaluation/generation_openai_v0_3_final_telemetry.json
artifacts/evaluation/generation_v0_3_final_comparison.json
```

---

## Why the final generation system changed

The v0.3 benchmark exposed several concrete failure modes.

### 1. Lexical sufficiency false refusal

A legitimate cryogenic-hydrogen question was rejected because surface-form differences such as `storing` versus `storage` reduced query-term coverage.

Resolution:

- morphology-aware deterministic normalization
- stopword calibration
- preservation of strict numeric/entity checks

### 2. Unsupported universal or regulatory claims

Some unsupported questions contained real NASA/FAA terms and relevant technical vocabulary, causing the original sufficiency gate to overestimate evidence support.

Resolution:

- claim-qualifier detection
- explicit support requirements for terms such as universal mandates, assigned values, and issued certificates

### 3. Technical compounds misclassified as named entities

Ordinary lowercase compounds such as `power-electronics` and `thermal-management` were initially treated as mandatory named anchors.

Resolution:

- named-anchor calibration
- lowercase technical compounds remain ordinary terminology
- acronyms, CamelCase names, and uppercase/digit-bearing identifiers remain protected anchors

### 4. Multi-facet retrieval failure

The query:

```text
What thermal-management challenges are shared by
battery-electric and fuel-cell aircraft?
```

passed the sufficiency gate but the original top-five evidence did not contain enough fuel-cell-specific material.

Resolution:

- deterministic facet planning for supported synthesis patterns
- facet-specific searches
- semantic facet verification
- deduplication
- quota-aware balanced evidence selection
- fallback to ordinary retrieval when a facet cannot be supported

This allowed the provider to answer the synthesis query with evidence from both battery-electric and fuel-cell sources.

---

## Retrieval benchmarks

### Retrieval benchmark v0.1

The original benchmark contains eight aerospace queries and relevance judgments selected from a BM25-generated candidate pool.

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.7500 | 0.9167 | 0.6771 | 0.7046 |
| Dense | 0.2292 | 0.3958 | 0.3376 | 0.2812 |

Because the v0.1 judgments were created from BM25 candidates only, this comparison can favor BM25.

### Pooled retrieval benchmark v0.2

The v0.2 benchmark pools BM25 and dense candidates before relevance assessment.

| Property | Value |
|---|---:|
| Evaluation queries | 8 |
| BM25 depth per query | 20 |
| Dense depth per query | 20 |
| Candidates after deduplication | 278 |
| Relevant labels | 101 |
| Non-relevant labels | 177 |
| Shuffle seed | 42 |
| Corpus size | 3,233 chunks |

| Retriever | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.2662 | 0.4016 | 0.7292 | 0.5321 |
| Dense | 0.1330 | 0.2778 | 0.5521 | 0.3976 |
| Hybrid RRF | 0.2043 | 0.3024 | 0.7639 | 0.4777 |
| Reranker top-10 | 0.2087 | 0.3024 | 0.7188 | 0.4614 |
| Reranker top-20 | 0.2068 | 0.3375 | 0.8375 | 0.5080 |

The fixed top-20 cross-encoder baseline achieves the highest current MRR@10 and NDCG@10. BM25 retains the highest Recall@5 and Recall@10 on this small benchmark.

Current reranker:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Current scoring-only CPU latency baseline:

| Field | Value |
|---|---:|
| Queries | 8 |
| Query-chunk pairs | 160 |
| Total scoring seconds | 3.170787 |
| Milliseconds per pair | 19.817420 |
| Hardware | MacBook Air, CPU baseline |

---

## Evidence-sufficiency gate

Primary implementation:

```text
src/aeroragx/generation/sufficiency.py
```

Current production benchmark configuration:

```text
configs/sufficiency_v0_2_1.yaml
```

The gate evaluates retrieved evidence before provider invocation.

It checks:

- minimum evidence count
- informative query-term coverage
- minimum supported terms
- single-evidence coverage
- numeric support
- named-anchor support
- claim-qualifier support
- stricter coverage for exact-value questions

Representative rejection reasons:

```text
insufficient_evidence_count
no_informative_query_terms
insufficient_supported_terms
low_query_term_coverage
low_single_evidence_coverage
missing_numeric_support
missing_named_anchor_support
missing_claim_qualifier_support
```

The full decision is stored in retrieval metadata so pre-provider refusals remain auditable.

---

## Facet-aware retrieval

Primary implementation:

```text
src/aeroragx/generation/facet_retrieval.py
```

Configuration:

```text
configs/facet_retrieval_v0_1.yaml
```

Facet-aware retrieval is conservative and optional.

Normal questions continue through ordinary reranked retrieval.

For recognized multi-facet synthesis patterns, the wrapper:

1. derives deterministic facet searches;
2. retrieves evidence for each facet;
3. verifies that selected chunks actually contain the facet identity terms;
4. deduplicates by `chunk_id`;
5. balances evidence across supported facets;
6. adds original-query evidence;
7. falls back to ordinary retrieval if semantic facet support is unavailable.

The current implementation is intentionally narrow rather than a general query-planning agent.

---

## Hardened provider layer

The production benchmark uses the OpenAI Responses API through a structured provider adapter.

Generation configuration:

```text
configs/generation_openai_v0_1.yaml
```

Current configured model:

```text
gpt-5.6-luna
```

Provider-hardening configuration:

```text
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml
```

Provider controls include:

- versioned prompt configuration
- explicit evidence delimiters
- prompt-injection heuristics
- response-schema enforcement
- bounded retries
- timeout handling
- retryable versus non-retryable transport errors
- secret redaction
- request IDs
- latency measurement
- input/output token accounting
- estimated cost accounting

Retrieved evidence is treated as untrusted input. The provider is not trusted to create authoritative citation metadata.

---

## Citation trust boundary

A provider can return:

```text
claim -> evidence ID
```

The application resolves each evidence ID to the authoritative retrieved record.

The resulting citation preserves:

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

Unknown evidence references are rejected rather than silently accepted.

---

## Installation

AeroRAG-X requires Python 3.12 or newer.

```bash
git clone https://github.com/triasha72/AeroRAG-X.git
cd AeroRAG-X

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Conda is also supported:

```bash
conda create -n aeroragx-py312 python=3.12
conda activate aeroragx-py312
python -m pip install -e ".[dev]"
```

Check the CLI:

```bash
aeroragx --help
```

---

## Important CLI workflows

### Cross-encoder reranking

```bash
aeroragx ntrs-reranker-search \
  --query "battery thermal runaway" \
  --candidate-top-k 20 \
  --top-k 10
```

### Deterministic grounded answer

```bash
aeroragx ntrs-grounded-answer \
  --query "How can battery thermal runaway propagate in electric aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_2_1.yaml
```

### OpenAI grounded answer with facet-aware retrieval

Set the API key in your environment without committing it:

```bash
export OPENAI_API_KEY="..."
```

Then:

```bash
aeroragx ntrs-grounded-answer \
  --query "What thermal-management challenges are shared by battery-electric and fuel-cell aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_openai_v0_1.yaml \
  --provider-config configs/provider_v0_1.yaml \
  --http-transport-config configs/http_transport_openai_v0_1.yaml \
  --provider-runtime-config configs/provider_runtime_openai_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_2_1.yaml \
  --facet-retrieval-config configs/facet_retrieval_v0_1.yaml
```

Clear the shell variable after use:

```bash
unset OPENAI_API_KEY
```

### Reproduce generation v0.3

```bash
python scripts/run_generation_v03.py \
  --queries-input data/evaluation/generation_queries_v0_3.jsonl \
  --generation-config configs/generation_openai_v0_1.yaml \
  --provider-config configs/provider_v0_1.yaml \
  --http-transport-config configs/http_transport_openai_v0_1.yaml \
  --provider-runtime-config configs/provider_runtime_openai_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_2_1.yaml \
  --facet-retrieval-config configs/facet_retrieval_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_openai_v0_3_final.json \
  --telemetry-output artifacts/evaluation/generation_openai_v0_3_final_telemetry.json
```

This command uses the remote provider and therefore incurs provider usage.

---

## Validation

Run the local quality gate:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy src/aeroragx
git diff --check
```

Provider-hardening regressions:

```bash
python -m pytest \
  tests/test_generation_guardrails.py \
  tests/test_structured_provider.py \
  -v
```

---

## Repository structure

```text
AeroRAG-X/
├── artifacts/
│   ├── embeddings/
│   └── evaluation/
├── configs/
│   ├── bm25_v0_1.yaml
│   ├── dense_v0_1.yaml
│   ├── hybrid_v0_1.yaml
│   ├── reranker_v0_1.yaml
│   ├── generation_v0_1.yaml
│   ├── generation_openai_v0_1.yaml
│   ├── sufficiency_v0_2_1.yaml
│   ├── facet_retrieval_v0_1.yaml
│   ├── provider_v0_1.yaml
│   ├── http_transport_openai_v0_1.yaml
│   └── provider_runtime_openai_v0_1.yaml
├── data/
│   ├── evaluation/
│   └── processed/
├── docs/
│   ├── architecture.md
│   ├── generation.md
│   └── evaluation.md
├── scripts/
│   └── run_generation_v03.py
├── src/aeroragx/
│   ├── evaluation/
│   ├── generation/
│   ├── ingestion/
│   ├── processing/
│   └── retrieval/
└── tests/
```

---

## Current limitations

AeroRAG-X is not yet a complete production service.

Current limitations include:

- the generation benchmark contains 32 labeled queries and needs broader independent evaluation;
- expected-term recall is a lexical heuristic, not semantic faithfulness;
- no external entailment or claim-support judge is currently used;
- facet-aware retrieval intentionally supports a narrow deterministic synthesis pattern rather than arbitrary query decomposition;
- the current dense index uses local NumPy storage rather than a vector database;
- there is no FastAPI service yet;
- there is no Dockerized deployment yet;
- tables and figures are not yet first-class retrievable units;
- no cloud observability stack is deployed.

---

## Next milestone

The next milestone is **serving and deployment**, not another retrieval feature:

```text
FastAPI service
    ->
API tests
    ->
Docker
    ->
structured observability
    ->
cloud deployment
```

See `ROADMAP.md` for the full development plan.
