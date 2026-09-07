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

common_args="--queries-input $queries --memory-bounded --generation-config configs/generation_transformers_local_claim4_v0_1.yaml --sufficiency-config configs/sufficiency_v0_1.yaml --provider-config configs/provider_v0_3_1_compact_dev.yaml --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml --candidate-top-k 20"

echo "=== FIXED TOP-5 CONTROL ==="
# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_lora_context5_dev_v0_5_control.json \
  --telemetry-output artifacts/evaluation/generation_lora_context5_dev_v0_5_control_telemetry.json

echo "=== FIXED TOP-3 REFERENCE ==="
# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --evidence-top-k 3 \
  --report-output artifacts/evaluation/generation_lora_context3_dev_v0_5_reference.json \
  --telemetry-output artifacts/evaluation/generation_lora_context3_dev_v0_5_reference_telemetry.json

echo "=== ADAPTIVE TOP-3 TO TOP-5 CANDIDATE ==="
# The generator requests the hard maximum of five. The deterministic wrapper
# returns the first three unless its pre-generation sufficiency decision finds
# a recoverable coverage gap and no unsupported-scope blocker.
# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --evidence-top-k 5 \
  --adaptive-evidence-budget-config configs/evidence_budget_adaptive_3_to_5_v0_1.yaml \
  --evidence-budget-decisions-output artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_budget.json \
  --report-output artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5.json \
  --telemetry-output artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_telemetry.json

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_lora_context5_dev_v0_5_control.json \
  --base-telemetry artifacts/evaluation/generation_lora_context5_dev_v0_5_control_telemetry.json \
  --treatment-report artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5.json \
  --treatment-telemetry artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_telemetry.json \
  --json-output artifacts/evaluation/generation_lora_adaptive_vs_context5_dev_v0_5_paired.json \
  --markdown-output reports/generation_lora_adaptive_vs_context5_dev_v0_5_paired.md

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_lora_context3_dev_v0_5_reference.json \
  --base-telemetry artifacts/evaluation/generation_lora_context3_dev_v0_5_reference_telemetry.json \
  --treatment-report artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5.json \
  --treatment-telemetry artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_telemetry.json \
  --json-output artifacts/evaluation/generation_lora_adaptive_vs_context3_dev_v0_5_paired.json \
  --markdown-output reports/generation_lora_adaptive_vs_context3_dev_v0_5_paired.md

if PYTHONPATH=src "$python_bin" scripts/check_compact_generation_promotion.py \
  --baseline-report artifacts/evaluation/generation_lora_context5_dev_v0_5_control.json \
  --candidate-report artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5.json \
  --paired-efficiency artifacts/evaluation/generation_lora_adaptive_vs_context5_dev_v0_5_paired.json \
  --expected-query-count 50 \
  --minimum-paired-calls 25 \
  --maximum-rate-regression 0.02 \
  --token-metric total \
  --output artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_decision.json; then
  echo "v0.5 adaptive evidence budget passed the 50-case development gate."
else
  echo "v0.5 adaptive evidence budget failed; fixed top-5 remains the default."
fi

echo "Development run complete. No protected-set claim was made."
