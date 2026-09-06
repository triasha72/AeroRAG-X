"""Integrity tests for the frozen context-compaction final protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/context_compaction_protected_protocol_v0_1.json"


def _load() -> dict[str, object]:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_every_frozen_input_matches_its_checksum() -> None:
    protocol = _load()
    inputs = protocol["inputs"]
    assert isinstance(inputs, dict)
    for relative, expected in inputs.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, relative


def test_protocol_freezes_single_variable_and_fail_closed_thresholds() -> None:
    protocol = _load()
    assert protocol["status"] == "frozen_before_execution"
    assert protocol["query_count"] == 32
    assert protocol["candidate_top_k"] == 20
    assert protocol["control_evidence_top_k"] == 5
    assert protocol["treatment_evidence_top_k"] == 3
    assert protocol["token_metric"] == "total"
    assert protocol["minimum_token_reduction"] == 0.15
    assert protocol["maximum_rate_regression"] == 0.03125
    assert protocol["minimum_paired_calls"] == 15


def test_all_one_shot_outputs_are_unique() -> None:
    outputs = _load()["outputs"]
    assert isinstance(outputs, dict)
    paths = list(outputs.values())
    assert len(paths) == len(set(paths))
