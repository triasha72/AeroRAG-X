"""Regression tests for the Phase 27 scope-qualifier safeguard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    SufficiencyConfig,
    load_sufficiency_config,
)

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Evidence:
    """Minimal evidence object used by sufficiency tests."""

    text: str


def _assessor(*, require_scope_qualifiers: bool) -> EvidenceSufficiencyAssessor:
    return EvidenceSufficiencyAssessor(
        SufficiencyConfig(
            version="0.3.0",
            require_claim_qualifiers=True,
            require_scope_qualifiers=require_scope_qualifiers,
        )
    )


def test_v030_config_enables_scope_qualifier_safeguard() -> None:
    config = load_sufficiency_config(ROOT / "configs/sufficiency_v0_3_0.yaml")

    assert config.version == "0.3.0"
    assert config.require_scope_qualifiers is True


def test_scope_guard_rejects_unsupported_zero_risk_guarantee() -> None:
    result = _assessor(require_scope_qualifiers=True).assess(
        query=(
            "Which certification regulation guarantees that hydrogen-powered "
            "aircraft will have zero operational risk?"
        ),
        evidence=[
            Evidence(
                "Certification regulations discuss hydrogen-powered aircraft, "
                "operational risk assessment, and safety analysis."
            )
        ],
    )

    assert result.sufficient is False
    assert "missing_scope_qualifier_support" in result.reasons
    assert result.required_scope_qualifiers
    assert result.supported_scope_qualifiers == []


def test_scope_guard_rejects_unsupported_universal_permanent_claim() -> None:
    result = _assessor(require_scope_qualifiers=True).assess(
        query=(
            "What date will all commercial aircraft permanently replace "
            "turbine engines with batteries?"
        ),
        evidence=[
            Evidence(
                "Future dates for commercial aircraft concepts discuss "
                "replacement of turbine engines with batteries."
            )
        ],
    )

    assert result.sufficient is False
    assert "missing_scope_qualifier_support" in result.reasons


def test_scope_guard_rejects_unsupported_every_aircraft_claim() -> None:
    result = _assessor(require_scope_qualifiers=True).assess(
        query=(
            "Which future weather event will make every "
            "distributed-propulsion aircraft unable to fly?"
        ),
        evidence=[
            Evidence(
                "Future weather events can affect distributed-propulsion "
                "aircraft operations and flight planning."
            )
        ],
    )

    assert result.sufficient is False
    assert "missing_scope_qualifier_support" in result.reasons


def test_scope_guard_accepts_explicitly_supported_scope() -> None:
    result = _assessor(require_scope_qualifiers=True).assess(
        query="Does every battery-electric aircraft require redundant cooling?",
        evidence=[
            Evidence(
                "Every battery-electric aircraft requires redundant cooling "
                "under this stated design requirement."
            )
        ],
    )

    assert result.sufficient is True
    assert result.required_scope_qualifiers == ["every_battery_electric"]
    assert result.supported_scope_qualifiers == ["every_battery_electric"]


def test_scope_guard_is_opt_in() -> None:
    result = _assessor(require_scope_qualifiers=False).assess(
        query=(
            "Which certification regulation guarantees that hydrogen-powered "
            "aircraft will have zero operational risk?"
        ),
        evidence=[
            Evidence(
                "Certification regulations discuss hydrogen-powered aircraft, "
                "operational risk assessment, and safety analysis."
            )
        ],
    )

    assert "missing_scope_qualifier_support" not in result.reasons
