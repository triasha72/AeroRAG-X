#!/usr/bin/env bash
set -euo pipefail

: "${AERORAGX_VECTOR_DATABASE_URL:?Set AERORAGX_VECTOR_DATABASE_URL first}"

python scripts/load_pgvector.py --config configs/vector_store_exact_v0_1.yaml
python scripts/benchmark_vector_backends.py \
  --config configs/vector_store_exact_v0_1.yaml \
  --output artifacts/evaluation/vector_backend_exact_v0_1.json

python scripts/load_pgvector.py --config configs/vector_store_hnsw_v0_1.yaml
python scripts/benchmark_vector_backends.py \
  --config configs/vector_store_hnsw_v0_1.yaml \
  --output artifacts/evaluation/vector_backend_hnsw_v0_1.json

python - <<'PY'
import json
from pathlib import Path

exact = json.loads(Path("artifacts/evaluation/vector_backend_exact_v0_1.json").read_text())
hnsw = json.loads(Path("artifacts/evaluation/vector_backend_hnsw_v0_1.json").read_text())
summary = {
    "version": "0.1",
    "query_count": exact["query_count"],
    "corpus_chunk_count": exact["corpus_chunk_count"],
    "exact": exact["pgvector"],
    "hnsw": hnsw["pgvector"],
    "hnsw_recall_at_10_delta": (
        hnsw["pgvector"]["recall_at_10"] - exact["pgvector"]["recall_at_10"]
    ),
    "promotable": (
        hnsw["pgvector"]["recall_at_10"]
        >= exact["pgvector"]["recall_at_10"] - 0.01
        and hnsw["pgvector"]["latency"]["p95_ms"]
        < exact["pgvector"]["latency"]["p95_ms"]
    ),
}
Path("artifacts/evaluation/vector_backend_crossover_v0_1.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(json.dumps(summary, indent=2))
PY
