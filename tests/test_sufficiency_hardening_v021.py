"""Regression tests for evidence-sufficiency hardening v0.2.1."""

from __future__ import annotations

from dataclasses import dataclass

from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    SufficiencyConfig,
)


@dataclass(frozen=True)
class Evidence:
    text: str


def _assessor() -> EvidenceSufficiencyAssessor:
    return EvidenceSufficiencyAssessor(
        SufficiencyConfig(
            version="0.2.1",
            require_claim_qualifiers=True,
        )
    )


def test_lowercase_technical_compound_is_not_named_anchor() -> None:
    result = _assessor().assess(
        query=(
            "Why do power-electronics components require "
            "thermal management in electrified aircraft?"
        ),
        evidence=[
            Evidence(
                "Power electronics components require "
                "thermal management in electrified aircraft "
                "because electrical components create heat."
            )
        ],
    )

    assert result.sufficient is True

    assert "power" not in result.required_named_anchors
    assert "electronic" not in result.required_named_anchors


def test_issues_is_not_a_claim_qualifier() -> None:
    result = _assessor().assess(
        query=(
            "What safety and thermal-management issues "
            "should designers consider across electrified "
            "aircraft propulsion systems?"
        ),
        evidence=[
            Evidence(
                "Designers should consider safety and "
                "thermal management issues across "
                "electrified aircraft propulsion systems."
            )
        ],
    )

    assert result.sufficient is True
    assert result.required_claim_qualifiers == []


def test_issued_remains_a_claim_qualifier() -> None:
    result = _assessor().assess(
        query=(
            "Which FAA certificate was issued to the "
            "fictional Project AetherWing superconducting "
            "aircraft motor?"
        ),
        evidence=[
            Evidence(
                "The FAA discusses certification of "
                "advanced aircraft and superconducting "
                "aircraft motors."
            )
        ],
    )

    assert result.sufficient is False
    assert "issue" in result.required_claim_qualifiers
    assert "missing_claim_qualifier_support" in result.reasons


def test_camelcase_anchor_remains_required() -> None:
    result = _assessor().assess(
        query=("Which FAA certificate was issued to AetherWing?"),
        evidence=[Evidence("The FAA issues certificates for aircraft projects.")],
    )

    assert result.sufficient is False
    assert "aetherw" in result.required_named_anchors
    assert "missing_named_anchor_support" in result.reasons
