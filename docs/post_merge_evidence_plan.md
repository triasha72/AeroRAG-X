# Post-merge evidence plan

This plan distinguishes implemented machinery from research evidence. No phase
is complete merely because a runner exists.

## External natural-query evidence

Two revision-pinned NASA IMPACT datasets are registered in
`configs/external_benchmarks_v0_1.yaml`.

1. `nasa-science-repos-sme-benchmark` supplies 219 expert queries, 253 relevance
   judgments, and a 5,264-repository corpus. It is independent human-query
   evidence, but it evaluates NASA software discovery rather than NTRS passage
   retrieval and must be reported separately.
2. `nasa-sde-IR-benchmark-20251024-v5` supplies 176,901 queries over an 82,608
   document corpus. Its questions were generated with GPT-4o mini. A frozen
   500+ slice can establish throughput and scale, but cannot be described as
   independent human judgment.

Fetch either dataset with:

```bash
python scripts/fetch_external_nasa_benchmark.py nasa_sme
python scripts/fetch_external_nasa_benchmark.py nasa_sde_scale
```

The downloader pins the upstream revision and emits byte counts and SHA-256
digests. External results must not be merged numerically with AeroRAG-X's NTRS
benchmark because the corpora, tasks, and relevance policies differ.

## Reviewer alternatives

If two unpaid independent reviewers are unavailable, acceptable alternatives
are: contracted aerospace annotators under a written rubric; collaboration with
an aerospace lab or student society; one domain reviewer plus the independent
NASA SME benchmark, with the NTRS set still labeled singly reviewed; or public
blind annotation with qualification checks and adjudication. The project owner,
an LLM acting as a reviewer, and duplicated reviews from one person do not count
as two independent reviewers.

## PostgreSQL crossover

PostgreSQL 17.11 and pgvector 0.8.6 are installed. Both the default bootstrap
and an `mmap`-configured bootstrap fail in the current sandbox at
`shmget(...): Operation not permitted`. Run the crossover from normal macOS
Terminal or a Linux host. Preserve exact/HNSW configurations, dataset hashes,
query IDs, warm-up policy, build time, index size, p50/p95 latency, peak memory,
Recall@10, NDCG@10, and failures. A runner-only result is not a measurement.

## Independent public-claim audit

Populate `docs/public_claim_audit_v0_1.csv` with one row per numeric statement
in README, roadmap, portfolio, CV, and reports. A person who did not produce the
result must verify the artifact, commit, scope, and limitation. Self-audited
rows remain `pending_independent_review`.

## Release gate

Create a versioned reproducibility release only when all required rows in the
claim ledger have independent sign-off, the compact 32-query promotion decision
exists, default-branch CI is green, raw non-sensitive measurements and hashes
are published, and remaining limitations are explicit. GPU framework studies
remain optional extensions and must not block the core evidence release.
