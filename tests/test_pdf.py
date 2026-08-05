from pathlib import Path

from pypdf import PdfWriter

from aeroragx.ingestion.acquisition import (
    DownloadReceipt,
    sha256_file,
)
from aeroragx.processing.pdf import (
    extract_pdf_pages,
    normalize_page_text,
    process_downloaded_pdfs,
    write_extraction_receipts,
    write_page_records,
)


def create_blank_pdf(
    path: Path,
    page_count: int = 2,
) -> None:
    """Create a simple test PDF."""

    writer = PdfWriter()

    for _ in range(page_count):
        writer.add_blank_page(
            width=612,
            height=792,
        )

    with path.open("wb") as output_stream:
        writer.write(output_stream)


def create_receipt(
    pdf_path: Path,
    checksum: str | None = None,
) -> DownloadReceipt:
    """Create an acquisition receipt for a test PDF."""

    return DownloadReceipt(
        document_id=123,
        source_url="https://example.com/123.pdf",
        local_path=str(pdf_path),
        sha256=checksum or sha256_file(pdf_path),
        size_bytes=pdf_path.stat().st_size,
        status="downloaded",
    )


def test_normalize_page_text() -> None:
    text = "First   line\r\n\r\nSecond\tline\x00"

    assert normalize_page_text(text) == ("First line\n\nSecond line")


def test_extract_pdf_pages_preserves_page_numbers(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "123.pdf"
    create_blank_pdf(pdf_path, page_count=2)

    pages = extract_pdf_pages(create_receipt(pdf_path))

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert pages[0].page_id == "123:page:1"
    assert pages[0].extraction_status == "empty"


def test_processing_rejects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "123.pdf"
    create_blank_pdf(pdf_path)

    pages, receipts = process_downloaded_pdfs(
        [
            create_receipt(
                pdf_path,
                checksum="incorrect-checksum",
            )
        ]
    )

    assert pages == []
    assert receipts[0].status == "failed"
    assert receipts[0].error is not None
    assert "Checksum mismatch" in receipts[0].error


def test_write_processing_outputs(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "123.pdf"
    create_blank_pdf(pdf_path)

    pages, receipts = process_downloaded_pdfs([create_receipt(pdf_path)])

    pages_path = tmp_path / "pages.jsonl"
    receipts_path = tmp_path / "receipts.jsonl"

    write_page_records(pages_path, pages)
    write_extraction_receipts(
        receipts_path,
        receipts,
    )

    assert pages_path.exists()
    assert receipts_path.exists()
    assert '"page_number": 1' in pages_path.read_text(encoding="utf-8")
    assert '"status": "processed"' in (receipts_path.read_text(encoding="utf-8"))
