# AeroRAG-X Architecture

AeroRAG-X is a retrieval-first, evidence-grounded system for aerospace technical knowledge.

The design keeps acquisition, processing, retrieval, reranking, sufficiency assessment, generation, citation resolution, and evaluation separable so that each stage can be tested and benchmarked independently.

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
 Evidence-sufficiency assessment
               |
        +------+------+
        |             |
        v             v
  sufficient      insufficient
        |             |
        v             v
 generation       grounded refusal
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
 generation evaluation
```

The current text pipeline operates over **3,233 citation-preserving NASA report chunks**.

---

## Design principles

### Retrieval first

Generation is downstream of retrieval and reranking. The generator does not directly search the corpus.

### Provenance first

Document ID, page ranges, URLs, chunk IDs, and source-document checksums are preserved from processing through final citations.

### Provider distrust

The provider is allowed to produce structured claims and refer to evidence IDs. It is not trusted to invent authoritative citation metadata.

### Fail closed on invalid citations

Unknown evidence IDs and invalid answer states are rejected.

### Refuse before generation when possible

The evidence-sufficiency gate can stop unsupported questions before a provider call.

### Evaluation before optimization

Each major retrieval/generation stage has a reproducible benchmark before additional complexity is added.

---

## Ingestion layer

Provides:

- NASA NTRS metadata search
- record normalization
- versioned corpus definitions
- manifest generation
- public PDF-link resolution
- streamed downloads
- `.part` temporary files
- checksum calculation
- acquisition receipts

Primary modules:

```text
src/aeroragx/ingestion/ntrs.py
src/aeroragx/ingestion/corpus.py
src/aeroragx/ingestion/acquisition.py
```

---

## Document-processing layer

Provides:

- checksum verification
- page-level PDF extraction
- empty-page preservation
- extraction receipts
- deterministic overlapping chunks
- page/document provenance
- citation URLs
- source URLs
- source-document checksums
- chunking receipts

Primary modules:

```text
src/aeroragx/processing/pdf.py
src/aeroragx/processing/chunking.py
```

Every processed chunk preserves:

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

---

## BM25 retrieval

Provides:

- tokenization
- in-memory inverted index
- configurable `k1`
- configurable `b`
- deterministic ranking
- citation-preserving results

Primary module:

```text
src/aeroragx/retrieval/bm25.py
```

---

## Dense retrieval

Provides:

- Sentence Transformer embeddings
- separate query/document encoding
- normalized embeddings
- NumPy persistence
- aligned chunk metadata
- versioned index manifest
- exact cosine-similarity search

Primary module:

```text
src/aeroragx/retrieval/dense.py
```

Current index:

```text
Model: sentence-transformers/all-MiniLM-L6-v2
Chunks: 3,233
Embedding dimension: 384
Normalization: enabled
Search: exact cosine similarity
```

---

## Hybrid retrieval

Provides:

- independent BM25 and dense retrieval
- Reciprocal Rank Fusion
- rank-based combination instead of raw-score addition
- deterministic candidate deduplication
- BM25/dense provenance preservation

Primary module:

```text
src/aeroragx/retrieval/hybrid.py
```

Configuration:

```text
configs/hybrid_v0_1.yaml
```

Fixed baseline:

```text
RRF k: 60
BM25 depth: 50
Dense depth: 50
Default output: 10
```

---

## Cross-encoder reranking

Provides:

- bounded reranking of Hybrid RRF candidates
- joint query/chunk scoring
- preservation of BM25, dense, and hybrid provenance
- deterministic tie-breaking
- scoring-only latency measurement
- generic retrieval-evaluation compatibility

Primary module:

```text
src/aeroragx/retrieval/reranker.py
```

Configuration:

```text
configs/reranker_v0_1.yaml
```

Current model:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

Default baseline:

```text
candidate_top_k: 20
default_top_k: 10
batch_size: 16
device: cpu
```

---

## Retrieval evaluation

Provides:

- natural-language query records
- relevance judgments
- Recall@5
- Recall@10
- MRR@10
- NDCG@10
- per-query metrics
- aggregate metrics
- shared retrieval protocols
- BM25 evaluation
- dense evaluation
- Hybrid RRF evaluation
- reranker evaluation

Primary modules:

```text
src/aeroragx/evaluation/retrieval.py
src/aeroragx/evaluation/pooling.py
```

Tracked reports:

```text
artifacts/evaluation/bm25_v0_1.json
artifacts/evaluation/dense_v0_1.json
artifacts/evaluation/bm25_v0_2.json
artifacts/evaluation/dense_v0_2.json
artifacts/evaluation/hybrid_v0_2.json
artifacts/evaluation/reranker_top10_v0_2.json
artifacts/evaluation/reranker_top20_v0_2.json
artifacts/evaluation/reranker_latency_v0_1.json
```

---

## Generation provider layer

Primary module:

```text
src/aeroragx/generation/provider.py
```

The provider interface receives:

```text
query
bounded evidence records
maximum claim count
```

and returns a structured response containing:

```text
answer
claims
insufficient_evidence
```

Each provider claim references evidence IDs rather than free-form URLs.

Current provider:

```text
DeterministicGenerationProvider
```

Purpose:

- local end-to-end pipeline validation
- deterministic tests
- no external credentials
- reproducible generation benchmarks

It is not a production neural LLM.

---

## Grounded-generation layer

Primary module:

```text
src/aeroragx/generation/grounded.py
```

Configuration:

```text
configs/generation_v0_1.yaml
```

Responsibilities:

1. request reranked evidence;
2. bound evidence depth;
3. bound per-chunk characters;
4. bound total context size;
5. reject duplicate reranked chunk IDs;
6. run optional evidence-sufficiency assessment;
7. refuse early when evidence is insufficient;
8. call the generation provider when evidence is sufficient;
9. validate provider evidence references;
10. resolve claims to authoritative citation records;
11. build deduplicated source-document summaries;
12. validate supported/refusal answer states;
13. attach retrieval/generation metadata.

### Evidence records

Each `GenerationEvidence` preserves:

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

### Citation trust boundary

The provider can say:

```text
claim → evidence ID E1
```

The application resolves `E1` to the authoritative stored evidence record and creates:

```text
citation ID
chunk ID
document ID
page range
NASA citation URL
source URL
checksum
reranker rank
```

This prevents a provider from becoming the source of truth for document provenance.

---

## Evidence-sufficiency layer

Primary module:

```text
src/aeroragx/generation/sufficiency.py
```

Configuration:

```text
configs/sufficiency_v0_1.yaml
```

The assessor checks:

```text
evidence count
informative query-term coverage
minimum supported terms
single-chunk evidence concentration
numeric support
named-anchor support
stricter exact-query coverage
```

Output:

```text
sufficient
evidence_count
query_terms
supported_terms
unsupported_terms
query_term_coverage
single_evidence_coverage
required_numeric_terms
supported_numeric_terms
required_named_anchors
supported_named_anchors
reasons
```

The result is stored inside:

```text
GroundedAnswer
└── retrieval_metadata
    └── evidence_sufficiency
