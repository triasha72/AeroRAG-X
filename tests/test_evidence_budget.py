"""Tests for deterministic pre-generation evidence budgeting."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from aeroragx.generation.evidence_budget import (
    AdaptiveEvidenceBudgetIndex,
    EvidenceBudgetConfig,
)
from aeroragx.generation.sufficiency import EvidenceSufficiencyAssessor, SufficiencyConfig


@dataclass(frozen=True)
class Chunk:
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk


class Index:
    def __init__(self, texts: list[str]) -> None:
        self.hits = [Hit(Chunk(text)) for text in texts]
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, top_k: int = 10):
        self.calls.append((query, top_k))
        return self.hits[:top_k]


def selector(texts: list[str]) -> tuple[AdaptiveEvidenceBudgetIndex, Index]:
    index = Index(texts)
    assessor = EvidenceSufficiencyAssessor(
        SufficiencyConfig(
            minimum_supported_terms=2,
            minimum_query_term_coverage=0.6,
            minimum_single_evidence_coverage=0.35,
        )
    )
    return AdaptiveEvidenceBudgetIndex(index, assessor, EvidenceBudgetConfig()), index  # type: ignore[arg-type]


def test_supported_top_three_does_not_expand() -> None:
    adaptive, index = selector(
        [
            "Aircraft battery thermal cooling manages heat.",
            "Additional unrelated evidence.",
            "More unrelated evidence.",
            "Fourth passage.",
            "Fifth passage.",
        ]
    )
    result = adaptive.search("How is aircraft battery heat managed?", top_k=5)
    assert len(result) == 3
    assert index.calls == [("How is aircraft battery heat managed?", 5)]
    assert adaptive.decisions[0].expanded is False
    assert adaptive.decisions[0].expansion_reason == "initial_evidence_sufficient"


def test_recoverable_coverage_gap_expands_once_to_five() -> None:
    adaptive, _ = selector(
        ["unrelated text", "another passage", "more text", "battery thermal", "aircraft heat"]
    )
    result = adaptive.search("How is aircraft battery heat managed?", top_k=5)
    assert len(result) == 5
    assert adaptive.decisions[0].expanded is True
    assert adaptive.decisions[0].maximum_sufficient is True
    assert adaptive.decisions[0].expansion_reason == "recoverable_coverage_gap"


def test_missing_numeric_support_blocks_expansion() -> None:
    adaptive, _ = selector(
        [
            "NASA aircraft battery research discusses future systems.",
            "Aircraft battery evidence.",
            "NASA research evidence.",
            "Fourth passage.",
            "Fifth passage.",
        ]
    )
    result = adaptive.search("What battery did NASA approve in 2040?", top_k=5)
    assert len(result) == 3
    assert adaptive.decisions[0].expanded is False
    assert "missing_numeric_support" in adaptive.decisions[0].initial_reasons


def test_does_not_expand_when_five_passages_remain_insufficient() -> None:
    adaptive, _ = selector(
        ["unrelated text", "another passage", "more text", "fourth text", "fifth text"]
    )
    result = adaptive.search("How is aircraft battery heat managed?", top_k=5)
    assert len(result) == 3
    assert adaptive.decisions[0].expanded is False
    assert adaptive.decisions[0].maximum_sufficient is False
    assert adaptive.decisions[0].expansion_reason == "maximum_evidence_still_insufficient"


def test_missing_universal_scope_support_blocks_expansion() -> None:
    adaptive, _ = selector(
        [
            "Electric aircraft can be affected by wind.",
            "Aircraft operating limitations vary.",
            "Wind affects aviation.",
            "Fourth passage.",
            "Fifth passage.",
        ]
    )
    result = adaptive.search("Which wind speed grounds every electric aircraft worldwide?", top_k=5)
    assert len(result) == 3
    assert adaptive.decisions[0].expansion_reason == "blocked_by_unsupported_signal"
    assert "missing_scope_qualifier_support" in adaptive.decisions[0].initial_reasons


def test_policy_refuses_unbounded_or_mismatched_request() -> None:
    adaptive, _ = selector(["evidence"] * 5)
    with pytest.raises(ValueError, match="requested top_k"):
        adaptive.search("question", top_k=4)


def test_decision_property_is_defensive() -> None:
    adaptive, _ = selector(["aircraft battery heat"] * 5)
    adaptive.search("aircraft battery heat", top_k=5)
    copy = adaptive.decisions
    copy[0].initial_reasons.append("changed")
    assert "changed" not in adaptive.decisions[0].initial_reasons
