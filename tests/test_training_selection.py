"""Tests for deterministic LoRA source-document selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from aeroragx.training.selection import (
    LoRASourceSelectionManifest,
    SourceDocumentMetadata,
    SourceSelectionConfig,
    load_source_selection_manifest,
    normalize_source_title,
    select_source_documents,
    write_source_selection_manifest,
)


def make_candidates() -> list[SourceDocumentMetadata]:
    """Build a compact candidate pool for selection tests."""

    return [
        SourceDocumentMetadata(
            document_id=1001,
            title="Thermal System Study",
            chunk_count=10,
            source_queries=["thermal"],
            sti_type=("TECHNICAL_PUBLICATION"),
            subject_categories=["Thermal"],
        ),
        SourceDocumentMetadata(
            document_id=1002,
            title="Thermal System Study",
            chunk_count=4,
            source_queries=["thermal"],
            sti_type="PRESENTATION",
            subject_categories=["Thermal"],
        ),
        SourceDocumentMetadata(
            document_id=1003,
            title="Fuel Cell Aircraft",
            chunk_count=8,
            source_queries=["fuel"],
            sti_type=("TECHNICAL_PUBLICATION"),
            subject_categories=["Propulsion"],
        ),
        SourceDocumentMetadata(
            document_id=1004,
            title="Electric Controls",
            chunk_count=7,
            source_queries=["controls"],
            sti_type=("CONFERENCE_PAPER"),
            subject_categories=["Controls"],
        ),
        SourceDocumentMetadata(
            document_id=1005,
            title="Materials Note",
            chunk_count=2,
            source_queries=["materials"],
            sti_type=("TECHNICAL_MEMORANDUM"),
            subject_categories=["Materials"],
        ),
    ]


def make_config(
    *,
    protected_count: int = 0,
) -> SourceSelectionConfig:
    """Build deterministic test configuration."""

    return SourceSelectionConfig(
        version="0.1",
        corpus_version="test",
        target_document_count=3,
        minimum_chunks_per_document=3,
        expected_corpus_document_count=(5 + protected_count),
        expected_protected_document_count=(protected_count),
        expected_candidate_document_count=5,
        expected_candidate_chunk_count=31,
        deduplicate_exact_titles=True,
        source_query_minimums={
            "thermal": 1,
            "fuel": 1,
            "controls": 1,
        },
        type_priority=[
            "TECHNICAL_PUBLICATION",
            "TECHNICAL_MEMORANDUM",
            "CONFERENCE_PAPER",
            "PRESENTATION",
        ],
    )


def select_fixture(
    candidates: list[SourceDocumentMetadata] | None = None,
) -> LoRASourceSelectionManifest:
    """Run the common fixture selection."""

    resolved = candidates if candidates is not None else make_candidates()

    return select_source_documents(
        resolved,
        protected_document_ids=set(),
        config=make_config(),
        corpus_document_count=5,
        protected_document_count=0,
        candidate_chunk_count=31,
        corpus_chunks_path=("chunks.jsonl"),
        metadata_manifest_path=("metadata.jsonl"),
        protected_manifest_path=("protected.json"),
        protected_manifest_sha256=("a" * 64),
        selection_config_path=("selection.yaml"),
        selection_config_sha256=("b" * 64),
    )


def test_selection_is_deterministic() -> None:
    first = select_fixture()

    second = select_fixture(list(reversed(make_candidates())))

    assert first == second

    assert first.selected_document_ids == [
        1001,
        1003,
        1004,
    ]


def test_exact_title_duplicate_prefers_richer_document() -> None:
    manifest = select_fixture()

    decisions = {document.document_id: document for document in manifest.documents}

    assert decisions[1001].status == "selected"

    assert decisions[1002].status == "duplicate_excluded"

    assert decisions[1002].representative_document_id == 1001

    assert decisions[1001].duplicate_family_id == decisions[1002].duplicate_family_id


def test_document_below_minimum_is_not_selected() -> None:
    manifest = select_fixture()

    decision = next(document for document in manifest.documents if document.document_id == 1005)

    assert decision.status == "not_selected"

    assert "minimum_chunks_per_document" in decision.reason


def test_protected_candidate_is_rejected() -> None:
    candidates = make_candidates()

    with pytest.raises(
        ValueError,
        match=("Protected documents appeared"),
    ):
        select_source_documents(
            candidates,
            protected_document_ids={1001},
            config=(make_config(protected_count=1)),
            corpus_document_count=6,
            protected_document_count=1,
            candidate_chunk_count=31,
            corpus_chunks_path=("chunks.jsonl"),
            metadata_manifest_path=("metadata.jsonl"),
            protected_manifest_path=("protected.json"),
            protected_manifest_sha256=("a" * 64),
            selection_config_path=("selection.yaml"),
            selection_config_sha256=("b" * 64),
        )


def test_source_query_minimum_is_enforced() -> None:
    config = make_config().model_copy(
        update={
            "source_query_minimums": {
                "missing-topic": 1,
            }
        }
    )

    with pytest.raises(
        ValueError,
        match=("Unable to satisfy source-query coverage"),
    ):
        select_source_documents(
            make_candidates(),
            protected_document_ids=set(),
            config=config,
            corpus_document_count=5,
            protected_document_count=0,
            candidate_chunk_count=31,
            corpus_chunks_path=("chunks.jsonl"),
            metadata_manifest_path=("metadata.jsonl"),
            protected_manifest_path=("protected.json"),
            protected_manifest_sha256=("a" * 64),
            selection_config_path=("selection.yaml"),
            selection_config_sha256=("b" * 64),
        )


def test_manifest_counts_are_consistent() -> None:
    manifest = select_fixture()

    assert manifest.candidate_document_count == 5

    assert manifest.candidate_chunk_count == 31

    assert manifest.deduplicated_candidate_count == 4

    assert manifest.selected_document_count == 3

    assert manifest.selected_chunk_count == 25

    assert manifest.duplicate_excluded_document_count == 1

    assert manifest.not_selected_document_count == 1

    assert manifest.protected_overlap_count == 0


def test_manifest_round_trip(
    tmp_path: Path,
) -> None:
    manifest = select_fixture()

    output = tmp_path / "selection.json"

    write_source_selection_manifest(
        output,
        manifest,
    )

    loaded = load_source_selection_manifest(output)

    assert loaded == manifest


def test_manifest_writer_is_deterministic(
    tmp_path: Path,
) -> None:
    manifest = select_fixture()

    first = tmp_path / "first.json"

    second = tmp_path / "second.json"

    write_source_selection_manifest(
        first,
        manifest,
    )

    write_source_selection_manifest(
        second,
        manifest,
    )

    assert first.read_bytes() == second.read_bytes()


def test_title_normalization_removes_markup_and_spacing() -> None:
    first = normalize_source_title("Advanced 30,000 lb<sub>f</sub> Test")

    second = normalize_source_title(" advanced 30,000 lbf test ")

    assert first == second
