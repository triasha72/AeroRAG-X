"""Tests for deterministic evidence-sufficiency assessment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    SufficiencyConfig,
    load_sufficiency_config,
)


@dataclass(frozen=True)
class TextEvidence:
    """Minimal evidence record used by sufficiency tests."""

    text: str


def make_config(
    **overrides: object,
) -> SufficiencyConfig:
    """Create one validated sufficiency configuration."""

    values: dict[str, object] = {
        "version": "0.1",
        "minimum_evidence_count": 1,
        "minimum_supported_terms": 2,
        "minimum_query_term_coverage": 0.60,
        "minimum_single_evidence_coverage": 0.35,
        "exact_query_minimum_coverage": 0.75,
        "require_all_numeric_terms": True,
        "require_named_anchors": True,
    }
    values.update(overrides)

    return SufficiencyConfig.model_validate(values)


def assess(
    query: str,
    evidence: list[str],
    *,
    config: SufficiencyConfig | None = None,
):
    """Assess a query against simple text evidence."""

    assessor = EvidenceSufficiencyAssessor(config or make_config())

    return assessor.assess(
        query=query,
        evidence=[TextEvidence(text=text) for text in evidence],
    )


def test_load_valid_sufficiency_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sufficiency.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            "minimum_evidence_count: 1\n"
            "minimum_supported_terms: 2\n"
            "minimum_query_term_coverage: 0.60\n"
            "minimum_single_evidence_coverage: 0.35\n"
            "exact_query_minimum_coverage: 0.75\n"
            "require_all_numeric_terms: true\n"
            "require_named_anchors: true\n"
        ),
        encoding="utf-8",
    )

    config = load_sufficiency_config(path)

    assert config.minimum_query_term_coverage == 0.60
    assert config.require_named_anchors is True


def test_config_rejects_non_mapping_yaml(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sufficiency.yaml"
    path.write_text(
        "- one\n- two\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must contain a YAML mapping",
    ):
        load_sufficiency_config(path)


def test_config_rejects_unknown_fields() -> None:
    with pytest.raises(
        ValueError,
        match="Extra inputs are not permitted",
    ):
        SufficiencyConfig.model_validate(
            {
                **make_config().model_dump(),
                "unexpected": True,
            }
        )


def test_config_rejects_weaker_exact_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="exact_query_minimum_coverage",
    ):
        make_config(
            minimum_query_term_coverage=0.80,
            exact_query_minimum_coverage=0.70,
        )


def test_accepts_supported_battery_query() -> None:
    result = assess(
        ("How can battery thermal runaway propagate in electric aircraft?"),
        [("Battery thermal runaway can propagate between adjacent cells in electric aircraft.")],
    )

    assert result.sufficient is True
    assert result.reasons == []
    assert result.query_term_coverage >= 0.60


def test_accepts_cooling_morphology() -> None:
    result = assess(
        "How are aircraft battery systems cooled?",
        [("Aircraft battery system cooling uses liquid and air thermal management.")],
    )

    assert result.sufficient is True
    assert "cool" in result.supported_terms


def test_accepts_detection_morphology() -> None:
    result = assess(
        ("How can lithium-ion battery fires be detected in aviation applications?"),
        [("Lithium ion battery fire detection supports aviation safety applications.")],
    )

    assert result.sufficient is True
    assert "detect" in result.supported_terms


def test_rejects_exact_ticket_price_query() -> None:
    result = assess(
        ("What was the exact passenger ticket price of NASA's 2035 hydrogen airliner?"),
        [
            (
                "NASA studied hydrogen aircraft concepts "
                "for possible service in 2035 and compared "
                "fuel prices."
            )
        ],
    )

    assert result.sufficient is False
    assert "low_query_term_coverage" in result.reasons
    assert "ticket" in result.unsupported_terms


def test_rejects_fictional_named_anchor() -> None:
    result = assess(
        ("Which fictional Zephyr-X battery received FAA certification on January 1, 2040?"),
        [("FAA certification research covers electric aircraft battery systems through 2040.")],
    )

    assert result.sufficient is False
    assert "missing_named_anchor_support" in result.reasons
    assert "zephyr" in result.required_named_anchors
    assert "zephyr" not in result.supported_named_anchors


def test_rejects_missing_numeric_support() -> None:
    result = assess(
        "What happened to the aircraft battery in 2040?",
        [("The aircraft battery program continued through future research.")],
    )

    assert result.sufficient is False
    assert "missing_numeric_support" in result.reasons
    assert result.required_numeric_terms == ["2040"]
    assert result.supported_numeric_terms == []


def test_rejects_low_single_evidence_concentration() -> None:
    result = assess(
        ("What thermal safety controls protect hybrid electric aircraft propulsion?"),
        [
            "Thermal design affects aircraft.",
            "Hybrid systems are under study.",
            "Electric propulsion is developing.",
            "Safety controls require validation.",
        ],
        config=make_config(
            minimum_query_term_coverage=0.60,
            minimum_single_evidence_coverage=0.60,
            exact_query_minimum_coverage=0.75,
        ),
    )

    assert result.sufficient is False
    assert "low_single_evidence_coverage" in result.reasons


def test_rejects_insufficient_evidence_count() -> None:
    result = assess(
        "How is aircraft battery cooling managed?",
        [("Aircraft battery cooling uses thermal-management systems.")],
        config=make_config(
            minimum_evidence_count=2,
        ),
    )

    assert result.sufficient is False
    assert "insufficient_evidence_count" in result.reasons


def test_rejects_query_without_informative_terms() -> None:
    result = assess(
        "What is it?",
        ["Some evidence exists."],
    )

    assert result.sufficient is False
    assert "no_informative_query_terms" in result.reasons


def test_blank_query_is_rejected() -> None:
    assessor = EvidenceSufficiencyAssessor(make_config())

    with pytest.raises(
        ValueError,
        match="query must not be blank",
    ):
        assessor.assess(
            query="   ",
            evidence=[],
        )


def test_result_preserves_auditable_fields() -> None:
    result = assess(
        "How is NASA battery cooling tested in 2035?",
        [("NASA tested battery cooling systems in 2035.")],
    )

    assert result.evidence_count == 1
    assert result.required_numeric_terms == ["2035"]
    assert result.supported_numeric_terms == ["2035"]
    assert result.required_named_anchors == ["nasa"]
    assert result.supported_named_anchors == ["nasa"]
