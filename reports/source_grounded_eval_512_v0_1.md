# Source-grounded 512-case retrieval diagnostic v0.1

## Purpose and boundary

This artifact expands evaluation scale without pretending that automatic labels
are independent human judgments. It contains 512 distinct source-chunk cases
drawn deterministically across all 94 documents in the frozen 3,233-chunk NASA
NTRS corpus. Each query retains document, chunk, and page provenance.

Queries use six high-TF-IDF source terms. This is a reproducible lexical
retrieval and load diagnostic, not a natural-question generation-quality
benchmark. Its manifest prohibits describing it as independently validated
until the supplied 512-row review template is completed.

## Actual exact-BM25 result

| Metric | Raw chunks | Parent collapse |
|---|---:|---:|
| Queries | 512 | 512 |
| Recall@10 | 1.0000 | 1.0000 |
| NDCG@10 | 0.9764 | 0.9764 |
| P50 latency | 1.066 ms | 1.401 ms |
| P95 latency | 1.330 ms | 1.703 ms |
| Index build | 0.180 s | 0.180 s |

The high result is expected because query terms were selected from the relevant
chunk. It establishes deterministic source recovery and a 512-query throughput
baseline; it does not establish semantic generalization.

The first execution produced false zero recall and exposed an evaluator defect:
JSON `null` parent IDs were converted to the string `"None"`. The evaluator now
treats null parents as root chunks. A regression test protects that behavior,
and only the corrected rerun is retained.

## Actual neural retrieval result

The same 512 queries and qrels were then evaluated through every frozen local
retrieval stage. No queries were sampled or removed.

| Method | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| Dense MiniLM | 0.2500 | 0.3262 | 0.1773 | 0.2124 |
| Hybrid RRF | 0.5195 | 0.6523 | 0.3944 | 0.4550 |
| Cross-encoder reranker | 0.9238 | 0.9355 | 0.8058 | 0.8385 |

The reranker evaluated 10,240 query-candidate pairs in 188.758 seconds, or
18.433 ms per pair, at candidate depth 20. These results show that reranking
substantially improves source-chunk recovery for this lexical diagnostic. They
do not remove the automatic-query limitation described above.

## Artifact identity

- Queries: `data/evaluation/source_grounded_queries_v0_1_512.jsonl`
- Qrels: `data/evaluation/source_grounded_qrels_v0_1_512.jsonl`
- Review template: `data/evaluation/source_grounded_review_v0_1_512.template.jsonl`
- Manifest: `data/evaluation/source_grounded_eval_v0_1_512_manifest.json`
- Corrected result SHA-256: `721c5065b2043932590050e3d69e5a53ee22e8d857c3c2400941636b888ae55b`
- Dense report SHA-256: `230b9ecd812f4c821d86930518852248785e033368fd0d61932d0d17828ff977`
- Hybrid report SHA-256: `d51a947ffa85a4b6747851bae726fbccc235350103f2749a5d86658f40dcfd82`
- Reranker report SHA-256: `d34b1db59a5478896f2ab6f180988e92138a657c2e629c0291effad84e343268`
- Reranker latency SHA-256: `ab7798f96172d5b9468e31658b8d6e6623d13e8a3e1fbdcda9ed884a82300b49`
