"""Tests for the Phase 25 frozen baseline manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "artifacts/evaluation/phase25_baseline_manifest_v0_1.json"


def test_phase25_manifest_preserves_every_frozen_baseline_checksum() -> None:
    manifest = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8",
        )
    )

    assert manifest["phase"] == 25
    assert manifest["protected_held_out_contract"]["status"] == "frozen"

    for item in manifest["frozen_inputs"]:
        path = PROJECT_ROOT / item["path"]
        actual_checksum = hashlib.sha256(path.read_bytes()).hexdigest()

        assert actual_checksum == item["sha256"], path
