"""Tests for deterministic multimodal annotation tasks and review summaries."""

import json
from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from aeroragx.evaluation.multimodal_annotation import (
    MultimodalAnnotationResponse,
    MultimodalAnnotationTask,
    build_multimodal_annotation_task,
    build_multimodal_annotation_task_id,
    build_multimodal_annotation_tasks,
    load_multimodal_annotation_responses,
    load_multimodal_annotation_tasks,
    summarize_multimodal_annotation_agreement,
    write_multimodal_annotation_responses,
    write_multimodal_annotation_tasks,
)
from aeroragx.processing.multimodal_provenance import (
    VisualAssetRecord,
    build_visual_asset_id,
    load_visual_asset_records,
)


def make_asset(
    page_number: int = 1,
    asset_type: Literal["figure", "table"] = "figure",
    asset_index: int = 0,
) -> VisualAssetRecord:
    """Create one deterministic visual-asset record for annotation tests."""

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
        caption_text="A verified caption." if asset_type == "figure" else None,
        source_path="data/raw/123.pdf",
        source_url="https://example.com/123.pdf",
        citation_url="https://ntrs.nasa.gov/citations/123",
        document_sha256="source-checksum",
    )


def make_response(
    task: MultimodalAnnotationTask,
    annotator_id: str,
    decision: Literal["confirmed", "rejected", "uncertain"] = "confirmed",
) -> MultimodalAnnotationResponse:
    """Create one annotation response for a known task."""

    return MultimodalAnnotationResponse(
        task_id=task.task_id,
        annotator_id=annotator_id,
        decision=decision,
        notes=None,
    )


def test_build_task_preserves_visual_asset_provenance() -> None:
    asset = make_asset()

    task = build_multimodal_annotation_task(asset)

    assert task.task_id == "123:page:1:figure:000:annotation:v0_1"
    assert task.task_kind == "asset_record_verification"
    assert task.asset_id == asset.asset_id
    assert task.page_id == asset.page_id
    assert task.caption_text == asset.caption_text
    assert task.document_sha256 == asset.document_sha256


def test_task_rejects_a_nondeterministic_task_id() -> None:
    payload = build_multimodal_annotation_task(make_asset()).model_dump()
    payload["task_id"] = "unrelated-task-id"

    with pytest.raises(ValidationError, match="task_id must equal"):
        MultimodalAnnotationTask.model_validate(payload)


def test_task_id_includes_the_asset_identity_and_version() -> None:
    assert (
        build_multimodal_annotation_task_id("123:page:1:table:000")
        == "123:page:1:table:000:annotation:v0_1"
    )


def test_build_tasks_sorts_records_deterministically() -> None:
    tasks = build_multimodal_annotation_tasks(
        [
            make_asset(page_number=2),
            make_asset(page_number=1, asset_type="table"),
            make_asset(page_number=1),
        ]
    )

    assert [task.asset_id for task in tasks] == [
        "123:page:1:figure:000",
        "123:page:1:table:000",
        "123:page:2:figure:000",
    ]


def test_build_tasks_revalidates_a_visual_asset_identity() -> None:
    invalid_asset = make_asset().model_copy(update={"asset_id": "not-a-visual-asset-id"})

    with pytest.raises(ValidationError, match="asset_id must equal"):
        build_multimodal_annotation_tasks([invalid_asset])


