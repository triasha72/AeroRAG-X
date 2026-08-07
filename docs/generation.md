# Grounded Generation

This document describes AeroRAG-X grounded generation, evidence sufficiency, facet-aware retrieval, provider hardening, and citation resolution.

---

## Generation goal

AeroRAG-X should answer only when the retrieved evidence can support the question and should preserve a machine-auditable path from every generated claim to authoritative source metadata.

The generation layer is therefore designed around four rules:

1. retrieval happens before generation;
2. unsupported questions should be refused before a paid provider call when possible;
3. the provider can reference evidence but cannot invent trusted provenance;
4. provider output must satisfy a structured schema.

---

## Generation path

```text
query
  |
  v
reranked retrieval
  |
  v
optional facet-aware evidence selection
  |
  v
bounded GenerationEvidence records
  |
  v
EvidenceSufficiencyAssessor
  |
  +--------------------+
  |                    |
  v                    v
sufficient         insufficient
  |                    |
  v                    v
provider call      grounded refusal
  |
  v
structured response validation
  |
  v
claim -> evidence validation
  |
  v
authoritative citation resolution
  |
  v
GroundedAnswer
```

---

## Evidence sufficiency

Current benchmark configuration:

```text
configs/sufficiency_v0_2_1.yaml
```

The assessor checks:

- evidence count;
- informative query-term coverage;
- supported-term count;
- single-evidence coverage;
- numeric support;
- named-anchor support;
- claim-qualifier support;
- exact-query coverage.

### Why v0.2.1 exists

The original stricter gate correctly blocked unsupported overclaims but introduced false refusals.

Two important calibrations were required.

#### Technical compounds

Lowercase technical compounds such as:

```text
power-electronics
thermal-management
battery-electric
fuel-cell
```

must not automatically become named entities.

True anchors such as:

```text
FAA
NASA
AetherWing
Zephyr-X
```

remain protected.

#### Claim qualifiers

The gate protects unsupported authority/overclaim language while avoiding false positives from ordinary technical language.

Examples of claims that should require direct evidence include:

```text
NASA mandates every...
FAA issued...
NASA assigns every...
universal...
worldwide...
```

---

## Facet-aware evidence retrieval

Configuration:

```text
configs/facet_retrieval_v0_1.yaml
```

Primary module:

```text
src/aeroragx/generation/facet_retrieval.py
```

The initial implementation targets a narrow synthesis pattern where a question asks what is shared by two explicit facets.

Example:

```text
What thermal-management challenges are shared by
battery-electric and fuel-cell aircraft?
```

The planner derives two deterministic facet searches, verifies semantic facet identity in returned chunks, balances evidence, removes duplicates, and adds original-query evidence.

The implementation falls back to ordinary retrieval if a required facet cannot be supported.

This behavior is intentionally deterministic and narrow. It is not an LLM-based planning agent.

---

## Provider hardening

Provider modules:

```text
src/aeroragx/generation/prompting.py
src/aeroragx/generation/guardrails.py
src/aeroragx/generation/structured_provider.py
src/aeroragx/generation/http_transport.py
src/aeroragx/generation/model_adapter.py
src/aeroragx/generation/provider_factory.py
```

Configurations:

```text
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml
configs/generation_openai_v0_1.yaml
```

Current configured remote provider:

```text
OpenAI Responses API
model: gpt-5.6-luna
```

### Prompt hardening

Provider prompts include:

- explicit prompt version;
- bounded query length;
- bounded evidence size;
- explicit evidence start/end markers;
- untrusted-evidence treatment;
- structured output requirements.

### Prompt-injection checks

Current heuristic regression patterns include:

- ignore previous/prior instructions;
- override system prompt;
- reveal hidden system prompt;
- developer-message injection;
- execute shell/tool command;
- role reassignment.

The project treats these checks as defense-in-depth, not proof that prompt injection is solved.

### Transport hardening

The structured provider supports:

- configurable timeout;
- bounded retries;
- retryable versus non-retryable transport errors;
- deterministic backoff;
- request IDs;
- usage telemetry;
- latency telemetry;
- estimated cost;
- secret redaction.

---

## Structured provider response

The provider returns structured data containing:

```text
answer
claims
insufficient_evidence
```

Each claim references evidence IDs.

The application rejects malformed states and unknown evidence IDs.

---

## Citation resolution

The provider is never the authority for citation metadata.

Instead:

```text
provider claim
    |
    v
evidence IDs
    |
    v
application lookup
    |
    v
authoritative citation records
```

Citation records preserve:

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

---

## Provider telemetry

Generation telemetry records provider behavior such as:

```text
provider_called
provider_bypassed
provider_call_policy_correct
attempts
retry behavior
latency
input tokens
output tokens
total tokens
estimated cost
request ID
```

The final v0.3 benchmark measured:

```text
Provider calls: 20
Provider bypasses: 12
Call-policy accuracy: 1.0
Total tokens: 58,915
Estimated cost: $0.103745
P50 latency: 5.6394 s
P95 latency: 7.6947 s
Retry rate: 0.0
```

---

## Failure behavior

### Insufficient evidence before provider

The provider is bypassed and AeroRAG-X returns:

```text
insufficient_evidence = true
claims = []
citations = []
source_documents = []
```

### Provider returns insufficient evidence

A validated refusal is returned when allowed by generation configuration.

### Unknown evidence ID

The provider response is rejected.

### Malformed structured payload

The provider response is rejected.

### Retryable provider/transport failure

The provider retries up to the configured limit.

### Non-retryable failure

The request fails immediately.

### Prompt injection under block policy

The provider invocation is blocked.

---

## Local validation

```bash
python -m pytest \
  tests/test_generation_guardrails.py \
  tests/test_structured_provider.py \
  tests/test_facet_retrieval.py \
  tests/test_sufficiency_hardening_v02.py \
  tests/test_sufficiency_hardening_v021.py \
  -v
```

Full repository gate:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy src/aeroragx
git diff --check
```

---

## Remote benchmark

Set `OPENAI_API_KEY` in the environment, then run:

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

Clear the key after use:

```bash
unset OPENAI_API_KEY
```

---

## Current limitations

- benchmark size remains small relative to production use;
- expected-term recall is lexical;
- no semantic entailment checker is applied to every claim;
- prompt-injection checks are heuristic;
- facet planning supports a narrow deterministic pattern;
- provider behavior can change across model/provider versions;
- no service-level rate limiting, auth, or request isolation exists yet.

These limitations are intentionally carried forward to the serving milestone rather than hidden by benchmark scores.
