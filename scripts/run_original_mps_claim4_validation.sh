#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

python_bin="work/train-venv/bin/python"
model_dir="work/models/Qwen3-0.6B"
adapter_dir="artifacts/training/adapters/aeroragx_lora_v0_1_reproduced_mps"

expected_model_sha="f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"
expected_train_sha="0210ada9daef286ca0adba8a41b2f58a1638de14d39ca88db06ad17e53c31617"
expected_dev_sha="9f20bce48b8b34df1956098f70b618fbd7fe0feb2dac048eb7a96fca31fbf2d3"

actual_model_sha=$(shasum -a 256 "$model_dir/model.safetensors" | awk '{print $1}')
actual_train_sha=$(shasum -a 256 data/training/splits/aeroragx_lora_v0_1_train_eligible.jsonl | awk '{print $1}')
actual_dev_sha=$(shasum -a 256 data/training/splits/aeroragx_lora_v0_1_dev.jsonl | awk '{print $1}')

[ "$actual_model_sha" = "$expected_model_sha" ] || { echo "Base-model checksum mismatch" >&2; exit 1; }
[ "$actual_train_sha" = "$expected_train_sha" ] || { echo "Training checksum mismatch" >&2; exit 1; }
[ "$actual_dev_sha" = "$expected_dev_sha" ] || { echo "Development checksum mismatch" >&2; exit 1; }

PYTHONPATH=src "$python_bin" -c 'import torch; assert torch.backends.mps.is_available(), "Apple MPS is unavailable"'

PYTHONPATH=src "$python_bin" scripts/train_lora_v01.py \
  --base-model "$model_dir" \
  --adapter-output "$adapter_dir" \
  --report-output artifacts/evaluation/aeroragx_lora_training_reproduced_mps_v0_1.json

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
import json
from pathlib import Path

training = json.loads(Path("artifacts/evaluation/aeroragx_lora_training_reproduced_mps_v0_1.json").read_text())
if training.get("best_epoch") != 2:
    raise SystemExit(f"Reproduced adapter selected epoch {training.get('best_epoch')}, expected epoch 2")

summary = {
    "version": "0.1",
    "base_model_sha256": "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b",
    "adapter_path": "artifacts/training/adapters/aeroragx_lora_v0_1_reproduced_mps",
    "best_epoch": training["best_epoch"],
    "best_dev_token_loss": training["best_dev_token_loss"],
    "base_report": "artifacts/evaluation/generation_transformers_base_claim4_v0_1.json",
    "lora_report": "artifacts/evaluation/generation_transformers_lora_claim4_v0_1.json",
    "status": "completed",
}
Path("artifacts/evaluation/generation_claim4_actual_checkpoint_manifest_v0_1.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY
