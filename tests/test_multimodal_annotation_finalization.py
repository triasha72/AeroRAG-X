"""Tests for strict Phase 35 multimodal review finalization."""

from typing import Literal

import pytest

from aeroragx.evaluation.multimodal_annotation import (
    MultimodalAnnotationResponse,
    MultimodalAnnotationTask,
    build_multimodal_annotation_tasks,
    validate_complete_multimodal_annotation_review,
)
from aeroragx.processing.multimodal_provenance import (
    VisualAssetRecord,
    build_visual_asset_id,
)


def make_asset(
    page_number: int,
    asset_type: Literal["figure", "table"] = "figure",
    asset_index: int = 0,
) -> VisualAssetRecord:
    """Create a deterministic visual asset for finalization tests."""

    document_id = 123
    page_id = f"{document_id}:page:{page_number}"

    return VisualAssetRecord(
        asset_id=build_visual_asset_id(
            page_id,
            asset_type,
            asset_index,
        ),
        document_id=document_id,
        page_id=page_id,
        page_number=page_number,
        asset_type=asset_type,
        asset_index=asset_index,
        caption_text="Verified figure caption." if asset_type == "figure" else None,
        source_path="data/raw/123.pdf",
        source_url="https://example.com/123.pdf",
        citation_url="https://ntrs.nasa.gov/citations/123",
        document_sha256="source-checksum",
    )


def make_tasks(count: int = 3) -> list[MultimodalAnnotationTask]:
    """Create a deterministic frozen task set."""

    return build_multimodal_annotation_tasks(
        [make_asset(page_number=index + 1) for index in range(count)]
    )


def make_response(
    task: MultimodalAnnotationTask,
    annotator_id: str,
    decision: Literal["confirmed", "rejected", "uncertain"] = "confirmed",
) -> MultimodalAnnotationResponse:
    """Create one valid reviewer response."""

    return MultimodalAnnotationResponse(
        task_id=task.task_id,
        annotator_id=annotator_id,
        decision=decision,
        notes=None,
    )


def test_complete_review_accepts_full_two_reviewer_coverage() -> None:
    tasks = make_tasks()
    responses = [
        *[make_response(task, "reviewer_a", "confirmed") for task in tasks],
        *[make_response(task, "reviewer_b", "confirmed") for task in tasks],
    ]

    summary = validate_complete_multimodal_annotation_review(
        tasks,
        responses,
        "reviewer_a",
        "reviewer_b",
    )

    assert summary.task_count == 3
    assert summary.response_count == 6
    assert summary.complete_review is True
    assert summary.comparable_task_count == 3
    assert summary.exact_match_count == 3
    assert summary.exact_match_rate == 1.0
    assert summary.disagreement_task_ids == []
    assert summary.adjudication_required is False


def test_complete_review_rejects_partial_second_reviewer() -> None:
    tasks = make_tasks()
    responses = [
        *[make_response(task, "reviewer_a") for task in tasks],
        make_response(tasks[0], "reviewer_b"),
    ]

    with pytest.raises(ValueError, match="Incomplete multimodal annotation review"):
        validate_complete_multimodal_annotation_review(
            tasks,
            responses,
            "reviewer_a",
            "reviewer_b",
        )


def test_complete_review_rejects_partial_first_reviewer() -> None:
    tasks = make_tasks()
    responses = [
        make_response(tasks[0], "reviewer_a"),
        *[make_response(task, "reviewer_b") for task in tasks],
    ]

    with pytest.raises(ValueError, match="Incomplete multimodal annotation review"):
        validate_complete_multimodal_annotation_review(
            tasks,
            responses,
            "reviewer_a",
            "reviewer_b",
        )


def test_complete_review_rejects_unexpected_annotator() -> None:
    tasks = make_tasks(count=1)
    responses = [
        make_response(tasks[0], "reviewer_a"),
        make_response(tasks[0], "reviewer_b"),
        make_response(tasks[0], "reviewer_c"),
    ]

    with pytest.raises(ValueError, match="Unexpected annotator IDs"):
        validate_complete_multimodal_annotation_review(
            tasks,
            responses,
            "reviewer_a",
            "reviewer_b",
        )


