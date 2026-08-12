"""Tests for the Phase 27 development-only unsupported-scope challenge set."""

from __future__ import annotations

from pathlib import Path

from aeroragx.generation.evaluation import load_generation_evaluation_queries

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_PATH = ROOT / "data/evaluation/adaptive_scope_challenge_v0_1.jsonl"
HELDOUT_PATH = ROOT / "data/evaluation/generation_queries_v0_4_heldout.jsonl"


def test_scope_challenge_has_expected_class_balance() -> None:
    """Keep the development challenge's intended answerability balance stable."""

    queries = load_generation_evaluation_queries(CHALLENGE_PATH)

    assert len(queries) == 14
    assert sum(query.expected_answerable for query in queries) == 4
    assert sum(not query.expected_answerable for query in queries) == 10


def test_scope_challenge_is_separate_from_phase26_heldout_queries() -> None:
    """Prevent development questions from being copied into the protected benchmark."""

    development_queries = load_generation_evaluation_queries(CHALLENGE_PATH)
    heldout_queries = load_generation_evaluation_queries(HELDOUT_PATH)

    development_ids = {query.query_id for query in development_queries}
    heldout_ids = {query.query_id for query in heldout_queries}

    development_text = {query.query.casefold() for query in development_queries}
    heldout_text = {query.query.casefold() for query in heldout_queries}

    assert development_ids.isdisjoint(heldout_ids)
    assert development_text.isdisjoint(heldout_text)


def test_unanswerable_scope_challenges_have_no_expected_terms() -> None:
    """Keep refusal challenges independent of answer-term scoring."""

    queries = load_generation_evaluation_queries(CHALLENGE_PATH)

    for query in queries:
        if not query.expected_answerable:
            assert query.expected_terms == []
