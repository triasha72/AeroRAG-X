#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
python_bin="work/train-venv/bin/python"
protocol="configs/context_compaction_protected_protocol_v0_1.json"

PYTHONPATH=src "$python_bin" - "$protocol" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

protocol_path = Path(sys.argv[1])
protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
if protocol.get("status") != "frozen_before_execution":
    raise SystemExit("Protocol is not frozen for execution.")
for name, expected in protocol["inputs"].items():
    path = Path(name)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Checksum mismatch: {path}\nexpected={expected}\nactual={actual}")
for path in protocol["outputs"].values():
    if Path(path).exists():
        raise SystemExit(f"One-shot output already exists; refusing overwrite: {path}")
print("FROZEN PROTOCOL PREFLIGHT: PASS")
PY

PYTHONPATH=src "$python_bin" -c '
import torch
if not torch.backends.mps.is_available():
    raise SystemExit("Apple MPS unavailable; CPU substitution is disabled.")
'
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

common_args="--queries-input data/evaluation/generation_queries_v0_3.jsonl --memory-bounded --generation-config configs/generation_transformers_local_claim4_v0_1.yaml --sufficiency-config configs/sufficiency_v0_1.yaml --provider-config configs/provider_v0_3_1_compact_dev.yaml --provider-runtime-config configs/transformers_runtime_local_lora_compact_v0_1.yaml --candidate-top-k 20"

# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --evidence-top-k 5 \
  --report-output artifacts/evaluation/generation_lora_context5_protected_v0_4_2_control.json \
  --telemetry-output artifacts/evaluation/generation_lora_context5_protected_v0_4_2_control_telemetry.json

# shellcheck disable=SC2086
PYTHONPATH=src "$python_bin" scripts/run_generation_v03.py $common_args \
  --evidence-top-k 3 \
  --report-output artifacts/evaluation/generation_lora_context3_protected_v0_4_2.json \
  --telemetry-output artifacts/evaluation/generation_lora_context3_protected_v0_4_2_telemetry.json

PYTHONPATH=src "$python_bin" scripts/analyze_paired_generation_efficiency.py \
  --base-report artifacts/evaluation/generation_lora_context5_protected_v0_4_2_control.json \
  --base-telemetry artifacts/evaluation/generation_lora_context5_protected_v0_4_2_control_telemetry.json \
  --treatment-report artifacts/evaluation/generation_lora_context3_protected_v0_4_2.json \
  --treatment-telemetry artifacts/evaluation/generation_lora_context3_protected_v0_4_2_telemetry.json \
  --json-output artifacts/evaluation/generation_lora_context3_protected_v0_4_2_paired.json \
  --markdown-output reports/generation_lora_context3_protected_v0_4_2_paired.md

set +e
PYTHONPATH=src "$python_bin" scripts/check_compact_generation_promotion.py \
  --baseline-report artifacts/evaluation/generation_lora_context5_protected_v0_4_2_control.json \
  --candidate-report artifacts/evaluation/generation_lora_context3_protected_v0_4_2.json \
  --paired-efficiency artifacts/evaluation/generation_lora_context3_protected_v0_4_2_paired.json \
  --expected-query-count 32 \
  --minimum-paired-calls 15 \
  --maximum-rate-regression 0.03125 \
  --token-metric total \
  --output artifacts/evaluation/generation_lora_context3_protected_v0_4_2_decision.json
gate_status=$?
set -e

PYTHONPATH=src "$python_bin" - "$protocol" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

protocol_path = Path(sys.argv[1])
protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
artifacts = {}
for name, path_text in protocol["outputs"].items():
    if name == "manifest":
        continue
    path = Path(path_text)
    if not path.is_file():
        raise SystemExit(f"Missing final artifact: {path}")
    artifacts[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
decision = json.loads(Path(protocol["outputs"]["decision"]).read_text(encoding="utf-8"))
manifest = {
    "version": "0.1",
    "status": f"completed_{decision['status']}",
    "protocol": str(protocol_path),
    "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
    "evidence_boundary": protocol["evidence_boundary"],
    "artifacts": artifacts,
}
output = Path(protocol["outputs"]["manifest"])
output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2, sort_keys=True))
PY

if [ "$gate_status" -eq 0 ]; then
  echo "v0.4.2 passed the frozen final-validation gate."
else
  echo "v0.4.2 failed the frozen final-validation gate; the result is preserved."
fi
exit "$gate_status"
