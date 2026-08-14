"""Deterministic task and response contracts for multimodal annotation review."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.processing.multimodal_provenance import (
    VisualAssetRecord,
    VisualAssetType,
    build_visual_asset_id,
)

AnnotationDecision = Literal["confirmed", "rejected", "uncertain"]
AnnotationTaskKind = Literal["asset_record_verification"]
AnnotationTaskVersion = Literal["v0_1"]


def build_multimodal_annotation_task_id(
    asset_id: str,
    task_version: AnnotationTaskVersion = "v0_1",
) -> str:
    """Return the deterministic identifier for an annotation task."""

    return f"{asset_id}:annotation:{task_version}"


class MultimodalAnnotationTask(BaseModel):
    """A page-linked task for independently reviewing one visual-asset record."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    task_id: str = Field(min_length=1)
    task_version: AnnotationTaskVersion = "v0_1"
    task_kind: AnnotationTaskKind = "asset_record_verification"
    asset_id: str = Field(min_length=1)
    document_id: int
    page_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    asset_type: VisualAssetType
    asset_index: int = Field(ge=0)
    caption_text: str | None = None
    source_path: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        """Ensure every task preserves its deterministic page and asset identity."""

        expected_page_id = f"{self.document_id}:page:{self.page_number}"

        if self.page_id != expected_page_id:
            raise ValueError(
                f"page_id must equal '{expected_page_id}' for document_id and page_number."
            )

        expected_asset_id = build_visual_asset_id(
            self.page_id,
            self.asset_type,
            self.asset_index,
        )

        if self.asset_id != expected_asset_id:
            raise ValueError(
                "asset_id must equal "
                f"'{expected_asset_id}' for page_id, asset_type, and asset_index."
            )

        expected_task_id = build_multimodal_annotation_task_id(
            self.asset_id,
            self.task_version,
        )

        if self.task_id != expected_task_id:
            raise ValueError(
                f"task_id must equal '{expected_task_id}' for asset_id and task_version."
            )

        return self


class MultimodalAnnotationResponse(BaseModel):
    """One independent reviewer decision for one annotation task."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    task_id: str = Field(min_length=1)
    annotator_id: str = Field(min_length=1)
    decision: AnnotationDecision
    notes: str | None = None


class MultimodalAnnotationAgreementSummary(BaseModel):
    """Raw exact-match summary for two independent annotation response sets."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    task_version: AnnotationTaskVersion = "v0_1"
    annotator_ids: tuple[str, str]
    comparable_task_count: int = Field(ge=1)
    exact_match_count: int = Field(ge=0)
    exact_match_rate: float = Field(ge=0.0, le=1.0)
    disagreement_task_ids: list[str]

    @model_validator(mode="after")
    def validate_summary(self) -> Self:
        """Ensure the summary represents two distinct annotators and valid counts."""

        if self.annotator_ids[0] == self.annotator_ids[1]:
            raise ValueError("Agreement requires two distinct annotator IDs.")

        if self.exact_match_count > self.comparable_task_count:
            raise ValueError("exact_match_count cannot exceed comparable_task_count.")

        expected_disagreement_count = self.comparable_task_count - self.exact_match_count

        if len(self.disagreement_task_ids) != expected_disagreement_count:
            raise ValueError("disagreement_task_ids must account for every non-matching task.")

        if len(set(self.disagreement_task_ids)) != len(self.disagreement_task_ids):
            raise ValueError("disagreement_task_ids must not contain duplicates.")

        expected_rate = self.exact_match_count / self.comparable_task_count

        if abs(self.exact_match_rate - expected_rate) > 1e-12:
            raise ValueError("exact_match_rate must match the recorded exact-match counts.")

        return self


