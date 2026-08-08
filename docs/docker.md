# AeroRAG-X Docker Service

AeroRAG-X supports containerized execution of its FastAPI service. The Docker deployment uses the same shared retrieval and grounded-generation runtime as the command-line interface, evaluation workflows, and native FastAPI service.

The default local image is designed for deterministic CPU-based execution.

## Architecture

```text
Host machine
    |
    +-- processed NASA NTRS corpus
    +-- dense embedding artifacts
    |
    | read-only mounts
    v
Docker container
    |
    v
non-root AeroRAG-X process
    |
    v
FastAPI
    |
    +--> GET /health
    +--> GET /ready
    +--> POST /v1/query
    |
    v
shared AeroRAG runtime
    |
    v
BM25 + dense retrieval
    |
    v
Reciprocal Rank Fusion
    |
    v
cross-encoder reranking
    |
    v
facet-aware evidence retrieval
    |
    v
evidence-sufficiency gate
    |
    +----------------------+
    |                      |
    v                      v
sufficient             insufficient
evidence               evidence
    |                      |
    v                      v
generation              grounded
provider                refusal
    |
    v
claim-level citation resolution
    |
    v
grounded API response
```

## Docker image

The serving image uses:

- Python 3.12;
- CPU-only PyTorch;
- Sentence Transformers;
- FastAPI;
- Uvicorn;
- AeroRAG-X retrieval and generation packages.

The default image does not install the NVIDIA CUDA runtime. CPU-only PyTorch is installed before the project dependencies so `sentence-transformers` reuses that installation instead of resolving the Linux CUDA/NVIDIA dependency stack.

## Runtime artifact policy

Generated corpus and dense-index artifacts are intentionally not tracked in Git or baked into the serving image.

Required runtime files:

```text
data/processed/ntrs/v0_1/chunks.jsonl
artifacts/embeddings/ntrs_v0_1.npy
artifacts/embeddings/ntrs_v0_1_metadata.jsonl
artifacts/embeddings/ntrs_v0_1_manifest.json
```

They are mounted read-only at runtime. This keeps source control clean, separates application code from generated artifacts, and allows the local corpus/index snapshot to change without rebuilding the application image.

## Required local artifacts

```bash
test -r data/processed/ntrs/v0_1/chunks.jsonl \
  && echo "chunks: OK"

test -r artifacts/embeddings/ntrs_v0_1.npy \
  && echo "embeddings: OK"

test -r artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
  && echo "metadata: OK"

test -r artifacts/embeddings/ntrs_v0_1_manifest.json \
  && echo "manifest: OK"
```

All four files must be present.

## Build

```bash
unset OPENAI_API_KEY

docker build \
  --progress=plain \
  -t aeroragx:local \
  .
```

A clean rebuild can be forced with:

```bash
docker build \
  --no-cache \
  --progress=plain \
  -t aeroragx:local \
  .
```

Inspect:

```bash
docker image ls aeroragx:local
```

## Verify CPU-only PyTorch

```bash
docker run \
  --rm \
  --entrypoint python \
  aeroragx:local \
  -c 'import torch; print("Torch:", torch.__version__); print("CUDA available:", torch.cuda.is_available())'
```

Expected for the local CPU image:

```text
CUDA available: False
```

Verify Sentence Transformers:

```bash
docker run \
  --rm \
  --entrypoint python \
  aeroragx:local \
  -c 'import sentence_transformers; print("sentence-transformers: OK")'
```

## Run

```bash
docker run \
  -d \
  --name aeroragx-local \
  -p 8000:8000 \
  -e AERORAGX_RUNTIME_MODE=local \
  -e AERORAGX_CANDIDATE_TOP_K=20 \
  -e AERORAGX_EVIDENCE_TOP_K=5 \
  -v "$PWD/data/processed:/app/data/processed:ro" \
  -v "$PWD/artifacts/embeddings:/app/artifacts/embeddings:ro" \
  aeroragx:local
```

The corpus and embedding mounts are read-only.

## Startup

```bash
docker logs -f aeroragx-local
```

Wait for:

```text
Application startup complete.
```

