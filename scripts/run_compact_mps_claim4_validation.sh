#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

python_bin="work/train-venv/bin/python"
base_report="artifacts/evaluation/generation_transformers_base_claim4_compact_v0_1.json"
lora_report="artifacts/evaluation/generation_transformers_lora_claim4_compact_v0_1.json"
base_telemetry="artifacts/evaluation/generation_transformers_base_claim4_compact_telemetry_v0_1.json"
lora_telemetry="artifacts/evaluation/generation_transformers_lora_claim4_compact_telemetry_v0_1.json"

require_sha() {
  path=$1
  expected=$2
  actual=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$actual" = "$expected" ] || {
    echo "Checksum mismatch: $path" >&2
    exit 1
  }
}

require_sha work/models/Qwen3-0.6B/model.safetensors f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b
require_sha artifacts/training/adapters/aeroragx_lora_v0_1_reproduced_mps/adapter_model.safetensors 13df5eb8449d5b204c2d740b0c194b7712969f15258c42b26a336febeb27c717
require_sha data/processed/ntrs/v0_1/chunks.jsonl 67ce4f814db096a0d49117fde9c924c7ae8825ea3c631463255e4fde0e3706c2

PYTHONPATH=src "$python_bin" -c 'import torch; assert torch.backends.mps.is_available(), "Apple MPS is unavailable"'

echo "=== BASE COMPACT CLAIM-4 VALIDATION ==="
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_3_compact.yaml \
  --provider-runtime-config configs/transformers_runtime_local_base_compact_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output "$base_report" \
  --telemetry-output "$base_telemetry"

echo "=== LORA COMPACT CLAIM-4 VALIDATION ==="
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_3_compact.yaml \
  --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output "$lora_report" \
  --telemetry-output "$lora_telemetry"

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report "$base_report" \
  --base-telemetry "$base_telemetry" \
  --treatment-report "$lora_report" \
  --treatment-telemetry "$lora_telemetry" \
  --json-output artifacts/evaluation/generation_claim4_compact_paired_efficiency_v0_1.json \
  --markdown-output reports/generation_claim4_compact_paired_efficiency_v0_1.md

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_transformers_lora_claim4_v0_1.json \
  --base-telemetry artifacts/evaluation/generation_transformers_lora_claim4_telemetry_v0_1.json \
  --treatment-report "$lora_report" \
  --treatment-telemetry "$lora_telemetry" \
  --json-output artifacts/evaluation/generation_lora_compact_vs_v01_paired_v0_1.json \
  --markdown-output reports/generation_lora_compact_vs_v01_paired_v0_1.md

if PYTHONPATH=src "$python_bin" scripts/check_compact_generation_promotion.py \
  --baseline-report artifacts/evaluation/generation_transformers_lora_claim4_v0_1.json \
  --candidate-report "$lora_report" \
  --paired-efficiency artifacts/evaluation/generation_lora_compact_vs_v01_paired_v0_1.json \
  --output artifacts/evaluation/generation_lora_compact_promotion_v0_1.json; then
  echo "Compact candidate passed every promotion gate."
else
  echo "Compact candidate was rejected; preserving the completed experiment."
fi

PYTHONPATH=src "$python_bin" - <<'PY'
import hashlib
import json
from pathlib import Path

paths = {
    "base_report": Path("artifacts/evaluation/generation_transformers_base_claim4_compact_v0_1.json"),
    "lora_report": Path("artifacts/evaluation/generation_transformers_lora_claim4_compact_v0_1.json"),
    "paired_report": Path("artifacts/evaluation/generation_claim4_compact_paired_efficiency_v0_1.json"),
    "lora_vs_original": Path("artifacts/evaluation/generation_lora_compact_vs_v01_paired_v0_1.json"),
    "promotion": Path("artifacts/evaluation/generation_lora_compact_promotion_v0_1.json"),
}
for path in paths.values():
    if not path.is_file():
        raise SystemExit(f"Missing completed compact-validation artifact: {path}")
promotion = json.loads(paths["promotion"].read_text(encoding="utf-8"))
summary = {
    "version": "0.1",
    "status": f"completed_{promotion['status']}",
    "prompt_version": "grounded-json-v0.3-compact",
    "max_new_tokens": 384,
    "query_count": 32,
    "artifacts": {
        name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in paths.items()
    },
}
Path("artifacts/evaluation/generation_claim4_compact_manifest_v0_1.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY
