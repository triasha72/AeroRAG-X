AeroRAG-X Architecture

AeroRAG-X is a retrieval-first, evidence-grounded system for aerospace technical knowledge.

The architecture separates acquisition, processing, retrieval, reranking, facet-aware evidence selection, evidence sufficiency, provider execution, citation resolution, serving, and evaluation so that each stage can be tested independently.

Implemented end-to-end pipeline

NASA Technical Reports Server
               |
               v
      Metadata normalization
               |
               v
       Versioned corpus manifest
               |
               v
 PDF download + checksum validation
               |
               v
     Page-level PDF extraction
               |
               v
 Citation-preserving text chunks
               |
       +-------+-------+
       |               |
       v               v
 BM25 retrieval   Dense retrieval
       |               |
       +-------+-------+
               |
               v
 Reciprocal Rank Fusion
               |
               v
       Hybrid retrieval
               |
               v
 Cross-encoder reranking
               |
               v
 Optional facet-aware evidence selection
               |
               v
 Evidence-sufficiency assessment
               |
        +------+------+
        |             |
        v             v
  sufficient      insufficient
        |             |
        v             v
 hardened LLM     grounded refusal
 provider
        |
        v
 structured response validation
        |
        v
 claim/evidence validation
        |
        v
 authoritative citation resolution
        |
        v
 source-document summaries
        |
        v
 retrieval + provider telemetry
        |
        v
 shared AeroRAG runtime
        |
        +--------------------+
        |                    |
        v                    v
      Typer                FastAPI
       CLI        /health /ready /v1/query

The current text pipeline operates over 3,233 citation-preserving NASA report chunks.

Design principles

Retrieval first

Generation is downstream of retrieval. The provider never directly searches the corpus.

Provenance first

Document IDs, page ranges, URLs, chunk IDs, and source-document checksums survive from processing through final citations.

Provider distrust

The provider may produce structured claims and refer to evidence IDs. It is not trusted to create authoritative citation metadata.

Retrieved text is untrusted input

Retrieved documents are evidence, not instructions. Provider prompts use explicit evidence delimiters and prompt-injection checks.

Fail closed

Unknown evidence IDs, malformed structured outputs, unsupported answer states, and insufficient evidence are rejected rather than silently accepted.

Refuse before paying when possible

The evidence-sufficiency gate can bypass the remote provider for unsupported questions.

Narrow deterministic complexity before agentic complexity

Facet-aware retrieval uses a deterministic planner for supported synthesis patterns instead of an unconstrained LLM query planner.

Reuse the same runtime across interfaces

CLI, evaluation, and HTTP serving compose the same retrieval/generation runtime. Serving code does not reimplement retrieval or grounding logic.

Evaluation before optimization

Every major retrieval/generation capability is paired with a benchmark or deterministic regression test before the next architectural layer is added.

Ingestion layer

Primary modules:

src/aeroragx/ingestion/ntrs.py
src/aeroragx/ingestion/corpus.py
src/aeroragx/ingestion/acquisition.py

Responsibilities:

NASA NTRS metadata search

record normalization

versioned corpus definitions

manifest generation

PDF-link resolution

streamed downloads

temporary .part files

checksum calculation

acquisition receipts

NASA citation/source URL preservation

Processing layer

Primary modules:

src/aeroragx/processing/pdf.py
src/aeroragx/processing/chunking.py

Each chunk preserves:

chunk_id
document_id
chunk_index
page_start
page_end
page_ids
text
word_count
character_count
token_estimate
citation_url
source_url
document_sha256

The processing layer is deterministic and provenance preserving.

Retrieval stack

BM25

src/aeroragx/retrieval/bm25.py

Provides lexical retrieval with deterministic ranking and chunk provenance.

Dense retrieval

src/aeroragx/retrieval/dense.py

Current baseline:

Model: sentence-transformers/all-MiniLM-L6-v2
Chunks: 3,233
Dimension: 384
Normalization: enabled
Search: exact cosine similarity
Storage: NumPy

Hybrid retrieval

src/aeroragx/retrieval/hybrid.py

Uses Reciprocal Rank Fusion rather than adding incompatible lexical and dense raw scores.

Baseline:

RRF k: 60
BM25 depth: 50
Dense depth: 50

Cross-encoder reranking

src/aeroragx/retrieval/reranker.py

Current model:

cross-encoder/ms-marco-MiniLM-L6-v2

Generation currently uses:

candidate_top_k: 20
evidence_top_k: 5

Facet-aware evidence selection

Primary module:

src/aeroragx/generation/facet_retrieval.py

Configuration:

configs/facet_retrieval_v0_1.yaml

For recognized multi-facet synthesis patterns:

original synthesis query
        |
        v
deterministic facet plan
   +----+----+
   |         |
   v         v
facet A    facet B
search     search
   |         |
   +----+----+
        |
        v
semantic facet verification
        |
        v
deduplicate by chunk_id
        |
        v
round-robin facet balancing
        |
        v
add original-query evidence
        |
        v
bounded final evidence set

