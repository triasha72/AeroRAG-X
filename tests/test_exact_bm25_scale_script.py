"""Regression tests for the exact scale-benchmark script."""

from scripts.benchmark_exact_bm25_scale import resolve_parent_id


def test_null_parent_uses_root_chunk_id() -> None:
    assert resolve_parent_id({"parent_chunk_id": None}, "chunk-1") == "chunk-1"


def test_explicit_parent_is_preserved() -> None:
    assert resolve_parent_id({"parent_chunk_id": "parent-1"}, "chunk-1") == "parent-1"
