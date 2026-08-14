"""Tests for deterministic multimodal page-render manifests."""

import json
from pathlib import Path
from typing import Literal

import pytest
from pypdf import PdfWriter

from aeroragx.ingestion.acquisition import sha256_file
from aeroragx.processing.multimodal_page_rendering import PageRenderRecord
from aeroragx.processing.multimodal_provenance import (
    VisualAssetRecord,
    build_visual_asset_id,
    write_visual_asset_records,
)
from aeroragx.processing.multimodal_render_manifest import (
    load_page_render_records,
    render_visual_asset_manifest,
    write_page_render_records,
)


def write_test_pdf(
    path: Path,
    page_count: int = 2,
) -> None:
    """Create a small PDF with deterministic page dimensions."""

    writer = PdfWriter()

    for _ in range(page_count):
        writer.add_blank_page(
            width=72,
            height=144,
        )

    with path.open("wb") as output_file:
        writer.write(output_file)


def make_asset(
    source_path: Path,
    page_number: int = 1,
    asset_type: Literal["figure", "table"] = "figure",
    asset_index: int = 0,
    document_sha256: str | None = None,
) -> VisualAssetRecord:
    """Create a validated visual-asset record for a local test PDF."""

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
        caption_text=None,
        source_path=str(source_path),
        source_url="https://example.com/123.pdf",
        citation_url="https://ntrs.nasa.gov/citations/123",
        document_sha256=document_sha256 or sha256_file(source_path),
    )


def make_page_render_record(
    page_number: int,
    png_path: str | None = None,
) -> PageRenderRecord:
    """Create a valid deterministic render record without writing a PNG."""

    document_id = 123

    return PageRenderRecord(
        page_id=f"{document_id}:page:{page_number}",
        document_id=document_id,
        page_number=page_number,
        source_path="data/raw/123.pdf",
        source_url="https://example.com/123.pdf",
        citation_url="https://ntrs.nasa.gov/citations/123",
        document_sha256="source-checksum",
        png_path=png_path or f"data/derived/123/page_{page_number:04d}.png",
        png_sha256=f"png-checksum-{page_number}",
        width_pixels=144,
        height_pixels=288,
        dpi=144,
        renderer_name="pypdfium2",
        renderer_version="5.13.0",
    )


def test_write_and_load_page_render_records_are_deterministic(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    records = [
        make_page_render_record(2),
        make_page_render_record(1),
    ]

    write_page_render_records(first_path, records)
    write_page_render_records(second_path, list(reversed(records)))

    assert first_path.read_text(encoding="utf-8") == second_path.read_text(encoding="utf-8")
    assert [
        json.loads(line)["page_number"]
        for line in first_path.read_text(encoding="utf-8").splitlines()
    ] == [1, 2]
    assert load_page_render_records(first_path) == [
        make_page_render_record(1),
        make_page_render_record(2),
    ]


def test_load_page_render_records_reports_the_invalid_line_number(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "invalid.jsonl"
    manifest_path.write_text('{"page_id":"not-a-valid-page-id"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid page-render record on line 1"):
        load_page_render_records(manifest_path)


def test_write_revalidates_page_render_identity_before_creating_output(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.jsonl"
    invalid_record = make_page_render_record(1).model_copy(
        update={"page_id": "not-a-deterministic-page-id"}
    )

    with pytest.raises(ValueError, match="page_id must equal"):
        write_page_render_records(manifest_path, [invalid_record])

    assert not manifest_path.exists()


def test_write_rejects_duplicate_png_paths(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.jsonl"
    first_record = make_page_render_record(1)
    second_record = make_page_render_record(
        2,
        png_path=first_record.png_path,
    )

    with pytest.raises(ValueError, match="Duplicate page-render PNG path"):
        write_page_render_records(
            manifest_path,
            [first_record, second_record],
        )

    assert not manifest_path.exists()


def test_render_visual_asset_manifest_renders_unique_pages_and_persists_jsonl(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    assets_input_path = tmp_path / "assets.jsonl"
    output_directory = tmp_path / "renders"
    manifest_output_path = output_directory / "page_renders.jsonl"
    write_test_pdf(source_path, page_count=2)
    write_visual_asset_records(
        assets_input_path,
        [
            make_asset(source_path, page_number=2),
            make_asset(source_path, page_number=1),
            make_asset(
                source_path,
                page_number=1,
                asset_index=1,
            ),
        ],
    )

    records = render_visual_asset_manifest(
        assets_input_path=assets_input_path,
        output_directory=output_directory,
        manifest_output_path=manifest_output_path,
        dpi=144,
    )

    assert [record.page_number for record in records] == [1, 2]
    assert manifest_output_path.is_file()
    assert load_page_render_records(manifest_output_path) == records
    assert [Path(record.png_path).is_file() for record in records] == [True, True]


def test_render_visual_asset_manifest_does_not_write_a_manifest_after_checksum_error(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    assets_input_path = tmp_path / "assets.jsonl"
    output_directory = tmp_path / "renders"
    manifest_output_path = output_directory / "page_renders.jsonl"
    write_test_pdf(source_path)
    write_visual_asset_records(
        assets_input_path,
        [
            make_asset(
                source_path,
                document_sha256="not-the-source-checksum",
            )
        ],
    )

    with pytest.raises(ValueError, match="Checksum mismatch"):
        render_visual_asset_manifest(
            assets_input_path=assets_input_path,
            output_directory=output_directory,
            manifest_output_path=manifest_output_path,
        )

    assert not output_directory.exists()