If a required facet lacks semantic matches, the wrapper falls back to ordinary original-query retrieval.

The current scope is intentionally narrow. It is not a general-purpose query decomposition engine.

Evidence-sufficiency layer

Primary module:

src/aeroragx/generation/sufficiency.py

Current benchmark config:

configs/sufficiency_v0_2_1.yaml

The assessor checks:

minimum evidence count
informative query-term coverage
minimum supported terms
single-evidence coverage
numeric support
named-anchor support
claim-qualifier support
stricter exact-query coverage

The result includes auditable reasons and is preserved in retrieval metadata.

Provider-bypass behavior

When evidence is insufficient:

provider called = false
insufficient_evidence = true
claims = []
citations = []
source_documents = []
provider_telemetry = null

This path has been validated over the HTTP service with an unsupported fictional query.

Provider layer

Provider protocol

The generation provider receives:

query
bounded evidence records
maximum claim count

and returns:

answer
claims
insufficient_evidence

Provider claims reference evidence IDs rather than arbitrary source URLs.

Implementations

Deterministic/local provider:

src/aeroragx/generation/provider.py

Structured remote provider:

src/aeroragx/generation/structured_provider.py
src/aeroragx/generation/http_transport.py
src/aeroragx/generation/model_adapter.py
src/aeroragx/generation/provider_factory.py

Prompt/guardrails:

src/aeroragx/generation/prompting.py
src/aeroragx/generation/guardrails.py

OpenAI configuration:

configs/generation_openai_v0_1.yaml
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml

Current configured model:

gpt-5.6-luna

Provider hardening

The hardened provider path includes:

versioned prompt configuration
evidence delimiters
prompt-injection assessment
structured response schema
bounded retries
timeouts
retryable/non-retryable transport errors
usage telemetry
provider request IDs
latency telemetry
estimated cost
secret redaction

Prompt-injection regression tests cover instruction override, hidden-prompt extraction, developer-message injection, tool/shell execution requests, and role reassignment.

Grounded-generation layer

Primary module:

src/aeroragx/generation/grounded.py

Responsibilities:

obtain bounded reranked/facet-aware evidence;

build generation evidence;

run evidence sufficiency;

bypass the provider when evidence is insufficient;

call the configured provider when evidence is sufficient;

validate provider evidence references;

resolve claim references to authoritative citations;

construct deduplicated source-document summaries;

validate supported/refusal answer states;

attach retrieval and provider telemetry.

Final answer

query
answer
claims
citations
source_documents
insufficient_evidence
retrieval_metadata

Citation trust boundary

Provider output may say:

CL1 -> E1, E3

The application resolves those evidence IDs to trusted stored metadata.

The provider does not supply authoritative:

document ID
page range
NASA citation URL
source URL
checksum

This prevents the model from becoming the source of truth for provenance.

Shared runtime layer

Primary module:

src/aeroragx/runtime.py

The runtime composes:

BM25Index
   +
DenseIndex
   |
   v
HybridIndex
   |
   v
RerankerIndex
   |
   +----------------------------+
   |                            |
   | optional                   |
   v                            |
FacetAwareEvidenceIndex         |
   |                            |
   +-------------+--------------+
                 |
                 v
EvidenceSufficiencyAssessor
                 |
                 v
Configured GenerationProvider
                 |
                 v
GroundedAnswerGenerator

The CLI, evaluation benchmark, and FastAPI service reuse this construction.

FastAPI serving layer

Primary modules:

src/aeroragx/api/app.py
src/aeroragx/api/schemas.py
src/aeroragx/api/service.py
src/aeroragx/api/settings.py
src/aeroragx/api/errors.py

Application lifecycle

process start
    |
    v
create FastAPI app
    |
    v
lifespan startup
    |
    v
load shared AeroRAG runtime once
    |
    v
store QueryService in app.state
    |
    v
serve requests using same runtime
    |
    v
lifespan shutdown

Heavy retrieval models and indexes are not rebuilt per request.

Runtime modes

Environment-driven selection:

AERORAGX_RUNTIME_MODE=local
AERORAGX_RUNTIME_MODE=openai

Depth controls:

AERORAGX_CANDIDATE_TOP_K
AERORAGX_EVIDENCE_TOP_K

HTTP query path

POST /v1/query
      |
      v
generate X-Request-ID
      |
      v
Pydantic validation
      |
      v
QueryService
      |
      v
GroundedAnswerGenerator
      |
      v
retrieval + reranking
      |
      v
facet-aware evidence selection
      |
      v
sufficiency gate
      |
      +-------------------+
      |                   |
      v                   v
provider call       grounded refusal
      |
      v
citation resolution
      |
      v
GroundedAnswer JSON

Endpoints

GET  /health
GET  /ready
POST /v1/query
GET  /docs
GET  /redoc
GET  /openapi.json

Structured error mapping

request validation      -> 422 invalid_request
provider failure        -> 502 provider_failure
runtime unavailable     -> 503 runtime_unavailable
unexpected exception    -> 500 internal_error

Error responses carry the same request ID in:

X-Request-ID
error.request_id

Provider/internal exception details are not returned to clients.

Controlled live validation

A controlled answerable OpenAI-backed HTTP request validated:

HTTP 200
Provider: openai-responses
Model: gpt-5.6-luna
Claims: 3
Citations: 5
Source documents: 4
Attempts: 1
Latency: 5.1753 s
Input tokens: 2355
Output tokens: 340
Estimated cost: $0.004395
Prompt-injection assessment: safe

A controlled unsupported query validated pre-provider refusal with:

insufficient_evidence = true
provider_telemetry = null

Generation evaluation

Primary modules:

src/aeroragx/generation/evaluation.py
src/aeroragx/generation/telemetry_evaluation.py

Benchmark:

data/evaluation/generation_queries_v0_3.jsonl

Final v0.3:

Queries: 32
Answerability accuracy: 1.0000
Answerable completion: 1.0000
Unsupported refusal: 1.0000
Claim citation coverage: 1.0000
Citation-reference validity: 1.0000
Expected-term recall: 0.9310
Structural validity: 1.0000

Provider calls: 20
Provider bypasses: 12
Provider call-policy accuracy: 1.0000
Total provider tokens: 58,915
Estimated total provider cost: $0.103745
P50 provider latency: 5.6394 s
P95 provider latency: 7.6947 s

These values describe the current engineering benchmark only.

Trust domains

1. External documents

Controls:

checksums

acquisition receipts

page provenance

source URLs

2. Retrieval/reranking outputs

Controls:

pooled evaluation

stage-specific metrics

ranking provenance

deterministic tie-breaking

3. Retrieved evidence text

Controls:

explicit data delimiters

prompt-injection checks

fail-closed policy when configured

4. Generation provider

Controls:

structured schema

bounded evidence references

retries/timeouts

malformed-response rejection

application-side citation resolution

telemetry

5. Serving layer

Controls:

Pydantic request validation

application lifecycle

reusable shared runtime

environment-driven configuration

request IDs

structured safe errors

provider failure mapping

runtime readiness endpoint

6. Container layer

Controls:

Python 3.12 slim runtime

CPU-only PyTorch serving environment

non-root process execution

read-only generated-artifact mounts

environment-driven runtime configuration

container health check

FastAPI readiness endpoint

reproducible local smoke validation

Docker build validation in CI

Failure behavior

Evidence insufficiency

provider called = false
insufficient_evidence = true
claims = []
citations = []
source_documents = []
provider_telemetry = null

Missing semantic facet

Facet-aware retrieval falls back to ordinary original-query retrieval.

Prompt injection detected under block policy

Provider invocation is blocked.

Unknown evidence reference

Provider response is rejected.

Malformed provider response

Provider response is rejected.

Retryable transport error

The provider retries up to the configured bound and records telemetry.

Non-retryable transport error

The provider fails immediately.

API validation error

Returns structured HTTP 422 with invalid_request.

Provider failure over HTTP

Returns structured HTTP 502 with provider_failure.

Runtime unavailable

Returns structured HTTP 503 with runtime_unavailable.

Unexpected API failure

Returns structured HTTP 500 with internal_error.

Current non-goals

The current milestone does not yet provide:

managed secret storage;

vector-database serving;

autonomous general-purpose agents;

semantic entailment verification;

table/figure retrieval;

cloud deployment.

Observability architecture

The serving path now includes an observability plane:

```text
FastAPI request
      |
      +--> structured JSON logs
      |
      +--> Prometheus metrics
      |
      +--> OpenTelemetry SERVER span
               |
               v
         aeroragx.query
               |
               +--> retrieval
               |     |
               |     +--> reranker
               |            |
               |            +--> hybrid_retrieval
               |                    |
               |                    +--> bm25
               |                    +--> dense
               |                    +--> hybrid_fusion
               |
               +--> evidence_build
               +--> sufficiency
               +--> provider
               +--> citation_resolution
```

The observability layer preserves the existing application trust boundary.

It does not log or trace raw query text, raw retrieved evidence, answer text, API keys, authorization headers, or provider credentials.

Prometheus labels avoid high-cardinality identifiers such as request IDs, document IDs, and chunk IDs.

Trace export is disabled by default and can be enabled through environment configuration. OTLP/HTTP export has been validated against a local OpenTelemetry Collector.

Next architecture milestone

AeroRAG-X core
      |
      v
FastAPI serving                IMPLEMENTED
      |
      v
Docker container               IMPLEMENTED
      |
      v
structured JSON logging        IMPLEMENTED
      |
      v
Prometheus metrics             IMPLEMENTED
      |
      v
P50/P95/P99 load validation    IMPLEMENTED
      |
      v
OpenTelemetry tracing          IMPLEMENTED
      |
      v
OTLP export                    IMPLEMENTED
      |
      v
cloud deployment               NEXT

The cloud phase should reuse the same Docker image, shared AeroRAG-X runtime, health/readiness contract, observability schema, and grounded-generation trust boundary.
