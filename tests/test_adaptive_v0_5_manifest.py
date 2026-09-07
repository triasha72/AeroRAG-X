import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    REPO_ROOT / "artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_manifest.json"
)


def test_adaptive_v0_5_manifest_preserves_rejected_real_evidence() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["status"] == "completed_rejected_noop"
    assert payload["observations"]["query_count"] == 50
    assert payload["observations"]["expanded_count"] == 1
    assert payload["observations"]["effective_higher_input_query_count"] == 0
    assert payload["observations"]["recoverable_top3_to_top5_cases_found"] == 1

    for artifact in payload["artifacts"]:
        path = REPO_ROOT / artifact["path"]
        assert path.is_file(), artifact["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
