"""Tests for frozen protected-document manifest validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aeroragx.training.protected import (
    ProtectedDocumentManifest,
    ProtectedQueryEvidence,
    load_protected_document_manifest,
    write_protected_document_manifest,
)


def make_manifest() -> ProtectedDocumentManifest:
    """Build one internally consistent protected manifest."""

    return ProtectedDocumentManifest(
        version="0.1",
        purpose=("Protect frozen evaluation evidence."),
        source_evaluation=("data/evaluation/example.jsonl"),
        dense_backend="numpy",
        candidate_top_k=20,
        evidence_top_k=2,
        query_count=2,
        protected_document_count=3,
        protected_chunk_count=4,
        protected_document_ids=[
            1001,
            1002,
            1003,
        ],
        protected_chunk_ids=[
            "1001:chunk:00001",
            "1002:chunk:00001",
            "1002:chunk:00002",
            "1003:chunk:00001",
        ],
        queries=[
            ProtectedQueryEvidence(
                query_id="q1",
                expected_answerable=True,
                document_ids=[
                    1001,
                    1002,
                ],
                chunk_ids=[
                    "1001:chunk:00001",
                    "1002:chunk:00001",
                ],
            ),
            ProtectedQueryEvidence(
                query_id="q2",
                expected_answerable=False,
                document_ids=[
                    1002,
                    1003,
                ],
                chunk_ids=[
                    "1002:chunk:00002",
                    "1003:chunk:00001",
                ],
            ),
        ],
    )


def test_manifest_is_valid() -> None:
    manifest = make_manifest()

    assert manifest.query_count == 2

    assert manifest.protected_document_count == 3

    assert manifest.protected_chunk_count == 4

    assert manifest.protected_document_id_set == {
        1001,
        1002,
        1003,
    }


def test_manifest_round_trip(
    tmp_path: Path,
) -> None:
    path = tmp_path / "protected_documents.json"

    manifest = make_manifest()

    write_protected_document_manifest(
        path,
        manifest,
    )

    loaded = load_protected_document_manifest(path)

    assert loaded == manifest


def test_writer_is_deterministic(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.json"

    second_path = tmp_path / "second.json"

    manifest = make_manifest()

    write_protected_document_manifest(
        first_path,
        manifest,
    )

    write_protected_document_manifest(
        second_path,
        manifest,
    )

    assert first_path.read_bytes() == second_path.read_bytes()


def test_query_count_mismatch_is_rejected() -> None:
    payload = make_manifest().model_dump(mode="json")

    payload["query_count"] = 3

    with pytest.raises(
        ValidationError,
        match="query_count",
    ):
        (ProtectedDocumentManifest.model_validate(payload))


def test_duplicate_query_ids_are_rejected() -> None:
    payload = make_manifest().model_dump(mode="json")

    payload["queries"][1]["query_id"] = "q1"

    with pytest.raises(
        ValidationError,
        match=("query IDs must be unique"),
    ):
        (ProtectedDocumentManifest.model_validate(payload))


def test_unknown_query_document_is_rejected() -> None:
    payload = make_manifest().model_dump(mode="json")

    payload["queries"][0]["document_ids"].append(9999)

    with pytest.raises(
        ValidationError,
        match=("missing from the global protected set"),
    ):
        (ProtectedDocumentManifest.model_validate(payload))


def test_wrong_evidence_count_is_rejected() -> None:
    payload = make_manifest().model_dump(mode="json")

    payload["queries"][0]["chunk_ids"] = ["1001:chunk:00001"]

    with pytest.raises(
        ValidationError,
        match="expected 2",
    ):
        (ProtectedDocumentManifest.model_validate(payload))


def test_loader_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "protected_documents.json"

    path.write_text(
        "{not-json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=("Invalid protected-document JSON"),
    ):
        (load_protected_document_manifest(path))


def test_loader_rejects_invalid_manifest(
    tmp_path: Path,
) -> None:
    path = tmp_path / "protected_documents.json"

    payload = make_manifest().model_dump(mode="json")

    payload["protected_document_count"] = 99

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=("Invalid protected-document manifest"),
    ):
        (load_protected_document_manifest(path))
