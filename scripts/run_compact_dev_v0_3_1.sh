#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

python_bin="work/train-venv/bin/python"
queries="data/evaluation/generation_queries_compact_dev_v0_1.jsonl"
protected="data/evaluation/generation_queries_v0_3.jsonl"

[ "$queries" != "$protected" ] || {
  echo "Development runner refuses the protected query set." >&2
  exit 1
}

for condition in base lora; do
  runtime="configs/transformers_runtime_local_${condition}_compact_v0_1.yaml"
  PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py \
    --queries-input "$queries" \
    --memory-bounded \
    --generation-config configs/generation_transformers_local_claim4_v0_1.yaml \
    --sufficiency-config configs/sufficiency_v0_1.yaml \
    --provider-config configs/provider_v0_3_1_compact_dev.yaml \
    --provider-runtime-config "$runtime" \
    --candidate-top-k 20 \
    --evidence-top-k 5 \
    --report-output "artifacts/evaluation/generation_${condition}_compact_dev_v0_3_1.json" \
    --telemetry-output \
      "artifacts/evaluation/generation_${condition}_compact_dev_v0_3_1_telemetry.json"
done

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_base_compact_dev_v0_3_1.json \
  --base-telemetry artifacts/evaluation/generation_base_compact_dev_v0_3_1_telemetry.json \
  --treatment-report artifacts/evaluation/generation_lora_compact_dev_v0_3_1.json \
  --treatment-telemetry \
    artifacts/evaluation/generation_lora_compact_dev_v0_3_1_telemetry.json \
  --json-output artifacts/evaluation/generation_compact_dev_v0_3_1_paired.json \
  --markdown-output reports/generation_compact_dev_v0_3_1_paired.md

echo "Development run complete. This is not protected-set promotion evidence."