def build_multimodal_annotation_task(
    asset: VisualAssetRecord,
    task_version: AnnotationTaskVersion = "v0_1",
) -> MultimodalAnnotationTask:
    """Build one review task from a fully revalidated visual-asset record."""

    validated_asset = VisualAssetRecord.model_validate(asset.model_dump(mode="python"))

    return MultimodalAnnotationTask(
        task_id=build_multimodal_annotation_task_id(
            validated_asset.asset_id,
            task_version,
        ),
        task_version=task_version,
        asset_id=validated_asset.asset_id,
        document_id=validated_asset.document_id,
        page_id=validated_asset.page_id,
        page_number=validated_asset.page_number,
        asset_type=validated_asset.asset_type,
        asset_index=validated_asset.asset_index,
        caption_text=validated_asset.caption_text,
        source_path=validated_asset.source_path,
        source_url=validated_asset.source_url,
        citation_url=validated_asset.citation_url,
        document_sha256=validated_asset.document_sha256,
    )


def build_multimodal_annotation_tasks(
    assets: Sequence[VisualAssetRecord],
    task_version: AnnotationTaskVersion = "v0_1",
) -> list[MultimodalAnnotationTask]:
    """Build deterministically ordered review tasks from page-linked visual assets."""

    validated_assets = _revalidate_visual_asset_records(assets)
    ordered_assets = sorted(
        validated_assets,
        key=lambda asset: (
            asset.document_id,
            asset.page_number,
            asset.asset_type,
            asset.asset_index,
        ),
    )
    tasks = [
        build_multimodal_annotation_task(
            asset,
            task_version=task_version,
        )
        for asset in ordered_assets
    ]

    return _revalidate_annotation_tasks(tasks)


def load_multimodal_annotation_tasks(
    path: Path,
) -> list[MultimodalAnnotationTask]:
    """Load page-linked multimodal annotation tasks from a JSONL file."""

    tasks: list[MultimodalAnnotationTask] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            task = MultimodalAnnotationTask.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(
                f"Invalid multimodal annotation task on line {line_number}: {exc}"
            ) from exc

        tasks.append(task)

    return _revalidate_annotation_tasks(tasks)


def write_multimodal_annotation_tasks(
    path: Path,
    tasks: Sequence[MultimodalAnnotationTask],
) -> None:
    """Write annotation tasks as deterministic JSON Lines."""

    validated_tasks = _revalidate_annotation_tasks(tasks)
    ordered_tasks = sorted(
        validated_tasks,
        key=lambda task: (
            task.document_id,
            task.page_number,
            task.asset_type,
            task.asset_index,
        ),
    )
    _write_jsonl(
        path,
        [task.model_dump(mode="json") for task in ordered_tasks],
    )


def load_multimodal_annotation_responses(
    path: Path,
) -> list[MultimodalAnnotationResponse]:
    """Load independent multimodal annotation responses from a JSONL file."""

    responses: list[MultimodalAnnotationResponse] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            response = MultimodalAnnotationResponse.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(
                f"Invalid multimodal annotation response on line {line_number}: {exc}"
            ) from exc

        responses.append(response)

    return _revalidate_annotation_responses(responses)


def write_multimodal_annotation_responses(
    path: Path,
    responses: Sequence[MultimodalAnnotationResponse],
) -> None:
    """Write independent annotation responses as deterministic JSON Lines."""

    validated_responses = _revalidate_annotation_responses(responses)
    ordered_responses = sorted(
        validated_responses,
        key=lambda response: (
            response.task_id,
            response.annotator_id,
        ),
    )
    _write_jsonl(
        path,
        [response.model_dump(mode="json") for response in ordered_responses],
    )


def summarize_multimodal_annotation_agreement(
    tasks: Sequence[MultimodalAnnotationTask],
    responses: Sequence[MultimodalAnnotationResponse],
    first_annotator_id: str,
    second_annotator_id: str,
) -> MultimodalAnnotationAgreementSummary:
    """Summarize raw exact agreement for responses shared by two annotators.

    This deliberately reports raw exact decision agreement only. It does not
    calculate chance-corrected reliability, and it does not imply that an
    independent annotation study has already been completed.
    """

    first_annotator_id = first_annotator_id.strip()
    second_annotator_id = second_annotator_id.strip()

    if not first_annotator_id or not second_annotator_id:
        raise ValueError("Agreement requires non-empty annotator IDs.")

    if first_annotator_id == second_annotator_id:
        raise ValueError("Agreement requires two distinct annotator IDs.")

    validated_tasks = _revalidate_annotation_tasks(tasks)
    validated_responses = _revalidate_annotation_responses(responses)
    task_ids = {task.task_id for task in validated_tasks}

    for response in validated_responses:
        if response.task_id not in task_ids:
            raise ValueError(f"Unknown annotation task ID for response: {response.task_id}.")

    first_responses = {
        response.task_id: response
        for response in validated_responses
        if response.annotator_id == first_annotator_id
    }
    second_responses = {
        response.task_id: response
        for response in validated_responses
        if response.annotator_id == second_annotator_id
    }
    comparable_task_ids = sorted(set(first_responses) & set(second_responses))

    if not comparable_task_ids:
        raise ValueError("No comparable annotation tasks exist for the selected annotators.")

    disagreement_task_ids = [
        task_id
        for task_id in comparable_task_ids
        if first_responses[task_id].decision != second_responses[task_id].decision
    ]
    exact_match_count = len(comparable_task_ids) - len(disagreement_task_ids)

    return MultimodalAnnotationAgreementSummary(
        annotator_ids=(first_annotator_id, second_annotator_id),
        comparable_task_count=len(comparable_task_ids),
        exact_match_count=exact_match_count,
        exact_match_rate=exact_match_count / len(comparable_task_ids),
        disagreement_task_ids=disagreement_task_ids,
    )


def _revalidate_visual_asset_records(
    assets: Sequence[VisualAssetRecord],
) -> list[VisualAssetRecord]:
    """Revalidate assets and reject duplicate deterministic asset identifiers."""

    validated_assets: list[VisualAssetRecord] = []
    asset_ids: set[str] = set()

    for asset in assets:
        validated_asset = VisualAssetRecord.model_validate(asset.model_dump(mode="python"))

        if validated_asset.asset_id in asset_ids:
            raise ValueError(f"Duplicate visual asset ID: {validated_asset.asset_id}.")

        asset_ids.add(validated_asset.asset_id)
        validated_assets.append(validated_asset)

    return validated_assets


def _revalidate_annotation_tasks(
    tasks: Sequence[MultimodalAnnotationTask],
) -> list[MultimodalAnnotationTask]:
    """Revalidate tasks and reject duplicate task or visual-asset identities."""

    validated_tasks: list[MultimodalAnnotationTask] = []
    task_ids: set[str] = set()
    asset_ids: set[str] = set()

    for task in tasks:
        validated_task = MultimodalAnnotationTask.model_validate(task.model_dump(mode="python"))

        if validated_task.task_id in task_ids:
            raise ValueError(f"Duplicate multimodal annotation task ID: {validated_task.task_id}.")

        if validated_task.asset_id in asset_ids:
            raise ValueError(
                "Duplicate visual asset ID in multimodal annotation tasks: "
                f"{validated_task.asset_id}."
            )

        task_ids.add(validated_task.task_id)
        asset_ids.add(validated_task.asset_id)
        validated_tasks.append(validated_task)

    return validated_tasks


def _revalidate_annotation_responses(
    responses: Sequence[MultimodalAnnotationResponse],
) -> list[MultimodalAnnotationResponse]:
    """Revalidate responses and reject duplicate reviewer decisions per task."""

    validated_responses: list[MultimodalAnnotationResponse] = []
    response_keys: set[tuple[str, str]] = set()

    for response in responses:
        validated_response = MultimodalAnnotationResponse.model_validate(
            response.model_dump(mode="python")
        )
        response_key = (
            validated_response.task_id,
            validated_response.annotator_id,
        )

        if response_key in response_keys:
            raise ValueError(
                "Duplicate multimodal annotation response for task and annotator: "
                f"{validated_response.task_id}, {validated_response.annotator_id}."
            )

        response_keys.add(response_key)
        validated_responses.append(validated_response)

    return validated_responses


def _write_jsonl(
    path: Path,
    rows: Sequence[dict[str, object]],
) -> None:
    """Write JSON-compatible mappings as deterministic JSON Lines."""

    content = "\n".join(
        json.dumps(
            row,
            sort_keys=True,
        )
        for row in rows
    )

    if content:
        content += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
