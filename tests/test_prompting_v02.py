"""Regression tests for grounded JSON prompt v0.2."""

from aeroragx.generation.prompting import (
    ProviderHardeningConfig,
    build_grounded_prompt,
)
from aeroragx.generation.provider import (
    ProviderEvidence,
)


def make_config(
    prompt_version: str,
) -> ProviderHardeningConfig:
    """Create a deterministic provider-hardening config."""

    return ProviderHardeningConfig(
        version="0.2",
        prompt_version=prompt_version,
        max_query_characters=2000,
        max_evidence_characters=12000,
        evidence_start_marker="<AERORAGX_EVIDENCE>",
        evidence_end_marker="</AERORAGX_EVIDENCE>",
        prompt_injection_policy="block",
        timeout_seconds=30.0,
        max_retries=2,
        retry_backoff_seconds=1.0,
        redact_secrets=True,
    )


def make_prompt(
    prompt_version: str,
) -> str:
    """Build one test system prompt."""

    prompt = build_grounded_prompt(
        query="What does the evidence show?",
        evidence=[
            ProviderEvidence(
                evidence_id="E1",
                text="The supplied evidence supports one technical statement.",
            )
        ],
        max_claims=3,
        config=make_config(prompt_version),
    )

    return prompt.system_prompt


def test_v01_prompt_does_not_gain_v02_rules() -> None:
    """Keep the original benchmark prompt reproducible."""

    system_prompt = make_prompt("grounded-json-v0.1")

    assert (
        "If insufficient_evidence=false, return at least one supported claim." not in system_prompt
    )

    assert "evidence_ids must be unique" not in system_prompt


def test_v02_requires_supported_claim() -> None:
    """Prompt v0.2 should explicitly require claims for supported answers."""

    system_prompt = make_prompt("grounded-json-v0.2")

    assert "If insufficient_evidence=false, return at least one supported claim." in system_prompt


def test_v02_requires_unique_evidence_ids() -> None:
    """Prompt v0.2 should prohibit duplicate evidence IDs."""

    system_prompt = make_prompt("grounded-json-v0.2")

    assert "evidence_ids must be unique" in system_prompt


def test_v02_requires_complete_json() -> None:
    """Prompt v0.2 should prioritize complete structured output."""

    system_prompt = make_prompt("grounded-json-v0.2")

    assert "Return exactly one complete JSON object" in system_prompt

    assert "within the generation budget" in system_prompt
