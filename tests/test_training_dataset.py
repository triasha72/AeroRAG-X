"""Tests for LoRA training-example validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderResponse,
)
from aeroragx.training.dataset import (
    TrainingEvidence,
    TrainingExample,
    load_training_examples,
    write_training_examples,
)


def make_supported_example(
    *,
    example_id: str = "train_001",
) -> TrainingExample:
    """Build one valid supported training example."""

    return TrainingExample(
        example_id=example_id,
        query=("How can a thermal-management system remove battery heat?"),
        max_claims=4,
        evidence=[
            TrainingEvidence(
                evidence_id="E1",
                text=("A liquid cooling loop can remove battery heat."),
                document_id=1001,
                chunk_id=("1001:chunk:00001"),
            ),
            TrainingEvidence(
                evidence_id="E2",
                text=("Temperature monitoring helps identify abnormal thermal behavior."),
                document_id=1001,
                chunk_id=("1001:chunk:00002"),
            ),
        ],
        response=ProviderResponse(
            answer=(
                "Battery heat can be "
                "removed with liquid cooling "
                "while temperature monitoring "
                "tracks abnormal behavior."
            ),
            claims=[
                ProviderClaim(
                    text=("A liquid cooling loop can remove battery heat."),
                    evidence_ids=["E1"],
                ),
                ProviderClaim(
                    text=("Temperature monitoring can identify abnormal thermal behavior."),
                    evidence_ids=["E2"],
                ),
            ],
            insufficient_evidence=False,
        ),
    )


def test_supported_training_example_is_valid() -> None:
    example = make_supported_example()

    assert example.example_id == "train_001"

    assert example.source_document_ids == (1001,)

    assert len(example.response.claims) == 2


def test_duplicate_evidence_ids_are_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match=("Training evidence IDs must be unique"),
    ):
        TrainingExample(
            example_id="train_001",
            query="Question",
            evidence=[
                TrainingEvidence(
                    evidence_id="E1",
                    text="First",
                    document_id=1001,
                    chunk_id="chunk-1",
                ),
                TrainingEvidence(
                    evidence_id="E1",
                    text="Second",
                    document_id=1001,
                    chunk_id="chunk-2",
                ),
            ],
            response=ProviderResponse(
                answer="Answer",
                claims=[
                    ProviderClaim(
                        text="Claim",
                        evidence_ids=["E1"],
                    )
                ],
                insufficient_evidence=False,
            ),
        )


def test_duplicate_chunks_are_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match=("Training evidence chunk IDs must be unique"),
    ):
        TrainingExample(
            example_id="train_001",
            query="Question",
            evidence=[
                TrainingEvidence(
                    evidence_id="E1",
                    text="First",
                    document_id=1001,
                    chunk_id="chunk-1",
                ),
                TrainingEvidence(
                    evidence_id="E2",
                    text="Second",
                    document_id=1001,
                    chunk_id="chunk-1",
                ),
            ],
            response=ProviderResponse(
                answer="Answer",
                claims=[
                    ProviderClaim(
                        text="Claim",
                        evidence_ids=["E1"],
                    )
                ],
                insufficient_evidence=False,
            ),
        )


def test_unknown_claim_evidence_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match=("unknown evidence IDs"),
    ):
        TrainingExample(
            example_id="train_001",
            query="Question",
            evidence=[
                TrainingEvidence(
                    evidence_id="E1",
                    text="Evidence",
                    document_id=1001,
                    chunk_id="chunk-1",
                )
            ],
            response=ProviderResponse(
                answer="Answer",
                claims=[
                    ProviderClaim(
                        text="Claim",
                        evidence_ids=["E9"],
                    )
                ],
                insufficient_evidence=False,
            ),
        )


def test_supported_response_requires_claims() -> None:
    with pytest.raises(
        ValidationError,
        match=("supported training response must contain at least one claim"),
    ):
        TrainingExample(
            example_id="train_001",
            query="Question",
            evidence=[
                TrainingEvidence(
                    evidence_id="E1",
                    text="Evidence",
                    document_id=1001,
                    chunk_id="chunk-1",
                )
            ],
            response=ProviderResponse(
                answer="Answer",
                claims=[],
                insufficient_evidence=False,
            ),
        )


def test_insufficient_response_rejects_claims() -> None:
    with pytest.raises(
        ValidationError,
        match=("insufficient-evidence training response must not contain claims"),
    ):
        TrainingExample(
            example_id="train_001",
            query="Question",
            evidence=[
                TrainingEvidence(
                    evidence_id="E1",
                    text="Insufficient evidence",
                    document_id=1001,
                    chunk_id="chunk-1",
                )
            ],
            response=ProviderResponse(
                answer=("The supplied evidence is insufficient."),
                claims=[
                    ProviderClaim(
                        text="Unsupported claim",
                        evidence_ids=["E1"],
                    )
                ],
                insufficient_evidence=True,
            ),
        )


def test_training_jsonl_round_trip(
    tmp_path: Path,
) -> None:
    output = tmp_path / "training.jsonl"

    example = make_supported_example()

    write_training_examples(
        output,
        [example],
    )

    loaded = load_training_examples(output)

    assert loaded == [example]


def test_loader_rejects_duplicate_example_ids(
    tmp_path: Path,
) -> None:
    path = tmp_path / "training.jsonl"

    serialized = make_supported_example().model_dump_json()

    path.write_text(
        serialized + "\n" + serialized + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=("Duplicate training example ID"),
    ):
        load_training_examples(path)
