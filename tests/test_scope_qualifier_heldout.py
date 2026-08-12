"""Tests for the Phase 28 scope-qualifier held-out benchmark."""

from __future__ import annotations

from pathlib import Path

from aeroragx.generation.evaluation import load_generation_evaluation_queries

ROOT = Path(__file__).resolve().parents[1]
HELDOUT_PATH = ROOT / "data/evaluation/scope_qualifier_heldout_v0_1.jsonl"
DEVELOPMENT_PATH = ROOT / "data/evaluation/adaptive_scope_challenge_v0_1.jsonl"
PHASE26_PATH = ROOT / "data/evaluation/generation_queries_v0_4_heldout.jsonl"


def test_scope_heldout_has_expected_class_balance() -> None:
    """Keep the separately authored benchmark class balance stable."""

    queries = load_generation_evaluation_queries(HELDOUT_PATH)

    assert len(queries) == 14
    assert sum(query.expected_answerable for query in queries) == 4
    assert sum(not query.expected_answerable for query in queries) == 10


def test_scope_heldout_is_separate_from_development_and_phase26() -> None:
    """Prevent reuse of Phase 27 development or protected Phase 26 questions."""

    heldout_queries = load_generation_evaluation_queries(HELDOUT_PATH)
    development_queries = load_generation_evaluation_queries(DEVELOPMENT_PATH)
    phase26_queries = load_generation_evaluation_queries(PHASE26_PATH)

    heldout_ids = {query.query_id for query in heldout_queries}
    heldout_text = {query.query.casefold() for query in heldout_queries}

    development_ids = {query.query_id for query in development_queries}
    development_text = {query.query.casefold() for query in development_queries}

    phase26_ids = {query.query_id for query in phase26_queries}
    phase26_text = {query.query.casefold() for query in phase26_queries}

    assert heldout_ids.isdisjoint(development_ids)
    assert heldout_ids.isdisjoint(phase26_ids)
    assert heldout_text.isdisjoint(development_text)
    assert heldout_text.isdisjoint(phase26_text)


def test_unanswerable_scope_heldout_queries_have_no_expected_terms() -> None:
    """Keep refusal cases independent of answer-term scoring."""

    queries = load_generation_evaluation_queries(HELDOUT_PATH)

    for query in queries:
        if not query.expected_answerable:
            assert query.expected_terms == []


def test_answerable_scope_heldout_queries_require_expected_terms() -> None:
    """Ensure answerable controls remain meaningful for accuracy scoring."""

    queries = load_generation_evaluation_queries(HELDOUT_PATH)

    for query in queries:
        if query.expected_answerable:
            assert query.expected_terms