def test_write_and_load_tasks_are_deterministic(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    tasks = build_multimodal_annotation_tasks(
        [
            make_asset(page_number=2),
            make_asset(page_number=1),
        ]
    )

    write_multimodal_annotation_tasks(first_path, tasks)
    write_multimodal_annotation_tasks(second_path, list(reversed(tasks)))

    assert first_path.read_text(encoding="utf-8") == second_path.read_text(encoding="utf-8")
    assert [
        json.loads(line)["page_number"]
        for line in first_path.read_text(encoding="utf-8").splitlines()
    ] == [1, 2]
    assert load_multimodal_annotation_tasks(first_path) == tasks


def test_write_tasks_rejects_duplicate_asset_id_before_creating_output(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "tasks.jsonl"
    task = build_multimodal_annotation_task(make_asset())

    with pytest.raises(ValueError, match="Duplicate multimodal annotation task ID"):
        write_multimodal_annotation_tasks(output_path, [task, task])

    assert not output_path.exists()


def test_load_tasks_reports_the_invalid_line_number(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "invalid.jsonl"
    input_path.write_text('{"task_id":"invalid"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid multimodal annotation task on line 1"):
        load_multimodal_annotation_tasks(input_path)


def test_annotation_response_round_trip_is_deterministic(
    tmp_path: Path,
) -> None:
    task = build_multimodal_annotation_task(make_asset())
    output_path = tmp_path / "responses.jsonl"
    responses = [
        make_response(task, "reviewer_b", "uncertain"),
        make_response(task, "reviewer_a", "confirmed"),
    ]

    write_multimodal_annotation_responses(output_path, responses)

    assert [
        json.loads(line)["annotator_id"]
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ] == ["reviewer_a", "reviewer_b"]
    assert load_multimodal_annotation_responses(output_path) == [
        make_response(task, "reviewer_a", "confirmed"),
        make_response(task, "reviewer_b", "uncertain"),
    ]


def test_response_writer_rejects_duplicate_task_and_annotator(
    tmp_path: Path,
) -> None:
    task = build_multimodal_annotation_task(make_asset())
    response = make_response(task, "reviewer_a")

    with pytest.raises(ValueError, match="Duplicate multimodal annotation response"):
        write_multimodal_annotation_responses(
            tmp_path / "responses.jsonl",
            [response, response],
        )


def test_agreement_summary_reports_only_shared_tasks() -> None:
    first_task, second_task = build_multimodal_annotation_tasks(
        [
            make_asset(page_number=1),
            make_asset(page_number=2),
        ]
    )
    responses = [
        make_response(first_task, "reviewer_a", "confirmed"),
        make_response(second_task, "reviewer_a", "rejected"),
        make_response(first_task, "reviewer_b", "confirmed"),
        make_response(second_task, "reviewer_b", "uncertain"),
    ]

    summary = summarize_multimodal_annotation_agreement(
        [first_task, second_task],
        responses,
        "reviewer_a",
        "reviewer_b",
    )

    assert summary.annotator_ids == ("reviewer_a", "reviewer_b")
    assert summary.comparable_task_count == 2
    assert summary.exact_match_count == 1
    assert summary.exact_match_rate == 0.5
    assert summary.disagreement_task_ids == [second_task.task_id]


def test_agreement_rejects_unknown_response_task() -> None:
    task = build_multimodal_annotation_task(make_asset())
    unknown_response = MultimodalAnnotationResponse(
        task_id="unknown:annotation:v0_1",
        annotator_id="reviewer_a",
        decision="confirmed",
    )

    with pytest.raises(ValueError, match="Unknown annotation task ID"):
        summarize_multimodal_annotation_agreement(
            [task],
            [
                unknown_response,
                make_response(task, "reviewer_b"),
            ],
            "reviewer_a",
            "reviewer_b",
        )


def test_agreement_requires_two_distinct_annotators() -> None:
    task = build_multimodal_annotation_task(make_asset())

    with pytest.raises(ValueError, match="two distinct annotator IDs"):
        summarize_multimodal_annotation_agreement(
            [task],
            [make_response(task, "reviewer_a")],
            "reviewer_a",
            "reviewer_a",
        )


def test_versioned_task_data_matches_the_current_visual_asset_slice() -> None:
    source_assets = load_visual_asset_records(
        Path("data/evaluation/multimodal_report_slice_v0_1.jsonl")
    )
    stored_tasks = load_multimodal_annotation_tasks(
        Path("data/evaluation/multimodal_annotation_tasks_v0_1.jsonl")
    )

    assert stored_tasks == build_multimodal_annotation_tasks(source_assets)
