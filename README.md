AeroRAG-X



A production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

AeroRAG-X is built around a curated NASA Technical Reports Server (NTRS) corpus. It combines reproducible document acquisition, citation-preserving processing, lexical and semantic retrieval, Reciprocal Rank Fusion, cross-encoder reranking, deterministic facet-aware evidence selection, evidence-sufficiency gating, hardened structured generation, authoritative claim-level citation resolution, provider telemetry, and a FastAPI serving layer.

Every generated claim is tied back to retrieved evidence whose document ID, page range, NASA citation URL, source URL, and source-document checksum are preserved through the pipeline.

Current status

AeroRAG-X implements an end-to-end text RAG system with both CLI and HTTP interfaces.

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
 Structured provider       grounded refusal
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
 Retrieval + provider telemetry
          |
          v
      Shared RAG runtime
          |
          +------------------+
          |                  |
          v                  v
        Typer              FastAPI
         CLI          /health /ready /v1/query

The current text corpus contains 3,233 citation-preserving NASA report chunks.

Implemented capabilities

NASA NTRS metadata search

reproducible corpus configuration

versioned document manifests

streamed PDF acquisition

checksum validation and acquisition receipts

page-level PDF extraction

citation-preserving overlapping chunks

BM25 lexical retrieval

Sentence Transformer dense retrieval

persistent NumPy embedding indexes

exact cosine-similarity dense search

Reciprocal Rank Fusion hybrid retrieval

cross-encoder reranking

preserved BM25, dense, hybrid, and reranker provenance

pooled retrieval evaluation

deterministic facet-aware evidence retrieval for supported synthesis patterns

deterministic evidence-sufficiency assessment

morphology-aware query normalization

numeric-support checks

named-anchor checks

claim-qualifier checks

insufficient-evidence refusal before provider invocation

provider-agnostic generation interface

deterministic local generation provider

OpenAI Responses API structured provider adapter

versioned provider configuration

prompt versioning and evidence delimiters

prompt-injection heuristics

structured provider-response validation

retry and timeout handling

token, latency, retry, request-ID, and estimated-cost telemetry

authoritative application-side citation resolution

claim, citation, source-document, and answer schemas

generation v0.3 benchmark with 32 labeled queries

reusable shared runtime construction

FastAPI application factory

lifespan-managed one-time RAG runtime loading

environment-driven local/OpenAI API modes

GET /health

GET /ready

POST /v1/query

structured API errors

per-request X-Request-ID

Typer command-line interface

Ruff, pytest, strict mypy, coverage, and GitHub Actions

Generation v0.3 final benchmark

The final benchmark contains:

20 expected-answerable queries
12 unsupported queries
32 total queries

The final benchmark configuration uses:

Sufficiency v0.2.1
+
Facet Retrieval v0.1
+
OpenAI Responses API provider

Final generation results

Metric

Baseline

Final

Answerability accuracy

0.9375

1.0000

Answerable completion

0.9000

1.0000

Unsupported refusal

1.0000

1.0000

Claim citation coverage

1.0000

1.0000

Citation-reference validity

1.0000

1.0000

Expected-term recall

0.9138

0.9310

Structural validity

1.0000

1.0000

Provider-routing results

Metric

Baseline

Final

Provider calls

22

20

Provider bypasses

10

12

Provider call-policy accuracy

0.8750

1.0000

Total tokens

63,638

58,915

Estimated benchmark cost

$0.105733

$0.103745

Final measured latency:

P50 provider latency: 5.6394 s
P95 provider latency: 7.6947 s
Provider retry rate: 0.0

The final benchmark produced zero answerability failures.

These results describe the current engineering benchmark only. They are not evidence of universal RAG correctness, general-purpose answer faithfulness, or performance outside the current corpus and evaluation set.

Tracked reports include:

artifacts/evaluation/generation_deterministic_v0_3.json
artifacts/evaluation/generation_deterministic_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3.json
artifacts/evaluation/generation_openai_v0_3_telemetry.json
artifacts/evaluation/generation_openai_v0_3_final.json
artifacts/evaluation/generation_openai_v0_3_final_telemetry.json
artifacts/evaluation/generation_v0_3_final_comparison.json

Retrieval benchmarks

Retrieval benchmark v0.1

Retriever

Recall@5

Recall@10

MRR@10

NDCG@10

BM25

0.7500

0.9167

0.6771

0.7046

Dense

0.2292

0.3958

0.3376

0.2812

The v0.1 judgments were created from a BM25-generated candidate pool, so this comparison can favor BM25.

Pooled retrieval benchmark v0.2

Property

Value

Evaluation queries

