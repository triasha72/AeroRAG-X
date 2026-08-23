# Release readiness and operating boundaries

This runbook turns the existing evaluation artifacts into an explicit ship/no-ship decision. It does not claim that AeroRAG-X is a public multi-tenant service. The current deployment evidence covers private validation, bounded request handling, deterministic regression checks, and failure-aware service behavior.

Required evidence must be both present and finalized. The versioned readiness
policy rejects configured placeholder markers, so an ablation template with
`pending` values cannot satisfy the release gate merely because the file is
nonempty. The current GRPO gate remains open until measured Base, LoRA/SFT, and
GRPO results replace the template.

## What is measured

- Frozen deterministic generation regression over the committed evaluation set.
- Retrieval, reranking, answerability, citation, claim-support, completeness, redundancy, and unsupported-response evidence recorded under `artifacts/evaluation/` and `reports/`.
- Base, LoRA, and GRPO experiments under their documented evaluation contracts.
- Agent trajectory, retry, termination, checkpoint, interruption, human-review, and fault-injection behavior.
- Distributed-service reliability, request identity, Prometheus metrics, OpenTelemetry traces, and edge-runtime experiments.

## What remains experimental

- Model-training or post-training improvements that have not passed the protected held-out evaluation.
- Public multi-tenant operation, shared distributed rate limiting, authentication, and abuse prevention.
- Generalization beyond the frozen NASA technical corpus and evaluation questions.
- Multimodal retrieval beyond the committed report-slice and annotation foundations.
- Claims of surrogate benefit from adaptive retrieval where the protected evaluation found no improvement.

## Pre-deploy

1. Confirm the target commit is on `main` and GitHub Actions is green.
2. Run:

   ```bash
   python scripts/check_evaluation_regression.py
   python scripts/check_release_readiness.py
   pytest --cov=aeroragx --cov-fail-under=80
   ```

   The command exits nonzero while a release gate is open. CI uses
   `--allow-unready` only to publish the truthful report as a build artifact;
   that flag must not be used for an actual ship/no-ship decision.

3. Build the container from the target commit.
4. Record the image digest, commit SHA, model/config versions, corpus manifest checksum, and protected-evaluation manifest checksum.
5. Confirm production secrets are supplied by the deployment platform and are absent from images, logs, and environment snapshots.
6. Set query guardrails:

   ```text
   AERORAGX_MAX_REQUEST_BYTES=16384
   AERORAGX_RATE_LIMIT_REQUESTS=60
   AERORAGX_RATE_LIMIT_WINDOW_SECONDS=60
   ```

   The built-in rate limiter is process-local. Multi-instance deployments must also enforce a shared ingress or gateway limit.

## Pgvector backup and restore

Create a versioned logical backup before migrations or corpus reloads:

```bash
pg_dump --format=custom --no-owner --no-acl \
  --dbname="$AERORAGX_VECTOR_DATABASE_URL" \
  --file="aeroragx-pgvector-$(date +%Y%m%d-%H%M%S).dump"
```

Verify the archive without changing a database:

```bash
pg_restore --list aeroragx-pgvector-YYYYMMDD-HHMMSS.dump
```

Restore only into an empty staging database first:

```bash
createdb aeroragx_restore_check
pg_restore --clean --if-exists --no-owner --no-acl \
  --dbname=postgresql://localhost/aeroragx_restore_check \
  aeroragx-pgvector-YYYYMMDD-HHMMSS.dump
```

Run readiness and retrieval-equivalence checks against the restored staging database before promoting it. Never restore directly over the active database.

## Deploy and smoke test

1. Deploy privately to staging.
2. Verify `/health`, `/ready`, and `/metrics`.
3. Run the three demo cases:
   - answerable query with valid citations;
   - multi-evidence query;
   - unsupported query that must refuse.
4. Confirm `X-Request-ID` propagation and trace continuity across agent, retrieval, and inference services.
5. Confirm an oversized query returns `413` and an exceeded query rate returns `429`.
6. Watch error rate, provider failures, evidence insufficiency, retrieval latency, reranker latency, and total RAG latency.

## Rollback triggers

Rollback to the previous image digest when any of these occur:

- readiness fails or the query endpoint cannot complete the smoke suite;
- the frozen evaluation regression or release-readiness check fails;
- citation validity, claim support, or answerability falls below the committed policy;
- HTTP 5xx responses exceed 2% for five minutes;
- p95 total query latency is more than twice the recorded staging baseline for ten minutes;
- request IDs or trace continuity are missing for query traffic;
- secrets, raw evidence, or raw user queries appear in logs;
- pgvector retrieval differs from the committed NumPy equivalence contract.

Rollback is an image/config promotion, not an in-place patch. Preserve the failed deployment logs and trace IDs for diagnosis.

## Post-deploy

- Record the deployed image digest and commit SHA.
- Save smoke-test results and the generated release-readiness artifact.
- Monitor the rollback signals for at least 15 minutes.
- Update the changelog or release notes with measured changes and known limits.
