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

## Artifact identity

- Queries: `data/evaluation/source_grounded_queries_v0_1_512.jsonl`
- Qrels: `data/evaluation/source_grounded_qrels_v0_1_512.jsonl`
- Review template: `data/evaluation/source_grounded_review_v0_1_512.template.jsonl`
- Manifest: `data/evaluation/source_grounded_eval_v0_1_512_manifest.json`
- Corrected result SHA-256: `721c5065b2043932590050e3d69e5a53ee22e8d857c3c2400941636b888ae55b`
