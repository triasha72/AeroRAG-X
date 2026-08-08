#!/usr/bin/env bash

set -euo pipefail

IMAGE="${AERORAGX_DOCKER_IMAGE:-aeroragx:local}"
CONTAINER="${AERORAGX_DOCKER_CONTAINER:-aeroragx-smoke}"
PORT="${AERORAGX_DOCKER_PORT:-8000}"

CHUNKS="data/processed/ntrs/v0_1/chunks.jsonl"
EMBEDDINGS="artifacts/embeddings/ntrs_v0_1.npy"
METADATA="artifacts/embeddings/ntrs_v0_1_metadata.jsonl"
MANIFEST="artifacts/embeddings/ntrs_v0_1_manifest.json"

cleanup() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "Checking required AeroRAG-X runtime artifacts..."

for artifact in \
    "$CHUNKS" \
    "$EMBEDDINGS" \
    "$METADATA" \
    "$MANIFEST"
do
    if [[ ! -r "$artifact" ]]; then
        echo "Missing required artifact: $artifact" >&2
        exit 1
    fi
done

echo "Runtime artifacts: PASS"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Docker image not found: $IMAGE" >&2
    echo "Build it first with:" >&2
    echo "  docker build -t $IMAGE ." >&2
    exit 1
fi

cleanup

echo "Starting container: $CONTAINER"

docker run \
    -d \
    --name "$CONTAINER" \
    -p "$PORT:8000" \
    -e AERORAGX_RUNTIME_MODE=local \
    -e AERORAGX_CANDIDATE_TOP_K=20 \
    -e AERORAGX_EVIDENCE_TOP_K=5 \
    -v "$PWD/data/processed:/app/data/processed:ro" \
    -v "$PWD/artifacts/embeddings:/app/artifacts/embeddings:ro" \
    "$IMAGE" \
    >/dev/null

echo "Waiting for AeroRAG-X readiness..."

READY=0

for _ in $(seq 1 180)
do
    if curl \
        --fail \
        --silent \
        --show-error \
        "http://127.0.0.1:$PORT/ready" \
        >/tmp/aeroragx_docker_ready.json \
        2>/dev/null
    then
        READY=1
        break
    fi

    if ! docker ps \
        --format '{{.Names}}' \
        | grep -qx "$CONTAINER"
    then
        echo "Container exited during startup." >&2
        docker logs "$CONTAINER" >&2
        exit 1
    fi

    sleep 2
done

if [[ "$READY" -ne 1 ]]; then
    echo "Container did not become ready." >&2
    docker logs "$CONTAINER" >&2
    exit 1
fi

echo "Readiness: PASS"

curl \
    --fail \
    --silent \
    --show-error \
    "http://127.0.0.1:$PORT/health" \
    >/tmp/aeroragx_docker_health.json

echo "Health: PASS"

USER_ID="$(
    docker exec \
        "$CONTAINER" \
        id -u
)"

if [[ "$USER_ID" == "0" ]]; then
    echo "Container is running as root." >&2
    exit 1
fi

echo "Non-root runtime: PASS (uid=$USER_ID)"

docker exec "$CONTAINER" test -r /app/data/processed/ntrs/v0_1/chunks.jsonl
docker exec "$CONTAINER" test -r /app/artifacts/embeddings/ntrs_v0_1.npy
docker exec "$CONTAINER" test -r /app/artifacts/embeddings/ntrs_v0_1_metadata.jsonl
docker exec "$CONTAINER" test -r /app/artifacts/embeddings/ntrs_v0_1_manifest.json

echo "Artifact mounts: PASS"

curl \
    --fail \
    --silent \
    --show-error \
    -D /tmp/aeroragx_docker_headers.txt \
    -o /tmp/aeroragx_docker_response.json \
    -X POST \
    "http://127.0.0.1:$PORT/v1/query" \
    -H "Content-Type: application/json" \
    -d '{
      "query":
      "What thermal-management challenges are shared by battery-electric and fuel-cell aircraft?"
    }'

python - <<'PY'
import json
from pathlib import Path

response = json.loads(
    Path("/tmp/aeroragx_docker_response.json").read_text(
        encoding="utf-8"
    )
)

metadata = response["retrieval_metadata"]

assert response["insufficient_evidence"] is False
assert len(response["claims"]) > 0
assert len(response["citations"]) > 0
assert len(response["source_documents"]) > 0
assert metadata["generation_provider"] == "fake"
assert metadata["generation_model"] == "deterministic-grounded-v0"

headers = Path("/tmp/aeroragx_docker_headers.txt").read_text(
    encoding="utf-8"
).lower()

assert "x-request-id:" in headers

print("Grounded query: PASS")
print("Claims:", len(response["claims"]))
print("Citations:", len(response["citations"]))
print("Sources:", len(response["source_documents"]))
print("Provider:", metadata["generation_provider"])
print("Model:", metadata["generation_model"])
PY

echo "X-Request-ID: PASS"
echo "Docker smoke test: PASS"
