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
    document_ids: list[int] | None = None,
) -> TrainingExample:
    """Build one supported training example."""

    resolved_document_ids = document_ids or [9001]

    evidence = [
        TrainingEvidence(
            evidence_id=(f"E{index}"),
            text=(f"Independent evidence from document {document_id}."),
            document_id=(document_id),
            chunk_id=(f"{document_id}:chunk:{index:05d}"),
        )
        for index, document_id in enumerate(
            resolved_document_ids,
            start=1,
        )
    ]

    return TrainingExample(
        example_id=example_id,
        query=query,
        evidence=evidence,
        response=ProviderResponse(
            answer=answer,
            claims=[
                ProviderClaim(
                    text=answer,
                    evidence_ids=[evidence_item.evidence_id for evidence_item in evidence],
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
        protected_document_ids={20210025384},
    )

    assert report.has_leakage is False

    assert report.protected_document_count == 1

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


def test_protected_source_document_is_detected() -> None:
    example = make_example(
        example_id="train_001",
        query="Independent question",
        answer="Independent answer.",
        document_ids=[20210025384],
    )

    report = audit_training_leakage(
        [example],
        protected_queries={},
        protected_answers={},
        protected_document_ids={20210025384},
    )

    assert report.has_leakage is True

    findings = [
        finding for finding in report.findings if finding.kind == "protected_source_document"
    ]

    assert len(findings) == 1

    assert findings[0].protected_reference == "20210025384"


def test_clean_source_document_is_not_flagged() -> None:
    example = make_example(
        example_id="train_001",
        query="Independent question",
        answer="Independent answer.",
        document_ids=[20140017337],
    )

    report = audit_training_leakage(
        [example],
        protected_queries={},
        protected_answers={},
        protected_document_ids={20210025384},
    )

    assert report.has_leakage is False

    assert report.findings == []


def test_all_protected_source_documents_are_reported() -> None:
    example = make_example(
        example_id="train_001",
        query=("Independent synthesis question"),
        answer=("Independent synthesis answer."),
        document_ids=[
            20210025384,
            20140017337,
            20170007959,
        ],
    )

    report = audit_training_leakage(
        [example],
        protected_queries={},
        protected_answers={},
        protected_document_ids={
            20210025384,
            20170007959,
        },
    )

    protected_document_findings = [
        finding.protected_reference
        for finding in report.findings
        if finding.kind == "protected_source_document"
    ]

    assert protected_document_findings == [
        "20170007959",
        "20210025384",
    ]
