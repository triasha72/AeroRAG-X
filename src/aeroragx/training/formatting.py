"""Convert validated examples into inference-aligned chat training records."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.generation.prompting import (
    ProviderHardeningConfig,
    build_grounded_prompt,
)
from aeroragx.generation.provider import (
    ProviderEvidence,
)
from aeroragx.training.dataset import (
    TrainingExample,
)

type TrainingMessageRole = Literal[
    "system",
    "user",
    "assistant",
]


class TrainingMessage(BaseModel):
    """One chat message used for supervised fine-tuning."""

    model_config = ConfigDict(
        extra="forbid",
    )

    role: TrainingMessageRole

    content: str = Field(
        min_length=1,
    )


class FormattedTrainingExample(BaseModel):
    """One inference-aligned supervised chat example."""

    model_config = ConfigDict(
        extra="forbid",
    )

    example_id: str = Field(
        min_length=1,
    )

    messages: list[TrainingMessage] = Field(
        min_length=3,
        max_length=3,
    )

    source_document_ids: list[int]


def format_training_example(
    example: TrainingExample,
    *,
    provider_config: ProviderHardeningConfig,
) -> FormattedTrainingExample:
    """Format one example using the production prompt builder."""

    provider_evidence = [
        ProviderEvidence(
            evidence_id=item.evidence_id,
            text=item.text,
        )
        for item in example.evidence
    ]

    prompt = build_grounded_prompt(
        query=example.query,
        evidence=provider_evidence,
        max_claims=example.max_claims,
        config=provider_config,
    )

    assistant_content = json.dumps(
        example.response.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return FormattedTrainingExample(
        example_id=example.example_id,
        messages=[
            TrainingMessage(
                role="system",
                content=prompt.system_prompt,
            ),
            TrainingMessage(
                role="user",
                content=prompt.user_prompt,
            ),
            TrainingMessage(
                role="assistant",
                content=assistant_content,
            ),
        ],
        source_document_ids=list(example.source_document_ids),
    )


def format_training_examples(
    examples: Sequence[TrainingExample],
    *,
    provider_config: ProviderHardeningConfig,
) -> list[FormattedTrainingExample]:
    """Format multiple examples deterministically."""

    return [
        format_training_example(
            example,
            provider_config=provider_config,
        )
        for example in examples
    ]
