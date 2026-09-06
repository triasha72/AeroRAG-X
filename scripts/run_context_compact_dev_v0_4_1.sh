#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

python_bin="work/train-venv/bin/python"
queries="data/evaluation/generation_queries_context_dev_v0_2.jsonl"

PYTHONPATH=src "$python_bin" scripts/build_context_compaction_dev_v0_2.py --check
PYTHONPATH=src "$python_bin" -c '
import torch
if not torch.backends.mps.is_built():
    raise SystemExit("PyTorch was not built with Apple MPS support.")
if not torch.backends.mps.is_available():
    raise SystemExit(
        "Apple MPS is unavailable in this process. Run from normal macOS Terminal; "
        "CPU substitution is intentionally disabled."
    )
'

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# The checkpoint, prompt, provider settings, candidate pool, and 50 queries are
# identical. Only the final evidence budget changes: top five versus top three.
for protected in \
  data/evaluation/generation_queries_v0_3.jsonl \
  data/evaluation/generation_queries_v0_4_heldout.jsonl \
  data/evaluation/scope_qualifier_heldout_v0_1.jsonl; do
  [ "$queries" != "$protected" ] || {
    echo "Development runner refuses a protected query set." >&2
    exit 1
  }
done

PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --queries-input "$queries" \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_3_1_compact_dev.yaml \
  --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_lora_context5_dev_v0_4_1_control.json \
  --telemetry-output artifacts/evaluation/generation_lora_context5_dev_v0_4_1_control_telemetry.json

PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
  --queries-input "$queries" \
  --memory-bounded \
  --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
  --sufficiency-config configs/sufficiency_v0_1.yaml \
  --provider-config configs/provider_v0_3_1_compact_dev.yaml \
  --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml \
  --candidate-top-k 20 \
  --evidence-top-k 3 \
  --report-output artifacts/evaluation/generation_lora_context3_dev_v0_4_1.json \
  --telemetry-output artifacts/evaluation/generation_lora_context3_dev_v0_4_1_telemetry.json

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_lora_context5_dev_v0_4_1_control.json \
  --base-telemetry artifacts/evaluation/generation_lora_context5_dev_v0_4_1_control_telemetry.json \
  --treatment-report artifacts/evaluation/generation_lora_context3_dev_v0_4_1.json \
  --treatment-telemetry artifacts/evaluation/generation_lora_context3_dev_v0_4_1_telemetry.json \
  --json-output artifacts/evaluation/generation_lora_context3_dev_v0_4_1_paired.json \
  --markdown-output reports/generation_lora_context3_dev_v0_4_1_paired.md

if PYTHONPATH=src "$python_bin" scripts/check_compact_generation_promotion.py \
  --baseline-report artifacts/evaluation/generation_lora_context5_dev_v0_4_1_control.json \
  --candidate-report artifacts/evaluation/generation_lora_context3_dev_v0_4_1.json \
  --paired-efficiency artifacts/evaluation/generation_lora_context3_dev_v0_4_1_paired.json \
  --expected-query-count 50 \
  --minimum-paired-calls 25 \
  --maximum-rate-regression 0.02 \
  --token-metric total \
  --output artifacts/evaluation/generation_lora_context3_dev_v0_4_1_decision.json; then
  echo "v0.4.1 passed the 50-case development gate."
else
  echo "v0.4.1 failed the larger development gate; do not use the protected set."
fi

echo "Development run complete. No protected-set or human-review claim was made."