8

BM25 depth per query

20

Dense depth per query

20

Candidates after deduplication

278

Relevant labels

101

Non-relevant labels

177

Shuffle seed

42

Corpus size

3,233 chunks

Retriever

Recall@5

Recall@10

MRR@10

NDCG@10

BM25

0.2662

0.4016

0.7292

0.5321

Dense

0.1330

0.2778

0.5521

0.3976

Hybrid RRF

0.2043

0.3024

0.7639

0.4777

Reranker top-10

0.2087

0.3024

0.7188

0.4614

Reranker top-20

0.2068

0.3375

0.8375

0.5080

Current reranker:

cross-encoder/ms-marco-MiniLM-L6-v2

Current scoring-only CPU latency baseline:

Field

Value

Queries

8

Query-chunk pairs

160

Total scoring seconds

3.170787

Milliseconds per pair

19.817420

Hardware

MacBook Air, CPU baseline

FastAPI service

AeroRAG-X exposes the same grounded-generation runtime through a FastAPI service.

The heavy retrieval and generation runtime is constructed once during application startup and reused across requests.

Endpoints

Method

Endpoint

Purpose

GET

/health

Process health check

GET

/ready

RAG runtime readiness

POST

/v1/query

Generate one evidence-grounded answer

GET

/docs

Interactive Swagger/OpenAPI documentation

GET

/redoc

ReDoc documentation

GET

/openapi.json

OpenAPI schema

Runtime environment

AERORAGX_RUNTIME_MODE
AERORAGX_CANDIDATE_TOP_K
AERORAGX_EVIDENCE_TOP_K

Supported runtime modes:

local
openai

Local deterministic mode

Local mode runs the full retrieval, reranking, facet-selection, sufficiency, citation-resolution, and HTTP path without an external LLM call.

Terminal 1:

unset OPENAI_API_KEY

export AERORAGX_RUNTIME_MODE=local
export AERORAGX_CANDIDATE_TOP_K=20
export AERORAGX_EVIDENCE_TOP_K=5

python -m uvicorn \
  aeroragx.api:app \
  --host 127.0.0.1 \
  --port 8000

Keep the server running. In Terminal 2:

curl -sS http://127.0.0.1:8000/health
echo

curl -sS http://127.0.0.1:8000/ready
echo

Example grounded query:

curl -sS \
  -X POST \
  http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query":
    "Why is cryogenic hydrogen storage challenging for aircraft?"
  }'

OpenAI-backed mode

The same service can use the configured OpenAI Responses API provider without changing application code.

export AERORAGX_RUNTIME_MODE=openai
export AERORAGX_CANDIDATE_TOP_K=20
export AERORAGX_EVIDENCE_TOP_K=5

Set OPENAI_API_KEY securely in the environment. Do not commit it.

On macOS, one temporary approach is to copy the key to the clipboard and run:

export OPENAI_API_KEY="$(pbpaste | tr -d '\r\n')"
printf '' | pbcopy

After the live test:

unset OPENAI_API_KEY
export AERORAGX_RUNTIME_MODE=local

OpenAI execution uses:

configs/generation_openai_v0_1.yaml
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml
configs/sufficiency_v0_2_1.yaml
configs/facet_retrieval_v0_1.yaml

Request IDs

Every HTTP request receives an AeroRAG-X request identifier.

Responses include:

X-Request-ID: <uuid>

Structured errors include the same request ID in the JSON body.

Example:

{
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed.",
    "request_id": "<same UUID as X-Request-ID>"
  }
}

Current error categories:

HTTP status

Error code

Meaning

422

invalid_request

Request-schema validation failure

502

provider_failure

Structured generation-provider failure

503

runtime_unavailable

RAG runtime is unavailable

500

internal_error

Unexpected internal failure

Provider and internal exception details are not exposed directly to clients.

Provider telemetry

When a structured external provider is invoked, retrieval_metadata.provider_telemetry can include:

provider request ID
model name
attempt count
latency
input tokens
output tokens
estimated cost
prompt-injection assessment
success/failure state

If the evidence-sufficiency gate rejects a request before provider invocation, provider telemetry remains null.

Controlled HTTP validation

The serving path has been validated through both deterministic and OpenAI-backed execution.

A controlled answerable OpenAI request returned:

HTTP status: 200
AeroRAG-X X-Request-ID: present
Provider: openai-responses
Model: gpt-5.6-luna
Grounded claims: 3
Authoritative citations: 5
Source documents: 4
Provider attempts: 1
Provider latency: 5.1753 s
Input tokens: 2355
Output tokens: 340
Estimated provider cost: $0.004395
Prompt-injection assessment: safe

