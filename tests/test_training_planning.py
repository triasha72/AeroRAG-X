"""Tests for deterministic LoRA evidence planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from aeroragx.processing.chunking import (
    ChunkRecord,
)
from aeroragx.training.planning import (
    ExamplePlanConfig,
    build_example_plan,
    load_example_plan_manifest,
    write_example_plan_manifest,
)
from aeroragx.training.selection import (
    LoRASourceSelectionManifest,
    SourceDocumentSelection,
)


def make_chunk(
    *,
    document_id: int,
    chunk_index: int,
    word_count: int = 120,
    text_prefix: str = "Technical evidence",
) -> ChunkRecord:
    """Build one deterministic chunk fixture."""

    filler_count = max(
        word_count - len(text_prefix.split()) - 1,
        1,
    )

    words = [
        text_prefix,
        *[f"word{index}" for index in range(filler_count)],
        "end",
    ]

    text = " ".join(words)

    return ChunkRecord(
        chunk_id=(f"{document_id}:chunk:{chunk_index:05d}"),
        document_id=document_id,
        chunk_index=chunk_index,
        page_start=1,
        page_end=1,
        page_ids=[f"{document_id}:page:00001"],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=len(text.split()),
        citation_url=(f"https://example.test/citation/{document_id}"),
        source_url=(f"https://example.test/source/{document_id}"),
        document_sha256=(f"{document_id:064d}"),
    )


def make_chunks() -> list[ChunkRecord]:
    """Build four documents with six chunks each."""

    return [
        make_chunk(
            document_id=document_id,
            chunk_index=chunk_index,
        )
        for document_id in [
            1001,
            1002,
            1003,
            1004,
        ]
        for chunk_index in range(6)
    ]


def make_source_selection() -> LoRASourceSelectionManifest:
    """Build a compact frozen source-selection fixture."""

    documents = [
        SourceDocumentSelection(
            document_id=document_id,
            title=(f"Document {document_id}"),
            chunk_count=6,
            source_queries=["topic"],
            sti_type=("TECHNICAL_PUBLICATION"),
            subject_categories=["Engineering"],
            status="selected",
            reason=("selected for test"),
        )
        for document_id in [
            1001,
            1002,
            1003,
            1004,
        ]
    ]

    return LoRASourceSelectionManifest(
        version="0.1",
        corpus_version="test",
        corpus_chunks_path=("chunks.jsonl"),
        metadata_manifest_path=("metadata.jsonl"),
        protected_manifest_path=("protected.json"),
        protected_manifest_sha256=("a" * 64),
        selection_config_path=("selection.yaml"),
        selection_config_sha256=("b" * 64),
        corpus_document_count=4,
        protected_document_count=0,
        candidate_document_count=4,
        candidate_chunk_count=24,
        deduplicated_candidate_count=4,
        selected_document_count=4,
        selected_chunk_count=24,
        duplicate_excluded_document_count=0,
        not_selected_document_count=0,
        protected_overlap_count=0,
        selected_document_ids=[
            1001,
            1002,
            1003,
            1004,
        ],
        source_query_selected_counts={
            "topic": 4,
        },
        documents=documents,
    )


def make_config() -> ExamplePlanConfig:
    """Build a reduced planning configuration for tests."""

    return ExamplePlanConfig(
        version="0.1",
        expected_selected_document_count=4,
        expected_selected_chunk_count=24,
        ordinary_examples_per_document=2,
        extra_ordinary_document_count=1,
        synthesis_document_count=2,
        refusal_document_count=3,
        expected_ordinary_example_count=9,
        expected_synthesis_example_count=2,
        expected_refusal_example_count=3,
        expected_total_example_count=14,
        ordinary_evidence_chunks=2,
        synthesis_evidence_chunks=3,
        refusal_evidence_chunks=2,
        minimum_chunk_words=80,
        reference_section_prefixes=[
            "references",
            "bibliography",
        ],
    )


def build_fixture(
    *,
    chunks: list[ChunkRecord] | None = None,
):
    """Build the common example-plan fixture."""

    return build_example_plan(
        (chunks if chunks is not None else make_chunks()),
        source_selection=(make_source_selection()),
        protected_document_ids=set(),
        config=make_config(),
        corpus_chunks_path=("chunks.jsonl"),
        corpus_chunks_sha256=("c" * 64),
        source_selection_manifest_path=("selection.json"),
        source_selection_manifest_sha256=("d" * 64),
        protected_manifest_path=("protected.json"),
        protected_manifest_sha256=("e" * 64),
        plan_config_path=("plan.yaml"),
        plan_config_sha256=("f" * 64),
    )


def test_plan_counts_are_correct() -> None:
    manifest = build_fixture()

    assert manifest.selected_document_count == 4

    assert manifest.planned_example_count == 14

    assert manifest.ordinary_example_count == 9

    assert manifest.synthesis_example_count == 2

    assert manifest.refusal_example_count == 3

    assert manifest.protected_overlap_count == 0


def test_plan_is_deterministic() -> None:
    first = build_fixture()

    second = build_fixture(chunks=list(reversed(make_chunks())))

    assert first == second


def test_plan_ids_are_sequential() -> None:
    manifest = build_fixture()

    assert [example.plan_id for example in manifest.examples] == [
        f"plan_{index:04d}"
        for index in range(
            1,
            15,
        )
    ]


def test_all_selected_documents_are_represented() -> None:
    manifest = build_fixture()

    observed = {example.document_id for example in manifest.examples}

    assert observed == {
        1001,
        1002,
        1003,
        1004,
    }


def test_evidence_bundle_sizes_match_type() -> None:
    manifest = build_fixture()

    expected_sizes = {
        "ordinary": 2,
        "synthesis": 3,
        "refusal": 2,
    }

    for example in manifest.examples:
        assert len(example.chunk_ids) == expected_sizes[example.example_type]


def test_all_plans_use_one_document() -> None:
    chunks = {chunk.chunk_id: chunk for chunk in make_chunks()}

    manifest = build_fixture(chunks=list(chunks.values()))

    for example in manifest.examples:
        document_ids = {chunks[chunk_id].document_id for chunk_id in example.chunk_ids}

        assert document_ids == {example.document_id}


def test_protected_document_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=("Protected documents appeared"),
    ):
        build_example_plan(
            make_chunks(),
            source_selection=(make_source_selection()),
            protected_document_ids={1001},
            config=make_config(),
            corpus_chunks_path=("chunks.jsonl"),
            corpus_chunks_sha256=("c" * 64),
            source_selection_manifest_path=("selection.json"),
            source_selection_manifest_sha256=("d" * 64),
            protected_manifest_path=("protected.json"),
            protected_manifest_sha256=("e" * 64),
            plan_config_path=("plan.yaml"),
            plan_config_sha256=("f" * 64),
        )


def test_short_chunks_can_make_document_ineligible() -> None:
    chunks = make_chunks()

    modified: list[ChunkRecord] = []

    for chunk in chunks:
        if chunk.document_id == 1004 and chunk.chunk_index >= 1:
            modified.append(
                make_chunk(
                    document_id=1004,
                    chunk_index=(chunk.chunk_index),
                    word_count=20,
                )
            )

        else:
            modified.append(chunk)

    with pytest.raises(
        ValueError,
        match=("insufficient to construct"),
    ):
        build_fixture(chunks=modified)


def test_reference_section_prefix_is_filtered() -> None:
    chunks = make_chunks()

    modified: list[ChunkRecord] = []

    for chunk in chunks:
        if chunk.document_id == 1004 and chunk.chunk_index >= 1:
            modified.append(
                make_chunk(
                    document_id=1004,
                    chunk_index=(chunk.chunk_index),
                    text_prefix=("References"),
                )
            )

        else:
            modified.append(chunk)

    with pytest.raises(
        ValueError,
        match=("insufficient to construct"),
    ):
        build_fixture(chunks=modified)


def test_manifest_round_trip(
    tmp_path: Path,
) -> None:
    manifest = build_fixture()

    output = tmp_path / "example_plan.json"

    write_example_plan_manifest(
        output,
        manifest,
    )

    loaded = load_example_plan_manifest(output)

    assert loaded == manifest


def test_manifest_writer_is_deterministic(
    tmp_path: Path,
) -> None:
    manifest = build_fixture()

    first = tmp_path / "first.json"

    second = tmp_path / "second.json"

    write_example_plan_manifest(
        first,
        manifest,
    )

    write_example_plan_manifest(
        second,
        manifest,
    )

    assert first.read_bytes() == second.read_bytes()
