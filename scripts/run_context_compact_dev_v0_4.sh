#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

python_bin="work/train-venv/bin/python"
queries="data/evaluation/generation_queries_compact_dev_v0_1.jsonl"
control_report="artifacts/evaluation/generation_lora_original_dev_v0_3_1_control.json"
control_telemetry="artifacts/evaluation/generation_lora_original_dev_v0_3_1_control_telemetry.json"

require_sha() {
  path=$1
  expected=$2
  actual=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$actual" = "$expected" ] || {
    echo "Frozen control checksum mismatch: $path" >&2
    exit 1
  }
}

require_sha "$control_report" "a63c594d2d97278cbcb64b6e1cf1e52b3d224de8265fb6fe30cb4214b3d01e39"
require_sha "$control_telemetry" "39bbd9f06ed87881405ab40d0e6225822735f15e015c421468b8b038c1b2298b"

PYTHONPATH=src "$python_bin" -c '
import torch
if not torch.backends.mps.is_available():
    raise SystemExit("Apple MPS is unavailable; CPU substitution is disabled.")
'
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Keep the reliable v0.3.1 prompt and checkpoint. Change only the evidence
# budget from five passages to three so this isolates context compression.
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --queries-input "$queries" \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_3_1_compact_dev.yaml \
  --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 3 \
  --report-output artifacts/evaluation/generation_lora_context3_dev_v0_4.json \
  --telemetry-output artifacts/evaluation/generation_lora_context3_dev_v0_4_telemetry.json

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report "$control_report" \
  --base-telemetry "$control_telemetry" \
  --treatment-report artifacts/evaluation/generation_lora_context3_dev_v0_4.json \
  --treatment-telemetry artifacts/evaluation/generation_lora_context3_dev_v0_4_telemetry.json \
  --json-output artifacts/evaluation/generation_lora_context3_dev_v0_4_paired.json \
  --markdown-output reports/generation_lora_context3_dev_v0_4_paired.md

if PYTHONPATH=src "$python_bin" scripts/check_compact_generation_promotion.py \
  --baseline-report "$control_report" \
  --candidate-report artifacts/evaluation/generation_lora_context3_dev_v0_4.json \
  --paired-efficiency artifacts/evaluation/generation_lora_context3_dev_v0_4_paired.json \
  --expected-query-count 8 \
  --minimum-paired-calls 7 \
  --maximum-rate-regression 0 \
  --token-metric total \
  --output artifacts/evaluation/generation_lora_context3_dev_v0_4_decision.json; then
  echo "v0.4 context candidate passed development gates."
else
  echo "v0.4 context candidate failed; do not use the protected set."
fi

echo "v0.4 development run complete. No protected-set claim was made."
