# AeroRAG-X Architecture

AeroRAG-X is a retrieval-first, evidence-grounded system for aerospace technical knowledge.

The architecture separates acquisition, processing, retrieval, reranking, facet-aware evidence selection, evidence sufficiency, provider execution, citation resolution, and evaluation so that each stage can be tested independently.

---

## Implemented end-to-end pipeline

```text
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
 generation + provider telemetry
```

The current text pipeline operates over **3,233 citation-preserving NASA report chunks**.

---

## Design principles

### Retrieval first

Generation is downstream of retrieval. The provider never directly searches the corpus.

### Provenance first

Document IDs, page ranges, URLs, chunk IDs, and source-document checksums survive from processing through final citations.

### Provider distrust

The provider may produce structured claims and refer to evidence IDs. It is not trusted to create authoritative citation metadata.

### Retrieved text is untrusted input

Retrieved documents are evidence, not instructions. Provider prompts use explicit evidence delimiters and prompt-injection checks.

### Fail closed

Unknown evidence IDs, malformed structured outputs, unsupported answer states, and insufficient evidence are rejected rather than silently accepted.

### Refuse before paying when possible

The evidence-sufficiency gate can bypass the remote provider for unsupported questions.

### Narrow deterministic complexity before agentic complexity

Facet-aware retrieval uses a deterministic planner for a supported synthesis pattern instead of an unconstrained LLM query planner.

### Evaluation before optimization

Every major retrieval/generation capability is paired with a benchmark or deterministic regression test before the next architectural layer is added.

---

## Ingestion layer

Primary modules:

```text
src/aeroragx/ingestion/ntrs.py
src/aeroragx/ingestion/corpus.py
src/aeroragx/ingestion/acquisition.py
```

Responsibilities:

- NASA NTRS metadata search
- record normalization
- versioned corpus definitions
- manifest generation
- PDF-link resolution
- streamed downloads
- temporary `.part` files
- checksum calculation
- acquisition receipts
- NASA citation/source URL preservation

---

## Processing layer

Primary modules:

```text
src/aeroragx/processing/pdf.py
src/aeroragx/processing/chunking.py
```

Each `ChunkRecord` preserves:

```text
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
```

The processing layer is deterministic and provenance preserving.

---

## Retrieval stack

### BM25

```text
src/aeroragx/retrieval/bm25.py
```

Provides lexical retrieval with deterministic ranking and chunk provenance.

### Dense retrieval

```text
src/aeroragx/retrieval/dense.py
```

Current baseline:

```text
Model: sentence-transformers/all-MiniLM-L6-v2
Chunks: 3,233
Dimension: 384
Normalization: enabled
Search: exact cosine similarity
Storage: NumPy
```

### Hybrid retrieval

```text
src/aeroragx/retrieval/hybrid.py
```

Uses Reciprocal Rank Fusion instead of adding incompatible lexical and dense raw scores.

Baseline:

```text
RRF k: 60
BM25 depth: 50
Dense depth: 50
```

### Cross-encoder reranking

```text
src/aeroragx/retrieval/reranker.py
```

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Generation currently reranks a bounded hybrid candidate set with:

```text
candidate_top_k: 20
evidence_top_k: 5
```

---

## Facet-aware evidence selection

Primary module:

```text
src/aeroragx/generation/facet_retrieval.py
```

Configuration:

```text
configs/facet_retrieval_v0_1.yaml
```

This layer wraps the reranked index.

### Ordinary query

```text
query
  |
  v
RerankerIndex.search()
  |
  v
top-k evidence
```

### Supported multi-facet synthesis query

```text
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
```

The semantic verifier requires the selected chunk to contain the facet identity terms. A hit does not qualify as facet evidence merely because it ranked for a facet query.

If a required facet lacks semantic matches, the wrapper falls back to ordinary original-query retrieval.

Current scope is intentionally narrow. It is not a general-purpose query decomposition engine.

---

## Evidence-sufficiency layer

Primary module:

```text
src/aeroragx/generation/sufficiency.py
```

Current production benchmark config:

```text
configs/sufficiency_v0_2_1.yaml
```

The assessor checks:

```text
minimum evidence count
informative query-term coverage
minimum supported terms
single-evidence coverage
numeric support
named-anchor support
claim-qualifier support
stricter exact-query coverage
```

The result includes auditable reasons and is preserved in retrieval metadata.

### Important calibration behavior

Sufficiency v0.2.1 distinguishes:

```text
power-electronics       ordinary technical compound
thermal-management      ordinary technical compound

FAA                     named anchor
AetherWing              named anchor
Zephyr-X                named anchor
```

It also distinguishes ordinary semantic use from unsupported authority claims. For example, a phrase like "components require thermal management" is not treated the same as an unsupported regulatory mandate.

---

## Provider layer

### Provider protocol

The generation provider receives:

```text
query
bounded evidence records
maximum claim count
```

and returns:

```text
answer
claims
insufficient_evidence
```

Provider claims reference evidence IDs, not arbitrary source URLs.

### Implementations

Deterministic/local provider:

```text
src/aeroragx/generation/provider.py
```

Structured remote provider:

```text
src/aeroragx/generation/structured_provider.py
src/aeroragx/generation/http_transport.py
src/aeroragx/generation/model_adapter.py
src/aeroragx/generation/provider_factory.py
```

Prompt/guardrails:

```text
src/aeroragx/generation/prompting.py
src/aeroragx/generation/guardrails.py
```

OpenAI benchmark configuration:

```text
configs/generation_openai_v0_1.yaml
configs/provider_v0_1.yaml
configs/http_transport_openai_v0_1.yaml
configs/provider_runtime_openai_v0_1.yaml
```

Current configured model:

```text
gpt-5.6-luna
```

---

## Provider hardening

The hardened provider path includes:

```text
versioned prompt configuration
evidence delimiters
prompt-injection assessment
structured response schema
bounded retries
timeouts
retryable/non-retryable transport errors
usage telemetry
request IDs
latency telemetry
estimated cost
secret redaction
```

Prompt-injection regression tests include patterns for:

- ignoring previous instructions;
- overriding system prompts;
- revealing hidden prompts;
- developer-message injection;
- tool/shell execution requests;
- role reassignment.

Structured-provider tests cover:

- normal success;
- response-schema presence;
- retryable transport failures;
- retry limits;
- non-retryable errors;
- malformed provider payloads;
- telemetry accounting.

---

## Grounded-generation layer

Primary module:

```text
src/aeroragx/generation/grounded.py
```

Responsibilities:

1. obtain bounded reranked/facet-aware evidence;
2. build `GenerationEvidence`;
3. run evidence sufficiency;
4. bypass provider when evidence is insufficient;
5. call the configured provider when sufficient;
6. validate provider evidence references;
7. resolve claim references to authoritative citations;
8. construct deduplicated source-document summaries;
9. validate supported/refusal answer states;
10. attach retrieval and provider telemetry.

### Generation evidence

Each evidence record preserves:

```text
evidence_id
chunk_id
document_id
page_start
page_end
text
citation_url
source_url
document_sha256
reranker_rank
reranker_score
hybrid_rank
hybrid_score
retrieved_by
bm25_rank
bm25_score
dense_rank
dense_score
```

### Final answer

```text
query
answer
claims
citations
source_documents
insufficient_evidence
retrieval_metadata
```

---

## Citation trust boundary

Provider output may say:

```text
CL1 -> E1, E3
```

The application resolves those evidence IDs to trusted stored metadata and creates citation records.

The provider does not supply the authoritative:

```text
document ID
page range
NASA citation URL
source URL
checksum
```

This prevents the model from becoming the source of truth for provenance.

---

## Generation evaluation

Primary modules:

```text
src/aeroragx/generation/evaluation.py
src/aeroragx/generation/telemetry_evaluation.py
```

Benchmark:

```text
data/evaluation/generation_queries_v0_3.jsonl
```

Final reports:

```text
artifacts/evaluation/generation_openai_v0_3_final.json
artifacts/evaluation/generation_openai_v0_3_final_telemetry.json
artifacts/evaluation/generation_v0_3_final_comparison.json
```

### Final v0.3

```text
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
```

These values describe the current engineering benchmark only.

---

## CLI composition

The CLI now composes:

```text
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
GroundedAnswerGenerator
                 |
                 v
Configured GenerationProvider
```

Important generation options include:

```text
--generation-config
--sufficiency-config
--facet-retrieval-config
--provider-config
--http-transport-config
--provider-runtime-config
--candidate-top-k
--evidence-top-k
```

---

## Trust domains

### 1. External documents

Controls:

- checksums
- acquisition receipts
- page provenance
- source URLs

### 2. Retrieval/reranking outputs

Controls:

- pooled evaluation
- stage-specific metrics
- ranking provenance
- deterministic tie-breaking

### 3. Retrieved evidence text

Controls:

- explicit data delimiters
- prompt-injection checks
- fail-closed policy when configured

### 4. Generation provider

Controls:

- structured schema
- bounded evidence references
- retries/timeouts
- malformed-response rejection
- application-side citation resolution
- telemetry

### 5. Serving layer

Not yet implemented. The next milestone must add API validation, request IDs, structured errors, and secret-safe logging.

---

## Failure behavior

### Evidence insufficiency

```text
provider called = false
insufficient_evidence = true
claims = []
citations = []
source_documents = []
```

### Missing semantic facet

Facet-aware retrieval falls back to ordinary original-query retrieval.

### Prompt injection detected under block policy

Provider invocation is blocked.

### Unknown evidence reference

Provider response is rejected.

### Malformed provider response

Provider response is rejected.

### Retryable transport error

The provider retries up to the configured bound and records telemetry.

### Non-retryable transport error

The provider fails immediately.

---

## Current non-goals

The current milestone does not yet provide:

- FastAPI serving;
- Dockerized deployment;
- managed secret storage;
- distributed tracing;
- vector-database serving;
- autonomous general-purpose agents;
- semantic entailment verification;
- table/figure retrieval;
- cloud deployment.

---

## Next architecture milestone

```text
AeroRAG-X core
      |
      v
FastAPI application
      |
      +--> GET /health
      +--> GET /ready
      +--> POST /v1/query
      |
      v
request IDs + structured errors
      |
      v
Docker container
      |
      v
structured telemetry/logging
      |
      v
cloud deployment
```

The serving layer should reuse the already-tested retrieval/generation core rather than duplicate it.