```

When `sufficient=false`, the provider is skipped and the system returns an insufficient-evidence answer.

---

## Generation evaluation

Primary module:

```text
src/aeroragx/generation/evaluation.py
```

Query set:

```text
data/evaluation/generation_queries_v0_1.jsonl
```

Reports:

```text
artifacts/evaluation/generation_v0_1.json
artifacts/evaluation/generation_v0_2.json
```

Current metrics:

```text
answerability_accuracy
answerable_completion_rate
unsupported_refusal_rate
claim_citation_coverage_rate
citation_reference_validity_rate
source_document_coverage_rate
expected_term_recall
structural_validity_rate
```

### v0.1

```text
Answerability accuracy: 0.8000
Answerable completion: 1.0000
Unsupported refusal: 0.0000
Expected-term recall: 0.9130
Structural validity: 1.0000
```

### v0.2 with sufficiency gate

```text
Answerability accuracy: 1.0000
Answerable completion: 1.0000
Unsupported refusal: 1.0000
Expected-term recall: 0.9130
Structural validity: 1.0000
```

The v0.2 result demonstrates correct behavior on the current ten-query engineering benchmark. It does not establish broad answerability generalization.

---

## CLI composition

The CLI assembles the complete pipeline:

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
   v
EvidenceSufficiencyAssessor
   |
   v
GroundedAnswerGenerator
```

