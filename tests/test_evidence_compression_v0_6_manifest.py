import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_v0_6_manifest_is_development_only_and_integrity_checked() -> None:
    manifest = json.loads(
        (
            REPO_ROOT / "artifacts/evaluation/generation_lora_compressed5_dev_v0_6_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["status"] == "development_promoted_protected_evaluation_pending"
    assert manifest["metrics"]["paired_completed_query_count"] == 47
    assert manifest["metrics"]["relative_total_token_change"] < -0.15
    for artifact in manifest["artifacts"]:
        path = REPO_ROOT / artifact["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
