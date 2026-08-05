from pathlib import Path

import httpx

from aeroragx.ingestion.acquisition import (
    download_documents,
    is_pdf,
    load_manifest,
    sha256_file,
    write_download_receipts,
)
from aeroragx.ingestion.corpus import ManifestEntry


def make_entry(
    document_id: int = 123,
    pdf_url: str | None = "https://example.com/report.pdf",
) -> ManifestEntry:
    """Create a test manifest entry."""

    return ManifestEntry(
        document_id=document_id,
        title="Example NASA Report",
        citation_url=(f"https://ntrs.nasa.gov/citations/{document_id}"),
        pdf_url=pdf_url,
        source_queries=["electric aircraft"],
    )


def test_load_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.jsonl"

    manifest_path.write_text(
        make_entry().model_dump_json() + "\n",
        encoding="utf-8",
    )

    entries = load_manifest(manifest_path)

    assert len(entries) == 1
    assert entries[0].document_id == 123


def test_download_documents_creates_pdf(
    tmp_path: Path,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"%PDF-1.7\nTest PDF",
            headers={"Content-Type": "application/pdf"},
        )

    receipts = download_documents(
        entries=[make_entry()],
        output_dir=tmp_path / "pdfs",
        limit=1,
        transport=httpx.MockTransport(handler),
    )

    target_path = tmp_path / "pdfs" / "123.pdf"

    assert target_path.exists()
    assert is_pdf(target_path)
    assert receipts[0].status == "downloaded"
    assert receipts[0].sha256 == sha256_file(target_path)


def test_download_documents_skips_existing_file(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "pdfs"
    output_dir.mkdir()

    target_path = output_dir / "123.pdf"
    target_path.write_bytes(b"%PDF-1.7\nExisting PDF")

    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP request should not occur for existing file.")

    receipts = download_documents(
        entries=[make_entry()],
        output_dir=output_dir,
        transport=httpx.MockTransport(handler),
    )

    assert receipts[0].status == "skipped"
    assert receipts[0].sha256 == sha256_file(target_path)


def test_download_documents_rejects_invalid_pdf(
    tmp_path: Path,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html>Not a PDF</html>",
        )

    receipts = download_documents(
        entries=[make_entry()],
        output_dir=tmp_path / "pdfs",
        transport=httpx.MockTransport(handler),
    )

    assert receipts[0].status == "failed"
    assert receipts[0].error is not None
    assert not (tmp_path / "pdfs" / "123.pdf").exists()


def test_write_download_receipts(
    tmp_path: Path,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"%PDF-1.7\nTest PDF",
        )

    receipts = download_documents(
        entries=[make_entry()],
        output_dir=tmp_path / "pdfs",
        transport=httpx.MockTransport(handler),
    )

    receipts_path = tmp_path / "receipts.jsonl"

    write_download_receipts(
        path=receipts_path,
        receipts=receipts,
    )

    assert receipts_path.exists()
    assert '"status": "downloaded"' in receipts_path.read_text(encoding="utf-8")
