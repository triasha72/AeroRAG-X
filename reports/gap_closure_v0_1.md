# Gap closure status v0.1

This report separates completed engineering work from measurements that require
artifacts, hardware, services, or human judgments not available on the current
host. A runnable code path is not marked as an empirical result.

## Closed with implementation and real measurement

| Gap | Action | Evidence |
|---|---|---|
| 1M rank crowding | Added best-child-per-parent collapse before final top-k | Recall@10 0.0467 → 0.0650; NDCG@10 0.0721 → 0.0903 |
| Duplicate-sensitive NDCG | Each relevant parent can contribute gain only once | Included in the frozen 1M ablation |
| Unbounded corpus-to-prompt growth | Preserved five-evidence funnel, 3,000-token context cap, 750-token chunk cap, and four-claim output cap | Versioned configuration and evidence builder |
| Estimated-only local-model budgeting | Added exact Transformers/MLX runtime-tokenizer counting and exact truncation | Evidence records identify `runtime_tokenizer` versus `stored_estimate` |
| Narrow metadata filtering | Added year, subject, type, program, and report-family filters | 101,622-row metadata completeness audit |
| Missing metadata treated ambiguously | Filters now exclude missing values explicitly | Program coverage measured at 66.64% of documents |
| Unreliable large-corpus process | Added bounded retries, incremental search-page processing, streaming counts/hashes, receipts, and compact parent-linked snapshots | Completed 100K breadth and 1M load snapshots |

## Partly closed

### Parent collapse

Quality improved, but the exact Python reference implementation added 22.47 ms
p50 and 63.14 ms p95 overhead. The policy is implemented in hierarchical
evidence selection. pgvector now also persists parent IDs and performs bounded
best-child grouping inside its candidate query, but production promotion still
requires measurement on a running database.

### Token reduction

The actual epoch-2 adapter was reconstructed by the complete three-epoch MPS
treatment and passed exact save/reload loss validation. The protected 32-query
Base/LoRA rerun then completed against the rebuilt, checksummed corpus and dense
index. Four claims did not close the verbosity gap: LoRA averaged 212.25 output
tokens per provider call versus 142.48 for Base. Citation coverage and validity
were perfect in both conditions, but LoRA had two generation failures versus
one and lower answerability, expected-term recall, and structural validity.
This closes the missing-evidence gap but leaves response-schema verbosity open.

### Metadata filters

The contract and completeness evidence are complete. Query-level filter quality
is not measured because the eight frozen queries have no independently annotated
filter intents. Inventing those labels after seeing results would contaminate
the protected benchmark.

## External evidence milestones still open

| Milestone | Missing dependency | Completion evidence required |
|---|---|---|
| Exact versus HNSW crossover | PostgreSQL process with System V shared-memory permission | Same snapshot/query set; HNSW parameters, Recall@10 loss, p50/p95, build time, index size, peak memory |
| Dense/hybrid/reranker 100K and 1M | embedding and reranker model artifacts plus adequate storage | Frozen inputs and end-to-end Recall/NDCG/latency/memory results |
| FSDP/DeepSpeed/Megatron and serving matrices | CUDA GPU host | Repeated preregistered runs with raw telemetry |
| Multimodal reliability | independent reviewers and expanded annotated assets | Versioned responses, agreement, adjudication, figure/table retrieval metrics |
| Broader statistical claims | larger independently judged query set | New qrels version; confidence intervals and slice analysis |

## Next executable order

1. Run paired successful-query verbosity analysis and evaluate a leaner response
   schema without changing retrieved evidence or citation validation.
2. Rerun the same 1M ablation through the implemented pgvector parent-collapse
   query and record its database-side overhead.
3. Run exact versus HNSW at a preregistered maximum Recall@10 loss.
4. Add independently annotated metadata-filter intents under a new query/qrels
   version and measure false exclusions.
5. Execute GPU and multimodal milestones only on hosts/review workflows that can
   produce the required evidence.

## Execution-environment validation

- PostgreSQL 17 and pgvector 0.8.6 were installed.
- An isolated cluster was attempted inside `work/pgdata`.
- PostgreSQL bootstrap failed at `shmget(...): Operation not permitted`; this
  sandbox blocks the required System V shared-memory operation before any
  database or index can be created.
- Normal macOS Terminal exposed MPS. The exact checkpoint runner completed 42
  optimizer steps, selected epoch 2, and reproduced dev loss after reload with
  a difference of 0.0. Staged validation then completed all 32 query attempts
  for both Base and LoRA.
