"""Targeted tests for evidence-sufficiency hardening v0.2."""

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
            version="0.2",
            require_claim_qualifiers=True,
        )
    )


def test_storage_paraphrase_is_supported() -> None:
    result = _assessor().assess(
        query=("Why is storing cryogenic hydrogen aboard aircraft technically challenging?"),
        evidence=[
            Evidence(
                "Cryogenic hydrogen storage in aircraft creates significant technical challenges."
            )
        ],
    )

    assert result.sufficient is True
    assert "storage" in result.query_terms
    assert "storage" in result.supported_terms


def test_universal_mandate_is_blocked() -> None:
    result = _assessor().assess(
        query=(
            "What universal maximum battery-cell "
            "temperature does NASA mandate for every "
            "electric aircraft?"
        ),
        evidence=[Evidence("NASA studies battery cell temperature limits for electric aircraft.")],
    )

    assert result.sufficient is False
    assert "missing_claim_qualifier_support" in result.reasons


def test_failure_probability_overclaim_is_blocked() -> None:
    result = _assessor().assess(
        query=(
            "What exact failure probability does NASA "
            "assign to every hybrid-electric aircraft "
            "propulsion system?"
        ),
        evidence=[
            Evidence(
                "NASA discusses failure probability "
                "analysis for hybrid-electric aircraft "
                "propulsion systems. The exact effects "
                "of a motor failure remain uncertain."
            )
        ],
    )

    assert result.sufficient is False
    assert "missing_claim_qualifier_support" in result.reasons


def test_camelcase_named_anchor_is_required() -> None:
    result = _assessor().assess(
        query=(
            "Which FAA certificate was issued to the "
            "fictional Project AetherWing superconducting "
            "aircraft motor?"
        ),
        evidence=[
            Evidence(
                "The FAA discusses certificate pathways "
                "and NASA has studied superconducting "
                "aircraft motors."
            )
        ],
    )

    assert result.sufficient is False
    assert "missing_named_anchor_support" in result.reasons
    assert "faa" in result.required_named_anchors
    assert "aetherw" in result.required_named_anchors
