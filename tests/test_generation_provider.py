"""Tests for local deterministic generation-provider support."""

from collections.abc import Sequence

import pytest

from aeroragx.generation.grounded import (
    GenerationConfig,
    with_evidence_top_k,
)
from aeroragx.generation.provider import (
    DeterministicGenerationProvider,
    ProviderEvidence,
    create_generation_provider,
)


def make_evidence() -> list[ProviderEvidence]:
    """Create deterministic provider evidence."""

    return [
        ProviderEvidence(
            evidence_id="E1",
            text=(
                "Thermal runaway can propagate "
                "between adjacent battery cells. "
                "Additional material follows."
            ),
        ),
        ProviderEvidence(
            evidence_id="E2",
            text=("Thermal barriers and cooling can reduce propagation risk."),
        ),
        ProviderEvidence(
            evidence_id="E3",
            text=("Monitoring supports earlier fault detection."),
        ),
    ]


def make_config() -> GenerationConfig:
    """Create a valid generation configuration."""

    return GenerationConfig(
        version="0.1",
        provider="fake",
        model_name="deterministic-grounded-v0",
        evidence_top_k=5,
        minimum_evidence_count=1,
        max_context_characters=12_000,
        max_chunk_characters=3_000,
        max_claims=6,
        require_citations=True,
        allow_insufficient_evidence=True,
        include_retrieval_metadata=True,
    )


def test_deterministic_provider_uses_evidence_order() -> None:
    provider = DeterministicGenerationProvider()

    response = provider.generate(
        query="How can thermal runaway propagate?",
        evidence=make_evidence(),
        max_claims=2,
    )

    assert response.insufficient_evidence is False
    assert len(response.claims) == 2
    assert response.claims[0].evidence_ids == ["E1"]
    assert response.claims[1].evidence_ids == ["E2"]
    assert response.answer == (response.claims[0].text + " " + response.claims[1].text)


def test_deterministic_provider_records_inputs() -> None:
    provider = DeterministicGenerationProvider()
    evidence = make_evidence()

    provider.generate(
        query="battery query",
        evidence=evidence,
        max_claims=1,
    )

    assert provider.call_count == 1
    assert provider.received_queries == ["battery query"]
    assert provider.received_max_claims == [1]
    assert [item.evidence_id for item in provider.received_evidence[0]] == ["E1", "E2", "E3"]


def test_deterministic_provider_returns_refusal_without_evidence() -> None:
    provider = DeterministicGenerationProvider()

    response = provider.generate(
        query="unsupported query",
        evidence=[],
        max_claims=3,
    )

    assert response.insufficient_evidence is True
    assert response.claims == []
    assert "insufficient" in response.answer.lower()


def test_deterministic_provider_truncates_long_text() -> None:
    provider = DeterministicGenerationProvider(maximum_claim_characters=25)

    response = provider.generate(
        query="test",
        evidence=[
            ProviderEvidence(
                evidence_id="E1",
                text=("A long evidence passage without punctuation and with extra trailing words"),
            )
        ],
        max_claims=1,
    )

    assert response.claims[0].text.endswith("…")
    assert response.claims[0].evidence_ids == ["E1"]


@pytest.mark.parametrize(
    "provider_name",
    [
        "fake",
        "deterministic",
        "extractive",
        "  FAKE  ",
    ],
)
def test_create_generation_provider_supports_local_names(
    provider_name: str,
) -> None:
    provider = create_generation_provider(provider_name)

    assert isinstance(
        provider,
        DeterministicGenerationProvider,
    )


def test_create_generation_provider_rejects_unknown_name() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported generation provider",
    ):
        create_generation_provider("unknown-provider")


def test_with_evidence_top_k_returns_original_without_override() -> None:
    config = make_config()

    assert (
        with_evidence_top_k(
            config,
            None,
        )
        is config
    )


def test_with_evidence_top_k_applies_valid_override() -> None:
    updated = with_evidence_top_k(
        make_config(),
        8,
    )

    assert updated.evidence_top_k == 8
    assert updated.minimum_evidence_count == 1


def test_with_evidence_top_k_validates_override() -> None:
    config = make_config().model_copy(
        update={
            "minimum_evidence_count": 3,
        }
    )

    with pytest.raises(
        ValueError,
        match=("minimum_evidence_count must not exceed evidence_top_k"),
    ):
        with_evidence_top_k(
            config,
            2,
        )


def test_provider_protocol_accepts_sequence() -> None:
    provider = DeterministicGenerationProvider()
    evidence: Sequence[ProviderEvidence] = make_evidence()

    response = provider.generate(
        query="query",
        evidence=evidence,
        max_claims=1,
    )

    assert response.claims[0].evidence_ids == ["E1"]