Exit log following with `Ctrl+C`. Because the container was launched in detached mode, this does not stop the service.

## Health

```bash
curl -sS http://127.0.0.1:8000/health
echo
```

Expected:

```json
{"status":"ok"}
```

## Readiness

```bash
curl -sS http://127.0.0.1:8000/ready
echo
```

Expected:

```json
{"status":"ready","ready":true}
```

Docker health:

```bash
docker inspect \
  --format '{{.State.Health.Status}}' \
  aeroragx-local
```

Expected after startup:

```text
healthy
```

## Non-root execution

The service is configured to execute as UID/GID `10001:10001`.

```bash
docker exec aeroragx-local id
```

The service must not execute as root.

## Verify artifact mounts

```bash
docker exec \
  aeroragx-local \
  sh -c '
    ls -lh \
      /app/data/processed/ntrs/v0_1/chunks.jsonl \
      /app/artifacts/embeddings/ntrs_v0_1.npy \
      /app/artifacts/embeddings/ntrs_v0_1_metadata.jsonl \
      /app/artifacts/embeddings/ntrs_v0_1_manifest.json
  '
```

## Grounded NASA query

```bash
curl -sS \
  -D /tmp/aeroragx_docker_headers.txt \
  -o /tmp/aeroragx_docker_response.json \
  -X POST \
  http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query":
    "What thermal-management challenges are shared by battery-electric and fuel-cell aircraft?"
  }'
```

Inspect:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path("/tmp/aeroragx_docker_response.json").read_text(
        encoding="utf-8"
    )
)

metadata = data["retrieval_metadata"]

print("Insufficient:", data["insufficient_evidence"])
print("Claims:", len(data["claims"]))
print("Citations:", len(data["citations"]))
print("Sources:", len(data["source_documents"]))
print("Provider:", metadata["generation_provider"])
print("Model:", metadata["generation_model"])
PY
```

For the deterministic local runtime, the result should have supported claims and citations and report:

```text
Provider: fake
Model: deterministic-grounded-v0
```

## Request IDs

```bash
grep -i \
  "x-request-id" \
  /tmp/aeroragx_docker_headers.txt
```

Expected:

```text
x-request-id: <UUID>
```

The application-generated request ID remains separate from any external provider request ID.

## Environment configuration

Supported serving variables:

```text
AERORAGX_RUNTIME_MODE
AERORAGX_CANDIDATE_TOP_K
AERORAGX_EVIDENCE_TOP_K
```

The local container uses:

```text
AERORAGX_RUNTIME_MODE=local
```

OpenAI-backed execution can inject `OPENAI_API_KEY` securely at runtime. API keys must never be copied into the Dockerfile, image, Git history, tracked configuration, or logs.

## Reproducible smoke test

The repository provides:

```text
scripts/docker_smoke.sh
```

After building the image:

```bash
./scripts/docker_smoke.sh
```

The script validates:

- required runtime artifacts;
- container startup;
- health and readiness;
- non-root execution;
- artifact mounts;
- a real NASA-backed grounded query;
- claim and citation presence;
- deterministic local provider selection;
- `X-Request-ID`.

## CI policy

GitHub Actions builds the Docker image from tracked repository contents. The standard CI workflow does not execute the full NASA-backed container integration test because the generated corpus and dense-index artifacts are intentionally excluded from Git.

The full `scripts/docker_smoke.sh` run remains a local or artifact-enabled integration test.

## Stop and remove

```bash
docker stop aeroragx-local
docker rm aeroragx-local
```

The image remains available until explicitly removed.

## Current limitations

The Docker milestone does not yet provide:

- structured JSON service logging;
- distributed tracing;
- OpenTelemetry instrumentation;
- managed model-cache persistence;
- cloud deployment;
- managed secret storage;
- authentication;
- rate limiting;
- autoscaling;
- persistent vector-database serving.

## Next milestone

```text
Dockerized FastAPI
        |
        v
structured JSON logging
        |
        v
request-ID correlation
        |
        v
retrieval/reranker timing
        |
        v
provider telemetry correlation
        |
        v
latency/error metrics
        |
        v
OpenTelemetry
```
