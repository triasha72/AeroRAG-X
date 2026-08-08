AeroRAG-X Roadmap

AeroRAG-X is a production-oriented, evidence-grounded retrieval-augmented generation system for aerospace technical knowledge.

The project follows an evaluation-first development strategy:

Reliable corpus
-> verified processing
-> lexical + semantic retrieval
-> pooled relevance evaluation
-> hybrid retrieval
-> cross-encoder reranking
-> grounded generation
-> evidence-sufficiency gating
-> hardened provider
-> facet-aware synthesis retrieval
-> generation v0.3 benchmark
-> FastAPI serving
-> containerization
-> observability
-> cloud deployment
-> persistent vector infrastructure
-> multimodal retrieval

Current project status

Completed text-RAG milestone

NASA NTRS metadata ingestion

reproducible corpus manifests

PDF acquisition and checksum validation

page-level PDF extraction

citation-preserving overlapping chunks

BM25 lexical retrieval

Sentence Transformer dense retrieval

exact cosine search over 3,233 chunks

Reciprocal Rank Fusion hybrid retrieval

cross-encoder reranking

pooled relevance evaluation

provider-agnostic grounded generation

deterministic local provider

OpenAI Responses API provider adapter

structured provider responses

prompt versioning

prompt-injection heuristics

timeout and bounded retry behavior

latency/token/cost telemetry

deterministic evidence-sufficiency gating

numeric support checks

named-anchor support checks

claim-qualifier support checks

Sufficiency v0.2.1 calibration

deterministic facet-aware evidence retrieval

semantic facet verification

generation v0.3 telemetry benchmark

32-query final generation benchmark

zero answerability failures on the current benchmark

frozen final benchmark artifacts

shared reusable RAG runtime

production-oriented FastAPI serving path

environment-driven local/OpenAI API modes

structured API errors

per-request request IDs

controlled live OpenAI HTTP validation

controlled unsupported-query provider-bypass validation

Final generation v0.3 results

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

Provider call-policy accuracy

0.8750

1.0000

Final provider telemetry:

Provider calls: 20
Provider bypasses: 12
Total tokens: 58,915
Estimated benchmark cost: $0.103745
P50 provider latency: 5.6394 s
P95 provider latency: 7.6947 s
Retry rate: 0.0

Current priority

The immediate priority is:

FastAPI PR + CI
-> main branch protection
-> Dockerized local service
-> structured logging / observability
-> deployment

Phase 1 — Repository foundation

Python package with src/ layout

pyproject.toml

editable installation

Typer CLI

YAML configuration

Ruff

pytest

coverage reporting

strict mypy

GitHub Actions

feature-branch and pull-request workflow

MIT license

protect main

require passing CI before merge

prevent force pushes to main

enforce coverage threshold

add pre-commit hooks

Phase 2 — Reproducible NASA corpus acquisition

define initial aerospace corpus

NASA NTRS metadata search

normalize NTRS records

versioned corpus configuration

document manifests

PDF-link resolution

streamed downloads

.part temporary files

download validation

checksums

acquisition receipts

NASA citation/source URLs

formal dataset card

corpus inclusion/exclusion criteria

corpus-version comparison tooling

additional approved aerospace sources

Phase 3 — Processing and provenance

source-checksum verification

PDF text extraction

page-boundary preservation

empty-page preservation

page-level records

extraction receipts

deterministic overlapping chunks

document/page identifiers

page ranges

citation URLs

source URLs

source-document checksums

chunking receipts

add document title to every chunk

add publication date to every chunk

semantic chunking experiment

fixed versus semantic chunking comparison

table detection

structured table extraction

figure detection

figure image/caption extraction

OCR fallback only when native extraction is unavailable

Phase 4 — Retrieval baselines

BM25

tokenization

inverted index

configurable k1

configurable b

deterministic tie-breaking

full chunk provenance

CLI

tests

real NASA corpus search

Dense retrieval

Sentence Transformers

normalized embeddings

NumPy persistence

aligned metadata

versioned manifest

exact cosine similarity

CLI

tests

