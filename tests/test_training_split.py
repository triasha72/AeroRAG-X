"""Tests for document-aware training splits."""

from __future__ import annotations

import pytest

from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderResponse,
)
from aeroragx.training.dataset import (
    TrainingEvidence,
    TrainingExample,
)
from aeroragx.training.split import (
    split_training_examples,
)


def make_example(
    *,
    example_id: str,
    document_ids: list[int],
) -> TrainingExample:
    """Build one example from specified source documents."""

    evidence = [
        TrainingEvidence(
            evidence_id=f"E{index}",
            text=(f"Evidence from document {document_id}."),
            document_id=document_id,
            chunk_id=(f"{document_id}:chunk:{index:05d}"),
        )
        for index, document_id in enumerate(
            document_ids,
            start=1,
        )
    ]

    return TrainingExample(
        example_id=example_id,
        query=f"Question {example_id}",
        evidence=evidence,
        response=ProviderResponse(
            answer=f"Answer {example_id}.",
            claims=[
                ProviderClaim(
                    text=(f"Claim {example_id}."),
                    evidence_ids=[item.evidence_id for item in evidence],
                )
            ],
            insufficient_evidence=False,
        ),
    )


def test_split_is_deterministic() -> None:
    examples = [
        make_example(
            example_id="a",
            document_ids=[1001],
        ),
        make_example(
            example_id="b",
            document_ids=[1002],
        ),
        make_example(
            example_id="c",
            document_ids=[1003],
        ),
        make_example(
            example_id="d",
            document_ids=[1004],
        ),
    ]

    first = split_training_examples(
        examples,
        dev_fraction=0.5,
        seed=42,
    )

    second = split_training_examples(
        list(reversed(examples)),
        dev_fraction=0.5,
        seed=42,
    )

    assert [item.example_id for item in first.train] == [item.example_id for item in second.train]

    assert [item.example_id for item in first.dev] == [item.example_id for item in second.dev]


def test_shared_documents_remain_in_same_split() -> None:
    examples = [
        make_example(
            example_id="a",
            document_ids=[1001],
        ),
        make_example(
            example_id="b",
            document_ids=[1001, 1002],
        ),
        make_example(
            example_id="c",
            document_ids=[1002],
        ),
        make_example(
            example_id="d",
            document_ids=[2000],
        ),
    ]

    split = split_training_examples(
        examples,
        dev_fraction=0.5,
        seed=123,
    )

    train_ids = {item.example_id for item in split.train}

    dev_ids = {item.example_id for item in split.dev}

    linked = {
        "a",
        "b",
        "c",
    }

    assert linked <= train_ids or linked <= dev_ids

    assert not (split.train_document_ids & split.dev_document_ids)


def test_invalid_dev_fraction_is_rejected() -> None:
    example = make_example(
        example_id="a",
        document_ids=[1001],
    )

    with pytest.raises(
        ValueError,
        match="dev_fraction",
    ):
        split_training_examples(
            [example],
            dev_fraction=1.5,
        )


def test_duplicate_example_ids_are_rejected() -> None:
    example = make_example(
        example_id="a",
        document_ids=[1001],
    )

    with pytest.raises(
        ValueError,
        match="duplicate example IDs",
    ):
        split_training_examples(
            [example, example],
        )
