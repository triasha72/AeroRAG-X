"""Tests for page-linked multimodal provenance."""

import json
from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from aeroragx.processing.multimodal_provenance import (
    VisualAssetRecord,
    build_visual_asset_id,
    load_visual_asset_records,
    validate_visual_asset_provenance,
    write_visual_asset_records,
)
from aeroragx.processing.pdf import PDFPageRecord


def make_page(
    page_number: int = 1,
) -> PDFPageRecord:
    """Create one deterministic PDF page."""

    return PDFPageRecord(
        page_id=f"123:page:{page_number}",
        document_id=123,
        page_number=page_number,
        text="Page text.",
        character_count=10,
        extraction_status="ok",
        source_path="data/raw/123.pdf",
        source_url="https://example.com/123.pdf",
        citation_url="https://ntrs.nasa.gov/citations/123",
        document_sha256="test-checksum",
    )


def make_asset(
    page_number: int = 1,
    asset_type: Literal["figure", "table"] = "figure",
    asset_index: int = 0,
) -> VisualAssetRecord:
    """Create one deterministic visual-asset record."""

    page_id = f"123:page:{page_number}"

    return VisualAssetRecord(
        asset_id=build_visual_asset_id(
            page_id,
            asset_type,
            asset_index,
        ),
        document_id=123,
        page_id=page_id,
        page_number=page_number,
        asset_type=asset_type,
        asset_index=asset_index,
        caption_text=None,
        source_path="data/raw/123.pdf",
        source_url="https://example.com/123.pdf",
        citation_url="https://ntrs.nasa.gov/citations/123",
        document_sha256="test-checksum",
    )


def test_visual_asset_record_preserves_page_linked_provenance() -> None:
    asset = make_asset()

    assert asset.asset_id == "123:page:1:figure:000"
    assert asset.page_id == "123:page:1"
    assert asset.caption_text is None
    assert asset.document_sha256 == "test-checksum"


def test_visual_asset_record_rejects_mismatched_page_id() -> None:
    payload = make_asset().model_dump()
    payload["page_id"] = "123:page:2"

    with pytest.raises(ValidationError, match="page_id must equal"):
        VisualAssetRecord.model_validate(payload)


def test_visual_asset_record_rejects_nondeterministic_asset_id() -> None:
    payload = make_asset().model_dump()
    payload["asset_id"] = "unrelated-id"

    with pytest.raises(ValidationError, match="asset_id must equal"):
        VisualAssetRecord.model_validate(payload)


def test_validation_accepts_asset_linked_to_empty_text_page() -> None:
    empty_page = make_page().model_copy(
        update={
            "text": "",
            "character_count": 0,
            "extraction_status": "empty",
        }
    )

    validate_visual_asset_provenance(
        [make_asset()],
        [empty_page],
    )


def test_validation_rejects_unknown_page() -> None:
    with pytest.raises(ValueError, match="Unknown page ID"):
        validate_visual_asset_provenance(
            [make_asset(page_number=2)],
            [make_page()],
        )


def test_validation_rejects_mismatched_provenance() -> None:
    mismatched_asset = make_asset().model_copy(update={"document_sha256": "different-checksum"})

    with pytest.raises(ValueError, match="document_sha256"):
        validate_visual_asset_provenance(
            [mismatched_asset],
            [make_page()],
        )


def test_validation_rejects_duplicate_asset_ids() -> None:
    asset = make_asset()

    with pytest.raises(ValueError, match="Duplicate visual asset ID"):
        validate_visual_asset_provenance(
            [asset, asset],
            [make_page()],
        )


def test_jsonl_round_trip_is_deterministic(
    tmp_path: Path,
) -> None:
    first_asset = make_asset(page_number=1)
    second_asset = make_asset(
        page_number=2,
        asset_type="table",
        asset_index=1,
    )
    output_path = tmp_path / "visual_assets.jsonl"

    write_visual_asset_records(
        output_path,
        [second_asset, first_asset],
    )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    assert [row["asset_id"] for row in rows] == [
        first_asset.asset_id,
        second_asset.asset_id,
    ]

    loaded_assets = load_visual_asset_records(output_path)

    assert [asset.model_dump() for asset in loaded_assets] == [
        first_asset.model_dump(),
        second_asset.model_dump(),
    ]