def test_complete_review_requires_distinct_annotators() -> None:
    tasks = make_tasks(count=1)

    with pytest.raises(ValueError, match="two distinct annotator IDs"):
        validate_complete_multimodal_annotation_review(
            tasks,
            [make_response(tasks[0], "reviewer_a")],
            "reviewer_a",
            "reviewer_a",
        )


def test_complete_review_requires_at_least_one_task() -> None:
    with pytest.raises(ValueError, match="at least one frozen task"):
        validate_complete_multimodal_annotation_review(
            [],
            [],
            "reviewer_a",
            "reviewer_b",
        )


def test_complete_review_rejects_unknown_task_id() -> None:
    tasks = make_tasks(count=1)
    unknown_response = MultimodalAnnotationResponse(
        task_id="unknown:annotation:v0_1",
        annotator_id="reviewer_a",
        decision="confirmed",
        notes=None,
    )
    responses = [
        unknown_response,
        make_response(tasks[0], "reviewer_b"),
    ]

    with pytest.raises(ValueError, match="Unknown annotation task ID"):
        validate_complete_multimodal_annotation_review(
            tasks,
            responses,
            "reviewer_a",
            "reviewer_b",
        )


def test_complete_review_records_one_disagreement() -> None:
    tasks = make_tasks(count=2)
    responses = [
        make_response(tasks[0], "reviewer_a", "confirmed"),
        make_response(tasks[1], "reviewer_a", "rejected"),
        make_response(tasks[0], "reviewer_b", "confirmed"),
        make_response(tasks[1], "reviewer_b", "uncertain"),
    ]

    summary = validate_complete_multimodal_annotation_review(
        tasks,
        responses,
        "reviewer_a",
        "reviewer_b",
    )

    assert summary.exact_match_count == 1
    assert summary.exact_match_rate == 0.5
    assert summary.disagreement_task_ids == [tasks[1].task_id]
    assert summary.adjudication_required is True


def test_complete_review_counts_each_decision_type() -> None:
    tasks = make_tasks(count=3)
    responses = [
        make_response(tasks[0], "reviewer_a", "confirmed"),
        make_response(tasks[1], "reviewer_a", "rejected"),
        make_response(tasks[2], "reviewer_a", "uncertain"),
        make_response(tasks[0], "reviewer_b", "confirmed"),
        make_response(tasks[1], "reviewer_b", "uncertain"),
        make_response(tasks[2], "reviewer_b", "uncertain"),
    ]

    summary = validate_complete_multimodal_annotation_review(
        tasks,
        responses,
        "reviewer_a",
        "reviewer_b",
    )

    assert summary.decision_counts_by_annotator["reviewer_a"] == {
        "confirmed": 1,
        "rejected": 1,
        "uncertain": 1,
    }
    assert summary.decision_counts_by_annotator["reviewer_b"] == {
        "confirmed": 1,
        "rejected": 0,
        "uncertain": 2,
    }


def test_matching_uncertain_decisions_count_as_exact_agreement() -> None:
    tasks = make_tasks(count=1)
    responses = [
        make_response(tasks[0], "reviewer_a", "uncertain"),
        make_response(tasks[0], "reviewer_b", "uncertain"),
    ]

    summary = validate_complete_multimodal_annotation_review(
        tasks,
        responses,
        "reviewer_a",
        "reviewer_b",
    )

    assert summary.exact_match_count == 1
    assert summary.exact_match_rate == 1.0
    assert summary.disagreement_task_ids == []


def test_complete_review_summary_is_input_order_independent() -> None:
    tasks = make_tasks(count=2)
    responses = [
        make_response(tasks[0], "reviewer_a", "confirmed"),
        make_response(tasks[1], "reviewer_a", "rejected"),
        make_response(tasks[0], "reviewer_b", "confirmed"),
        make_response(tasks[1], "reviewer_b", "uncertain"),
    ]

    first_summary = validate_complete_multimodal_annotation_review(
        tasks,
        responses,
        "reviewer_a",
        "reviewer_b",
    )
    second_summary = validate_complete_multimodal_annotation_review(
        list(reversed(tasks)),
        list(reversed(responses)),
        "reviewer_a",
        "reviewer_b",
    )

    assert first_summary == second_summary
