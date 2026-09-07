#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
python_bin="work/train-venv/bin/python"
queries="data/evaluation/generation_queries_context_dev_v0_2.jsonl"

PYTHONPATH=src "$python_bin" scripts/build_context_compaction_dev_v0_2.py --check
PYTHONPATH=src "$python_bin" -c '
import torch
if not torch.backends.mps.is_available():
    raise SystemExit("Apple MPS unavailable; CPU substitution is disabled.")
'
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

common_args="--queries-input $queries --memory-bounded --generation-config configs/generation_transformers_local_claim4_v0_1.yaml --sufficiency-config configs/sufficiency_v0_1.yaml --provider-config configs/provider_v0_3_1_compact_dev.yaml --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml --candidate-top-k 20 --evidence-top-k 5"

echo "=== UNCOMPRESSED TOP-5 CONTROL ==="
# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --report-output artifacts/evaluation/generation_lora_uncompressed5_dev_v0_6_control.json \
  --telemetry-output artifacts/evaluation/generation_lora_uncompressed5_dev_v0_6_control_telemetry.json

echo "=== EXTRACTIVELY COMPRESSED TOP-5 TREATMENT ==="
# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --evidence-compression-config configs/evidence_compression_top5_v0_1.yaml \
  --evidence-compression-output artifacts/evaluation/generation_lora_compressed5_dev_v0_6_compression.json \
  --report-output artifacts/evaluation/generation_lora_compressed5_dev_v0_6.json \
  --telemetry-output artifacts/evaluation/generation_lora_compressed5_dev_v0_6_telemetry.json

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_lora_uncompressed5_dev_v0_6_control.json \
  --base-telemetry artifacts/evaluation/generation_lora_uncompressed5_dev_v0_6_control_telemetry.json \
  --treatment-report artifacts/evaluation/generation_lora_compressed5_dev_v0_6.json \
  --treatment-telemetry artifacts/evaluation/generation_lora_compressed5_dev_v0_6_telemetry.json \
  --json-output artifacts/evaluation/generation_lora_compressed5_dev_v0_6_paired.json \
  --markdown-output reports/generation_lora_compressed5_dev_v0_6_paired.md

if PYTHONPATH=src "$python_bin" scripts/check_compact_generation_promotion.py \
  --baseline-report artifacts/evaluation/generation_lora_uncompressed5_dev_v0_6_control.json \
  --candidate-report artifacts/evaluation/generation_lora_compressed5_dev_v0_6.json \
  --paired-efficiency artifacts/evaluation/generation_lora_compressed5_dev_v0_6_paired.json \
  --expected-query-count 50 \
  --minimum-paired-calls 25 \
  --maximum-rate-regression 0.02 \
  --token-metric total \
  --output artifacts/evaluation/generation_lora_compressed5_dev_v0_6_decision.json; then
  echo "v0.6 source-preserving evidence compression passed development gates."
else
  echo "v0.6 evidence compression failed; uncompressed top-5 remains the default."
fi

echo "Development run complete. No protected-set claim was made."