index over 3,233 chunks

evaluate alternative embedding models

embedding-throughput benchmark

ANN indexing when scale requires it

vector database integration

Phase 5 — Retrieval evaluation

v0.1

eight aerospace queries

BM25 annotation candidates

relevance judgments

Recall@5

Recall@10

MRR@10

NDCG@10

aggregate/per-query reports

BM25 and dense reports

candidate-pool bias documented

pooled v0.2

top-20 BM25 candidates

top-20 dense candidates

candidate combination/deduplication

blinded annotation records

deterministic ordering

278 candidates reviewed

101 relevant / 177 non-relevant labels

BM25 reevaluation

dense reevaluation

Hybrid RRF evaluation

cross-encoder reranker evaluation

independent second-pass relevance audit

expand to 25–40 retrieval queries

multiple assessors

inter-annotator agreement

regression thresholds

Phase 6 — Hybrid retrieval

Reciprocal Rank Fusion

independent BM25/dense retrieval

deterministic candidate deduplication

source ranks and scores

retrieval provenance

CLI

unit tests

pooled benchmark

tune RRF parameters on separate development data

Phase 7 — Cross-encoder reranking

cross-encoder model

bounded Hybrid RRF candidate reranking

retrieval provenance

CLI

deterministic fake-scorer tests

scoring latency

pooled evaluation

alternate reranker benchmark

CPU/MPS/CUDA comparison

Current model:

cross-encoder/ms-marco-MiniLM-L6-v2

Phase 8 — Grounded answer generation

Core

provider protocol

deterministic provider

structured provider response

grounded-answer schema

claim schema

authoritative citation schema

source-document schema

bounded evidence/context

citation-ID requirements

application-side citation resolution

invalid state rejection

source-document summaries

JSON writer

CLI

OpenAI Responses API adapter

local neural LLM provider

neighboring-chunk expansion experiment

near-duplicate context-removal experiment

Evidence sufficiency

deterministic sufficiency configuration

informative query-term coverage

minimum supported-term check

single-evidence coverage

numeric-support check

named-anchor support check

exact-query threshold

morphology normalization

claim-qualifier support

calibrated technical-compound handling

auditable rejection reasons

refusal before provider invocation

Sufficiency v0.2.1

Facet-aware evidence

deterministic shared-facet planning

facet-specific retrieval

semantic facet verification

deduplication

balanced evidence selection

ordinary-retrieval fallback

integrated CLI support

integrated generation benchmark support

broaden facet planner only after additional benchmark coverage

Phase 9 — Provider hardening and safety

Provider infrastructure

versioned provider configuration

structured prompt builder

prompt version identifier

OpenAI structured-output adapter

HTTP transport

provider factory

timeout handling

bounded retries

retryable/non-retryable transport errors

structured-response validation

latency telemetry

input/output token telemetry

estimated cost telemetry

secret redaction

Guardrails

retrieved evidence treated as untrusted input

prompt-injection detection heuristics

explicit evidence delimiters

hidden/system prompt extraction patterns

role-reassignment detection

tool-execution injection detection

unknown evidence-ID rejection

malformed-provider-payload rejection

provider-error regression tests

prompt-injection regression tests

Future hardening

broaden adversarial evaluation dataset

semantic prompt-injection classifier experiment

provider circuit-breaker policy

rate-limit specific integration tests

fault-injection benchmark

production secret-manager integration

Phase 10 — Generation evaluation

answerability-labeled queries

unsupported controls

answerability accuracy

answerable completion

unsupported refusal

claim citation coverage

citation-reference validity

source-document coverage

expected-term recall

structural-validity checks

per-query results

telemetry evaluation

deterministic provider baseline

OpenAI provider baseline

expanded v0.3 dataset: 32 queries

multi-document synthesis cases

provider call/bypass policy metric

latency/token/cost telemetry

final 32-query run with zero answerability failures

final comparison artifact

semantic citation-support scoring

semantic answer-faithfulness evaluation

semantic answer-relevance evaluation

independent human review

multiple benchmark assessors

larger benchmark

generation regression thresholds in CI

Phase 11 — FastAPI serving — IMPLEMENTED

Application

FastAPI dependency

application factory

query-service dependency injection

startup/shutdown lifespan

shared runtime construction

load retrieval/generation components once per process

environment-driven runtime configuration

deterministic local mode

OpenAI-backed mode

Endpoints

GET /health

GET /ready

POST /v1/query

request/response Pydantic schemas

structured error responses

per-request X-Request-ID

validation-error mapping

provider-error mapping

runtime-unavailable mapping

safe internal-error mapping

OpenAPI documentation

optional debug-metadata exposure policy

API tests

health endpoint

readiness endpoint

supported query

blank-query rejection

missing-query rejection

unexpected-field rejection

structured validation errors

structured provider errors

structured internal errors

request-ID behavior

runtime lifecycle behavior

dedicated unsupported-query API regression test

dedicated citation-preservation API contract test

dedicated provider-bypass API regression test

dedicated facet-aware API regression test

HTTP integration validation

deterministic local-runtime HTTP smoke test

real NASA retrieval through FastAPI

runtime reuse across multiple HTTP requests

environment-driven local-mode validation

controlled OpenAI-backed HTTP request

provider telemetry validation

request-ID validation

controlled unsupported-query provider bypass

API key removed after live validation

The serving architecture and HTTP execution path are implemented. Remaining unchecked API-test items are extended regression coverage rather than blockers for this milestone.

Phase 12 — Docker and local service deployment — IMPLEMENTED

Dockerfile

.dockerignore

Python 3.12 slim serving image

CPU-only PyTorch runtime

reproducible container build

non-root runtime user

environment-variable documentation

container health check

extended model-loading startup allowance

generated corpus mounted read-only

generated dense index mounted read-only

deterministic local container boot

GET /health container validation

GET /ready container validation

Docker health validation

real NASA-backed query through container

grounded claims through container

authoritative citations through container

X-Request-ID preservation through container

reproducible scripts/docker_smoke.sh integration test

Docker image architecture validation

CPU dependency validation

Docker image-size review

Docker build validation in GitHub Actions

BuildKit GitHub Actions cache

Docker Compose intentionally deferred until additional services require it

The Docker service deliberately keeps generated corpus and dense-index
artifacts outside the image and mounts them read-only at runtime.

Phase 13 — Observability and reliability — NEXT

structured JSON logging

request-ID propagation into logs

retrieval latency

reranker latency

facet-retrieval usage

sufficiency result

provider called/bypassed

provider attempts/retries

provider latency

token counts

estimated cost

citation count

error counters

P50/P95 request latency

redaction verification

OpenTelemetry instrumentation

load test

failure-mode runbook

Phase 14 — Cloud deployment

select deployment target

container registry

managed secret storage

deploy service

health/readiness configuration

structured logs

deployment CI workflow

rollback procedure

cost estimate

public demo policy and abuse limits

Phase 15 — Persistent vector infrastructure

Do this only when service requirements justify it.

PostgreSQL + pgvector development configuration

vector-schema migration

embeddings/provenance persistence

metadata filtering

document upsert/delete

index-version metadata

pgvector retrieval implementation

compare pgvector with exact NumPy baseline

retrieval latency benchmark

backup/restore instructions

Phase 16 — Multimodal report processing

figure detection

figure-caption extraction

page linkage

table detection

structured table extraction

multimodal retrieval records

image/table citation representation

multimodal evaluation dataset

multimodal answer tests

OCR fallback policy

Phase 17 — Evaluation maturity

larger retrieval benchmark

larger generation benchmark

conflicting-evidence cases

partial-evidence cases

adversarial prompt-injection benchmark

semantic citation support

semantic answer faithfulness

semantic answer relevance

independent human review

multiple benchmark assessors

regression thresholds in CI

Phase 18 — Portfolio-quality release

merge FastAPI PR through green CI

protect main

add Docker deployment

add service architecture diagram

add one reproducible demo workflow

publish benchmark summary

publish container usage

create versioned release/tag

add concise portfolio/resume project description