A controlled unsupported fictional query returned:

insufficient_evidence: true
claims: 0
citations: 0
provider_telemetry: null

That verifies provider bypass when the sufficiency layer rejects unsupported evidence.

Evidence-sufficiency gate

Primary implementation:

src/aeroragx/generation/sufficiency.py

Current benchmark configuration:

configs/sufficiency_v0_2_1.yaml

The gate checks:

minimum evidence count

informative query-term coverage

minimum supported terms

single-evidence coverage

numeric support

named-anchor support

claim-qualifier support

stricter coverage for exact-value questions

The full decision is preserved in retrieval metadata for auditable provider bypasses and refusals.

Facet-aware retrieval

Primary implementation:

src/aeroragx/generation/facet_retrieval.py

Configuration:

configs/facet_retrieval_v0_1.yaml

For recognized multi-facet synthesis patterns, the wrapper:

derives deterministic facet searches;

retrieves evidence for each facet;

verifies semantic facet identity;

deduplicates by chunk_id;

balances evidence across supported facets;

adds original-query evidence;

falls back to ordinary retrieval if semantic facet support is unavailable.

The current implementation is intentionally narrow rather than a general-purpose query-planning agent.

Hardened provider layer

Current OpenAI generation configuration:

configs/generation_openai_v0_1.yaml

Current configured model:

gpt-5.6-luna

Provider-hardening configuration:

configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml

Controls include:

versioned prompt configuration

explicit evidence delimiters

prompt-injection heuristics

response-schema enforcement

bounded retries

timeout handling

retryable versus non-retryable transport errors

secret redaction

provider request IDs

latency measurement

input/output token accounting

estimated cost accounting

Retrieved evidence is treated as untrusted input. The provider is not trusted to create authoritative citation metadata.

Citation trust boundary

The provider may return:

claim -> evidence ID

AeroRAG-X resolves each evidence ID to authoritative retrieved metadata.

The final citation preserves:

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

Unknown evidence references are rejected.

Installation

AeroRAG-X requires Python 3.12 or newer.

git clone https://github.com/triasha72/AeroRAG-X.git
cd AeroRAG-X

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

Conda is also supported:

conda create -n aeroragx-py312 python=3.12
conda activate aeroragx-py312
python -m pip install -e ".[dev]"

Check the CLI:

aeroragx --help

Important CLI workflows

Cross-encoder reranking

aeroragx ntrs-reranker-search \
  --query "battery thermal runaway" \
  --candidate-top-k 20 \
  --top-k 10

Deterministic grounded answer

aeroragx ntrs-grounded-answer \
  --query "How can battery thermal runaway propagate in electric aircraft?" \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --generation-config configs/generation_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_2_1.yaml

OpenAI grounded answer with facet-aware retrieval

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

Validation

Run the local quality gate:

python -m ruff format --check .
python -m ruff check .
python -m pytest -q
python -m mypy src/aeroragx
git diff --check

CI runs the same core quality checks on pull requests.

Repository structure

AeroRAG-X/
├── .github/
│   └── workflows/
├── artifacts/
├── configs/
├── data/
├── docs/
│   ├── api.md
│   ├── architecture.md
│   ├── evaluation.md
│   └── generation.md
├── scripts/
├── src/
│   └── aeroragx/
│       ├── api/
│       ├── generation/
│       ├── ingestion/
│       ├── processing/
│       ├── retrieval/
│       └── runtime.py
├── tests/
├── LICENSE
├── README.md
├── ROADMAP.md
└── pyproject.toml

Documentation

docs/architecture.md — architecture, trust boundaries, runtime composition, and failure behavior

docs/api.md — FastAPI endpoints, environment configuration, request IDs, errors, and smoke tests

docs/generation.md — grounded generation and provider behavior

docs/evaluation.md — retrieval and generation evaluation

ROADMAP.md — completed milestones and next phases

Security and limitations

AeroRAG-X currently:

treats retrieved text as untrusted provider input;

uses deterministic prompt-injection heuristics;

validates structured provider output;

rejects unknown evidence IDs;

resolves citation metadata application-side;

redacts provider secrets from transport errors;

refuses unsupported questions before provider invocation when possible;

keeps API keys in environment variables rather than tracked configuration.

Current non-goals include:

autonomous general-purpose agents;

semantic entailment verification;

table/figure retrieval;

managed secret storage;

cloud deployment;

persistent vector-database serving.

Next milestone

The next engineering milestone is Dockerized local service deployment, followed by structured service observability and cloud deployment.

See ROADMAP.md for the planned sequence.