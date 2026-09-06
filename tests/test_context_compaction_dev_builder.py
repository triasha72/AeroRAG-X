"""Regression tests for the context-compaction development dataset."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_context_compaction_dev_v0_2.py"


def _module():
    spec = importlib.util.spec_from_file_location("context_dev_builder", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_is_deterministic_and_has_frozen_composition() -> None:
    module = _module()
    first = module.build()
    second = module.build()
    assert first == second
    rows = [json.loads(line) for line in first[0].splitlines()]
    manifest = json.loads(first[1])
    assert len(rows) == 50
    assert manifest["answerable_count"] == 38
    assert manifest["unsupported_count"] == 12
    assert manifest["source_counts"] == {
        "automatic_source_stress": 32,
        "curated_compact": 8,
        "scope_challenge": 10,
    }


def test_build_has_no_normalized_protected_overlap() -> None:
    module = _module()
    output, _ = module.build()
    rows = [json.loads(line) for line in output.splitlines()]
    protected = [row for path in module.PROTECTED for row in module._rows(path)]
    assert {row["query_id"] for row in rows}.isdisjoint({row["query_id"] for row in protected})
    assert {module._normalized(row["query"]) for row in rows}.isdisjoint(
        {module._normalized(row["query"]) for row in protected}
    )


def test_checked_in_files_match_deterministic_build() -> None:
    module = _module()
    output, manifest = module.build()
    assert module.DEFAULT_OUTPUT.read_bytes() == output
    assert module.DEFAULT_MANIFEST.read_bytes() == manifest
