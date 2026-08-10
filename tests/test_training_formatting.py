"""Tests for inference-aligned LoRA formatting."""

from __future__ import annotations

from aeroragx.generation.prompting import (
    ProviderHardeningConfig,
    build_grounded_prompt,
)
from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderEvidence,
    ProviderResponse,
)
from aeroragx.training.dataset import (
    TrainingEvidence,
    TrainingExample,
)
from aeroragx.training.formatting import (
    format_training_example,
)


def make_config() -> ProviderHardeningConfig:
    """Build deterministic prompt configuration."""

    return ProviderHardeningConfig(
        prompt_version="training-test-v1",
    )


def make_example() -> TrainingExample:
    """Build one supported training example."""

    return TrainingExample(
        example_id="train_001",
        query="How is battery heat removed?",
        max_claims=4,
        evidence=[
            TrainingEvidence(
                evidence_id="E1",
                text=("Liquid cooling can remove battery heat."),
                document_id=1001,
                chunk_id=("1001:chunk:00001"),
            ),
            TrainingEvidence(
                evidence_id="E2",
                text=("Temperature sensors monitor battery conditions."),
                document_id=1001,
                chunk_id=("1001:chunk:00002"),
            ),
        ],
        response=ProviderResponse(
            answer=("Liquid cooling removes heat and sensors monitor battery temperature."),
            claims=[
                ProviderClaim(
                    text=("Liquid cooling can remove battery heat."),
                    evidence_ids=["E1"],
                ),
                ProviderClaim(
                    text=("Temperature sensors monitor battery conditions."),
                    evidence_ids=["E2"],
                ),
            ],
            insufficient_evidence=False,
        ),
    )


def test_formatter_reuses_production_prompt() -> None:
    example = make_example()

    config = make_config()

    formatted = format_training_example(
        example,
        provider_config=config,
    )

    expected_prompt = build_grounded_prompt(
        query=example.query,
        evidence=[
            ProviderEvidence(
                evidence_id=(item.evidence_id),
                text=item.text,
            )
            for item in example.evidence
        ],
        max_claims=(example.max_claims),
        config=config,
    )

    assert formatted.messages[0].role == "system"

    assert formatted.messages[0].content == expected_prompt.system_prompt

    assert formatted.messages[1].role == "user"

    assert formatted.messages[1].content == expected_prompt.user_prompt


def test_assistant_payload_matches_provider_response() -> None:
    example = make_example()

    formatted = format_training_example(
        example,
        provider_config=(make_config()),
    )

    assistant = formatted.messages[2]

    assert assistant.role == "assistant"

    parsed = ProviderResponse.model_validate_json(assistant.content)

    assert parsed == example.response


def test_formatter_keeps_provenance_outside_model_messages() -> None:
    example = make_example()

    formatted = format_training_example(
        example,
        provider_config=(make_config()),
    )

    assert formatted.source_document_ids == [1001]

    combined_messages = " ".join(message.content for message in formatted.messages)

    assert "1001:chunk:00001" not in combined_messages