Important commands:

```text
ntrs-search
ntrs-build-manifest
ntrs-download-documents
ntrs-extract-pages
ntrs-build-chunks
ntrs-bm25-search
ntrs-build-dense-index
ntrs-dense-search
ntrs-hybrid-search
ntrs-reranker-search
ntrs-grounded-answer
ntrs-build-evaluation-candidates
ntrs-build-pooled-candidates
ntrs-build-qrels-from-annotations
ntrs-evaluate-bm25
ntrs-evaluate-dense
ntrs-evaluate-hybrid
ntrs-evaluate-reranker
ntrs-evaluate-generation
```

---

## Trust boundaries

AeroRAG-X separates four trust domains.

### 1. External source documents

NASA documents are external inputs.

Controls:

- acquisition receipts
- checksums
- page provenance
- source URLs

### 2. Retrieval outputs

Retrieval rankings are model outputs and may be wrong.

Controls:

- pooled relevance evaluation
- stage-specific metrics
- preserved rankings/scores
- reranking benchmarks

### 3. Retrieved text

Retrieved text is evidence, but future corpora must still be treated as untrusted prompt content.

Planned controls:

- prompt-injection defenses
- explicit data/instruction separation
- adversarial benchmark cases

### 4. Generation provider

The provider must not be trusted to invent provenance.

Current controls:

- structured provider schema
- bounded evidence IDs
- unknown evidence-ID rejection
- authoritative application-side citation resolution
- final answer schema validation

---

## Failure behavior

### No usable evidence

The system returns:

```text
insufficient_evidence = true
claims = []
citations = []
source_documents = []
```

### Sufficiency check fails

Same grounded refusal state is returned, with auditable sufficiency metadata.

### Provider references unknown evidence

The response is rejected.

### Provider marks insufficient evidence

The system produces a validated refusal when configuration permits it.

### Provider returns a supported state with no claims

The response is rejected.

### Claim references unknown citation ID

The final answer is rejected by schema validation.

---

## Current non-goals

The current milestone does not attempt to provide:

- production hosted LLM integration
- semantic entailment verification
- autonomous general-purpose agents
- large-scale vector database serving
- table/figure retrieval
- cloud deployment

Those capabilities are separate future milestones so they can be evaluated independently.

---

## Planned target architecture

```text
NASA NTRS + additional approved aerospace sources
                         |
                         v
              acquisition + validation
                         |
                         v
             multimodal document parsing
                         |
                         v
               text/table/figure units
                         |
              +----------+----------+
              |                     |
              v                     v
        sparse retrieval      vector database
              |                     |
              +----------+----------+
                         |
                         v
                  hybrid fusion
                         |
                         v
                 neural reranking
                         |
                         v
              sufficiency assessment
                         |
                         v
              hardened LLM provider
                         |
                         v
            citation/faithfulness checks
                         |
                         v
             tool-enabled research agent
                         |
                         v
                   FastAPI service
                         |
                         v
             interactive web interface
                         |
                         v
           observability + cloud deploy
```

---

## Next architectural milestone

Provider hardening introduces:

```text
src/aeroragx/generation/prompting.py
src/aeroragx/generation/guardrails.py
configs/provider_v0_1.yaml
```

with:

- explicit prompt templates
- prompt versioning
- retrieved-data delimiters
- structured response validation
- hosted/local provider adapters
- timeout/retry handling
- token/latency/cost telemetry
- prompt-injection regression cases

After that, the next architecture milestone is persistent vector infrastructure plus FastAPI serving.
