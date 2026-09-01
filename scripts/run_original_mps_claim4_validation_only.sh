#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

python_bin="work/train-venv/bin/python"
model_file="work/models/Qwen3-0.6B/model.safetensors"
adapter_dir="artifacts/training/adapters/aeroragx_lora_v0_1_reproduced_mps"
adapter_file="$adapter_dir/adapter_model.safetensors"
chunks_file="data/processed/ntrs/v0_1/chunks.jsonl"
training_report="artifacts/evaluation/aeroragx_lora_training_reproduced_mps_v0_1.json"
embeddings_file="artifacts/embeddings/ntrs_v0_1.npy"
embedding_metadata="artifacts/embeddings/ntrs_v0_1_metadata.jsonl"
embedding_manifest="artifacts/embeddings/ntrs_v0_1_manifest.json"

require_sha() {
  path=$1
  expected=$2
  actual=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$actual" = "$expected" ] || {
    echo "Checksum mismatch: $path" >&2
    echo "expected=$expected" >&2
    echo "actual=$actual" >&2
    exit 1
  }
}

require_sha "$model_file" "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"
require_sha "$adapter_file" "13df5eb8449d5b204c2d740b0c194b7712969f15258c42b26a336febeb27c717"
require_sha "$chunks_file" "67ce4f814db096a0d49117fde9c924c7ae8825ea3c631463255e4fde0e3706c2"

PYTHONPATH=src "$python_bin" - <<'PY'
import json
from pathlib import Path

from aeroragx.retrieval.bm25 import load_chunk_records
from aeroragx.retrieval.dense import load_dense_index

report = json.loads(
    Path("artifacts/evaluation/aeroragx_lora_training_reproduced_mps_v0_1.json").read_text()
)

expected = {
    "status": "complete",
    "best_epoch": 2,
    "optimizer_steps_completed": 42,
    "reload_difference": 0.0,
}
for key, value in expected.items():
    if report.get(key) != value:
        raise SystemExit(f"Training report mismatch for {key}: {report.get(key)!r} != {value!r}")

corpus = load_chunk_records(Path("data/processed/ntrs/v0_1/chunks.jsonl"))
embeddings, dense_chunks, manifest = load_dense_index(
    embeddings_path=Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_path=Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_path=Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
)
if embeddings.shape != (3233, 384):
    raise SystemExit(f"Dense embedding shape mismatch: {embeddings.shape!r}")
if manifest.model_name != "sentence-transformers/all-MiniLM-L6-v2":
    raise SystemExit(f"Dense model mismatch: {manifest.model_name!r}")
if [chunk.chunk_id for chunk in corpus] != [chunk.chunk_id for chunk in dense_chunks]:
    raise SystemExit("Dense metadata is not aligned to the frozen corpus.")

print("COMPLETED CHECKPOINT PREFLIGHT: PASS", flush=True)
print("FROZEN DENSE INDEX PREFLIGHT: PASS", flush=True)
PY

PYTHONPATH=src "$python_bin" -c 'import torch; assert torch.backends.mps.is_available(), "Apple MPS is unavailable"'

echo "=== BASE CLAIM-4 VALIDATION ==="
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_1.yaml \
  --provider-runtime-config configs/transformers_runtime_local_base_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_transformers_base_claim4_v0_1.json \
  --telemetry-output artifacts/evaluation/generation_transformers_base_claim4_telemetry_v0_1.json

echo "=== LORA CLAIM-4 VALIDATION ==="
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_1.yaml \
  --provider-runtime-config configs/transformers_runtime_local_lora_reproduced_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_transformers_lora_claim4_v0_1.json \
  --telemetry-output artifacts/evaluation/generation_transformers_lora_claim4_telemetry_v0_1.json

PYTHONPATH=src "$python_bin" - <<'PY'
import hashlib
import json
from pathlib import Path


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


training = json.loads(
    Path("artifacts/evaluation/aeroragx_lora_training_reproduced_mps_v0_1.json").read_text()
)
summary = {
    "version": "0.1",
    "status": "completed",
    "base_model_sha256": sha256("work/models/Qwen3-0.6B/model.safetensors"),
    "adapter_path": "artifacts/training/adapters/aeroragx_lora_v0_1_reproduced_mps",
    "adapter_sha256": sha256(
        "artifacts/training/adapters/aeroragx_lora_v0_1_reproduced_mps/adapter_model.safetensors"
    ),
    "chunks_path": "data/processed/ntrs/v0_1/chunks.jsonl",
    "chunks_sha256": sha256("data/processed/ntrs/v0_1/chunks.jsonl"),
    "embeddings_sha256": sha256("artifacts/embeddings/ntrs_v0_1.npy"),
    "embedding_metadata_sha256": sha256(
        "artifacts/embeddings/ntrs_v0_1_metadata.jsonl"
    ),
    "embedding_manifest_sha256": sha256(
        "artifacts/embeddings/ntrs_v0_1_manifest.json"
    ),
    "best_epoch": training["best_epoch"],
    "best_dev_token_loss": training["best_dev_token_loss"],
    "base_report": "artifacts/evaluation/generation_transformers_base_claim4_v0_1.json",
    "lora_report": "artifacts/evaluation/generation_transformers_lora_claim4_v0_1.json",
}
Path("artifacts/evaluation/generation_claim4_actual_checkpoint_manifest_v0_1.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY
