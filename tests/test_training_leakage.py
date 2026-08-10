"""Tests for protected-evaluation leakage checks."""

from __future__ import annotations

from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderResponse,
)
from aeroragx.training.dataset import (
    TrainingEvidence,
    TrainingExample,
    audit_training_leakage,
)


def make_example(
    *,
    example_id: str,
    query: str,
    answer: str,
) -> TrainingExample:
    """Build one supported training example."""

    return TrainingExample(
        example_id=example_id,
        query=query,
        evidence=[
            TrainingEvidence(
                evidence_id="E1",
                text="Independent evidence.",
                document_id=9001,
                chunk_id=("9001:chunk:00001"),
            )
        ],
        response=ProviderResponse(
            answer=answer,
            claims=[
                ProviderClaim(
                    text=answer,
                    evidence_ids=["E1"],
                )
            ],
            insufficient_evidence=False,
        ),
    )


def test_clean_training_example_has_no_leakage() -> None:
    example = make_example(
        example_id="train_001",
        query=("How does a radiator reject aircraft waste heat?"),
        answer=("A radiator transfers waste heat to the surrounding flow."),
    )

    report = audit_training_leakage(
        [example],
        protected_queries={"core_001": ("How can battery thermal runaway propagate?")},
        protected_answers={"core_001": ("Thermal runaway can propagate between cells.")},
    )

    assert report.has_leakage is False

    assert report.findings == []


def test_exact_query_overlap_is_detected() -> None:
    protected_query = "How can battery thermal runaway propagate?"

    example = make_example(
        example_id="train_001",
        query=protected_query,
        answer="Independent answer.",
    )

    report = audit_training_leakage(
        [example],
        protected_queries={
            "core_001": protected_query,
        },
        protected_answers={},
    )

    assert report.has_leakage is True

    assert {finding.kind for finding in report.findings} == {
        "exact_query",
    }


def test_normalized_query_overlap_is_detected() -> None:
    example = make_example(
        example_id="train_001",
        query=("HOW   CAN BATTERY THERMAL RUNAWAY PROPAGATE?"),
        answer="Independent answer.",
    )

    report = audit_training_leakage(
        [example],
        protected_queries={"core_001": ("How can battery thermal runaway propagate?")},
        protected_answers={},
    )

    kinds = {finding.kind for finding in report.findings}

    assert "normalized_query" in kinds


def test_protected_example_id_is_detected() -> None:
    example = make_example(
        example_id="core_001",
        query="Independent question",
        answer="Independent answer",
    )

    report = audit_training_leakage(
        [example],
        protected_queries={"core_001": ("Protected question")},
        protected_answers={},
    )

    kinds = {finding.kind for finding in report.findings}

    assert "protected_example_id" in kinds


def test_target_answer_overlap_is_detected() -> None:
    protected_answer = "Thermal runaway can propagate between cells."

    example = make_example(
        example_id="train_001",
        query="Independent question",
        answer=protected_answer,
    )

    report = audit_training_leakage(
        [example],
        protected_queries={},
        protected_answers={"core_001": (protected_answer)},
    )

    kinds = {finding.kind for finding in report.findings}

    assert "exact_target_answer" in kinds


def test_normalized_target_answer_overlap_is_detected() -> None:
    example = make_example(
        example_id="train_001",
        query="Independent question",
        answer=("THERMAL   RUNAWAY can propagate BETWEEN cells."),
    )

    report = audit_training_leakage(
        [example],
        protected_queries={},
        protected_answers={"core_001": ("Thermal runaway can propagate between cells.")},
    )

    kinds = {finding.kind for finding in report.findings}

    assert "normalized_target_answer" in kinds
