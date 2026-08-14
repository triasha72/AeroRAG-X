"""Tests for page rendering linked to multimodal provenance records."""

from importlib.metadata import version
from pathlib import Path
from typing import Literal

import pytest
from PIL import Image
from pydantic import ValidationError
from pypdf import PdfWriter

from aeroragx.ingestion.acquisition import sha256_file
from aeroragx.processing.multimodal_page_rendering import (
    PageRenderRecord,
    build_page_render_path,
    render_visual_asset_pages,
)
from aeroragx.processing.multimodal_provenance import (
    VisualAssetRecord,
    build_visual_asset_id,
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


def test_build_page_render_path_is_deterministic(
    tmp_path: Path,
) -> None:
    output_path = build_page_render_path(
        tmp_path / "renders",
        document_id=123,
        page_number=7,
    )

    assert output_path == tmp_path / "renders" / "123" / "page_0007.png"


def test_render_emits_one_png_per_referenced_page(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    output_directory = tmp_path / "renders"
    write_test_pdf(source_path)

    records = render_visual_asset_pages(
        [
            make_asset(
                source_path,
                page_number=2,
            ),
            make_asset(
                source_path,
                page_number=1,
            ),
            make_asset(
                source_path,
                page_number=1,
                asset_index=1,
            ),
        ],
        output_directory=output_directory,
        dpi=144,
    )

    assert [record.page_number for record in records] == [1, 2]
    assert [record.png_path for record in records] == [
        str(output_directory / "123" / "page_0001.png"),
        str(output_directory / "123" / "page_0002.png"),
    ]

    first_record = records[0]

    assert first_record.page_id == "123:page:1"
    assert first_record.document_sha256 == sha256_file(source_path)
    assert first_record.png_sha256 == sha256_file(Path(first_record.png_path))
    assert first_record.width_pixels == 144
    assert first_record.height_pixels == 288
    assert first_record.dpi == 144
    assert first_record.renderer_name == "pypdfium2"
    assert first_record.renderer_version == version("pypdfium2")

    with Image.open(first_record.png_path) as rendered_image:
        assert rendered_image.size == (144, 288)


def test_render_rejects_checksum_mismatch_before_creating_output(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    output_directory = tmp_path / "renders"
    write_test_pdf(source_path)
    asset = make_asset(
        source_path,
        document_sha256="not-the-source-checksum",
    )

    with pytest.raises(ValueError, match="Checksum mismatch"):
        render_visual_asset_pages(
            [asset],
            output_directory=output_directory,
        )

    assert not output_directory.exists()


def test_render_rejects_page_outside_source_pdf(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    output_directory = tmp_path / "renders"
    write_test_pdf(
        source_path,
        page_count=1,
    )
    asset = make_asset(
        source_path,
        page_number=2,
    )

    with pytest.raises(ValueError, match="has no page 2"):
        render_visual_asset_pages(
            [asset],
            output_directory=output_directory,
        )

    assert not output_directory.exists()


def test_render_revalidates_the_visual_asset_identity(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    write_test_pdf(source_path)
    invalid_asset = make_asset(source_path).model_copy(
        update={"asset_id": "not-a-deterministic-asset-id"},
    )

    with pytest.raises(ValidationError, match="asset_id must equal"):
        render_visual_asset_pages(
            [invalid_asset],
            output_directory=tmp_path / "renders",
        )


def test_render_rejects_nonpositive_dpi(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    write_test_pdf(source_path)

    with pytest.raises(ValueError, match="DPI must be at least 1"):
        render_visual_asset_pages(
            [make_asset(source_path)],
            output_directory=tmp_path / "renders",
            dpi=0,
        )


def test_page_render_record_rejects_non_png_output_path() -> None:
    payload = {
        "page_id": "123:page:1",
        "document_id": 123,
        "page_number": 1,
        "source_path": "data/raw/123.pdf",
        "source_url": "https://example.com/123.pdf",
        "citation_url": "https://ntrs.nasa.gov/citations/123",
        "document_sha256": "document-checksum",
        "png_path": "data/derived/page_0001.jpg",
        "png_sha256": "png-checksum",
        "width_pixels": 10,
        "height_pixels": 20,
        "dpi": 144,
        "renderer_name": "pypdfium2",
        "renderer_version": "5.7.0",
    }

    with pytest.raises(ValidationError, match="png_path must point to a PNG file"):
        PageRenderRecord.model_validate(payload)
