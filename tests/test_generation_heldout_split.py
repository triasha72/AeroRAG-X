"""Tests for the development and held-out generation-evaluation split."""

from __future__ import annotations

from pathlib import Path

from aeroragx.generation.evaluation import load_generation_evaluation_queries

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_PATH = PROJECT_ROOT / "data/evaluation/generation_queries_v0_3.jsonl"
HELDOUT_PATH = PROJECT_ROOT / "data/evaluation/generation_queries_v0_4_heldout.jsonl"


def _normalize_query(value: str) -> str:
    """Normalize text before comparing queries across evaluation splits."""

    return " ".join(value.casefold().split())


def test_heldout_generation_queries_are_disjoint_from_development_queries() -> None:
    development_queries = load_generation_evaluation_queries(DEVELOPMENT_PATH)
    heldout_queries = load_generation_evaluation_queries(HELDOUT_PATH)

    development_ids = {query.query_id for query in development_queries}
    heldout_ids = {query.query_id for query in heldout_queries}

    development_text = {_normalize_query(query.query) for query in development_queries}
    heldout_text = {_normalize_query(query.query) for query in heldout_queries}

    assert len(heldout_queries) == 12
    assert sum(query.expected_answerable for query in heldout_queries) == 6
    assert development_ids.isdisjoint(heldout_ids)
    assert development_text.isdisjoint(heldout_text)
