# Retrieval scaling v0.1

## Decision

AeroRAG-X now has three measured exact-BM25 checkpoints: real NTRS breadth at
10K and 100K chunks, followed by a one-million-segment real-text load test.
Corpus size remains independent of the LoRA prompt: retrieval is bounded,
overlap is removed, document diversity is enforced, context is capped at 3,000
estimated tokens, and generation is capped at four claims.

## Why this sequence was chosen

The project first expanded real source breadth to 100,614 chunks because a
large synthetic corpus would measure machinery but not aerospace retrieval.
The development host then had roughly 5.1 GiB free and external NTRS breadth
expansion did not progress reliably. Repeating full document metadata or
retaining PDFs and embeddings would have exceeded that constraint.

For the one-million milestone, the selected alternative was a normalized
load-scale snapshot: 32-word segments with 8-word overlap, derived only from
the frozen real NASA text and linked to their parent chunks. This is useful for
testing index and ranking pressure. It is deliberately not described as a
one-million-chunk breadth study.

Rejected alternatives were:

- synthetic distractor text, because it cannot support retrieval-quality claims;
- copying the same full chunks until the target was reached, because it hides
  duplication behind a larger count;
- promoting HNSW before measuring exact-search behavior, because faster search
  is not valuable if the quality loss is unknown;
- sending more retrieved chunks to LoRA, because corpus scale should not inflate
  prompt tokens or weaken the evidence boundary.

## Frozen inputs and method

- queries: `data/evaluation/queries_v0_1.jsonl` (8)
- judgments: `data/evaluation/qrels_v0_2.jsonl`
- exact BM25: `k1=1.5`, `b=0.75`, query-term postings
- 10K SHA-256: `73dd8e735de70fcbb331bd63d2413391aef45ab60342ddaf2b5ef493b0a97efe`
- 100K-prefix SHA-256: `7744c8a8f217710acb5ab32afaea3fde4846c623c6a20a6706d518bee25be3a5`
- 1M SHA-256: `c4fbe18f16f316f9d5f220eccbb3a063d198eb14e940a3043eb7b752987f158e`

## Results

| Snapshot | Role | Recall@10 | NDCG@10 | p50 ms | p95 ms | index build s |
|---|---|---:|---:|---:|---:|---:|
| 10,060 | real NTRS breadth | 0.2275 | 0.2793 | 7.05 | 11.39 | not recorded |
| 100,614 | real NTRS breadth | 0.2136 | 0.2476 | 31.63 | 71.15 | 10.00 |
| 1,000,000 | real-text segment load | 0.0467 | 0.0721 | 32.93 | 106.15 | 13.98 |

The 100K result preserves most of the 10K quality while increasing tail
latency. The 1M result is a controlled failure: fine overlapping segments from
the same parent passage occupy multiple top-ten positions. Evaluation maps
segments back to judged parent chunks, but rank slots remain consumed. The
result establishes parent-level collapsing and hierarchical retrieval as the
next measured intervention.

## Parent-collapse ablation

The intervention was implemented and rerun on the exact same 1M snapshot. Each
parent keeps its highest-scoring child before the final top ten are selected;
duplicate parents also receive relevance gain only once.

| Ranking | Recall@10 | NDCG@10 | p50 ms | p95 ms |
|---|---:|---:|---:|---:|
| raw segments | 0.0467 | 0.0721 | 32.99 | 108.12 |
| best child per parent | 0.0650 | 0.0903 | 55.46 | 170.78 |

Recall improved by 39.2% relative and NDCG improved by 25.3% relative. The
Python reference implementation added 22.47 ms p50 and 63.14 ms p95 collapse
overhead because it scans and groups the touched posting set. The quality gap
is partly closed, while the latency result rejects this implementation as the
production form. A bounded best-child query is now implemented in pgvector;
its latency remains unmeasured because no database service is available here.

Report SHA-256:
`a3910380453e1ec4bb78938e9e4af685458931bd1fbea82c3092a88e27bd7b3e`.

## Metadata readiness

The real 101,622-row corpus contains 1,112 documents. Publication year, subject
categories, document type, and report family are present for every document;
program metadata is present for 66.64%. Consequently, the first four fields are
safe to expose as explicit filters, while program filtering remains opt-in and
must report that missing metadata is excluded. The audit does not establish a
quality gain because the frozen queries do not contain independently annotated
filter intents.

## Research benefit and next experiment

The experiment separates three concerns that are often conflated: source
breadth, addressable chunk count, and prompt size. It shows that merely making
chunks smaller can increase index scale while harming useful top-k diversity.
The next preregistered comparison should measure the new pgvector collapse
query, apply the bounded cross-encoder funnel to the same snapshots, then
compare exact search with HNSW at a fixed recall-loss tolerance. Only after that
crossover is measured should ANN become the default.

These results do not establish dense, hybrid, reranker, or HNSW performance,
and eight frozen queries are too small for broad statistical claims.
