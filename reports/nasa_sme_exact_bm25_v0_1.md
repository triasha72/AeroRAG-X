# NASA SME external BM25 evaluation v0.1

AeroRAG-X began with NTRS passage retrieval, so its internal diagnostic sets
could not answer a separate question: does the retrieval approach transfer to
questions written independently by NASA subject-matter experts? We selected
NASA IMPACT's revision-pinned software-repository benchmark because it supplies
real expert queries and relevance judgments. We rejected combining it with the
NTRS scores because the corpus and task are different.

The downloaded revision contains 5,264 repositories and 219 expert queries.
Only 212 queries have relevance judgments; the seven unjudged queries were
reported and excluded rather than scored as failures. Inspection of the pinned
files found 259 relevance rows, correcting the earlier planning estimate of
253. The evaluator indexed repository names, titles, descriptions, topics,
cleaned README text, and additional context with exact BM25 (`k1=1.5`,
`b=0.75`).

| Metric | Measured result |
|---|---:|
| Corpus repositories | 5,264 |
| Total / judged queries | 219 / 212 |
| Relevance rows | 259 |
| Mean Recall@10 | 0.5889 |
| Mean NDCG@10 | 0.4725 |
| Index construction | 1.21 s |
| Query latency p50 / p95 | 8.60 / 12.66 ms |

These are real local exact-BM25 measurements from the pinned external dataset.
They support cross-dataset software-discovery evidence, not NTRS passage-quality
or generation-quality claims. Timing is limited to this host and run; the
quality metrics are reproducible from the recorded rankings and input hashes.
The complete 212-query observations are stored in
`artifacts/evaluation/nasa_sme_exact_bm25_v0_1.json`.

The generated NASA SDE dataset remains a separate scale experiment. Its model-
generated questions cannot be presented as independent human review.
