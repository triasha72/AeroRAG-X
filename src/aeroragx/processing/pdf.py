"""Page-preserving extraction from downloaded NASA PDFs."""

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from aeroragx.ingestion.acquisition import (
    DownloadReceipt,
    sha256_file,
)


class PDFPageRecord(BaseModel):
    """Text and provenance for one PDF page."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    page_id: str
    document_id: int
    page_number: int = Field(ge=1)
    text: str
    character_count: int = Field(ge=0)
    extraction_status: Literal["ok", "empty"]
    source_path: str
    source_url: str
    citation_url: str
    document_sha256: str


class PDFExtractionReceipt(BaseModel):
    """Result of processing one downloaded PDF."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int
    source_path: str
    document_sha256: str
    page_count: int = Field(ge=0)
    nonempty_page_count: int = Field(ge=0)
    status: Literal["processed", "failed"]
    error: str | None = None


def normalize_page_text(text: str) -> str:
    """Clean extracted text while preserving paragraph boundaries."""

    normalized = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines: list[str] = []
    previous_line_was_blank = False

    for raw_line in normalized.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()

        if line:
            cleaned_lines.append(line)
            previous_line_was_blank = False
            continue

        if cleaned_lines and not previous_line_was_blank:
            cleaned_lines.append("")
            previous_line_was_blank = True

    return "\n".join(cleaned_lines).strip()


def load_download_receipts(
    path: Path,
) -> list[DownloadReceipt]:
    """Load document acquisition receipts from JSON Lines."""

    receipts: list[DownloadReceipt] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            receipt = DownloadReceipt.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid download receipt row {line_number}: {exc}") from exc

        receipts.append(receipt)

    return receipts


def extract_pdf_pages(
    receipt: DownloadReceipt,
) -> list[PDFPageRecord]:
    """Extract page text from one verified local PDF."""

    if receipt.local_path is None:
        raise ValueError(f"Document {receipt.document_id} has no local path.")

    if receipt.sha256 is None:
        raise ValueError(f"Document {receipt.document_id} has no checksum.")

    source_path = Path(receipt.local_path)

    if not source_path.exists():
        raise ValueError(f"PDF does not exist: {source_path}")

    actual_checksum = sha256_file(source_path)

    if actual_checksum != receipt.sha256:
        raise ValueError(f"Checksum mismatch for document {receipt.document_id}.")

    try:
        reader = PdfReader(
            str(source_path),
            strict=False,
        )
    except (OSError, PdfReadError) as exc:
        raise ValueError(f"Could not read PDF {source_path}: {exc}") from exc

    page_records: list[PDFPageRecord] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            raw_text = page.extract_text() or ""
        except Exception as exc:
            raise ValueError(
                f"Could not extract page {page_number} from document {receipt.document_id}: {exc}"
            ) from exc

        text = normalize_page_text(raw_text)
        extraction_status: Literal["ok", "empty"]

        if text:
            extraction_status = "ok"
        else:
            extraction_status = "empty"

        page_records.append(
            PDFPageRecord(
                page_id=(f"{receipt.document_id}:page:{page_number}"),
                document_id=receipt.document_id,
                page_number=page_number,
                text=text,
                character_count=len(text),
                extraction_status=extraction_status,
                source_path=str(source_path),
                source_url=receipt.source_url,
                citation_url=(f"https://ntrs.nasa.gov/citations/{receipt.document_id}"),
                document_sha256=receipt.sha256,
            )
        )

    return page_records


def process_downloaded_pdfs(
    receipts: list[DownloadReceipt],
    limit: int | None = None,
    max_size_bytes: int | None = None,
) -> tuple[
    list[PDFPageRecord],
    list[PDFExtractionReceipt],
]:
    """Extract pages from eligible acquisition receipts."""

    if limit is not None and limit < 1:
        raise ValueError("Limit must be at least 1.")

    candidates = [
        receipt
        for receipt in receipts
        if receipt.status in {"downloaded", "skipped"}
        and receipt.local_path is not None
        and receipt.sha256 is not None
    ]

    if max_size_bytes is not None:
        candidates = [
            receipt
            for receipt in candidates
            if receipt.size_bytes is None or receipt.size_bytes <= max_size_bytes
        ]

    if limit is not None:
        candidates = candidates[:limit]

    all_pages: list[PDFPageRecord] = []
    extraction_receipts: list[PDFExtractionReceipt] = []

    for receipt in candidates:
        source_path = receipt.local_path
        document_sha256 = receipt.sha256

        if source_path is None or document_sha256 is None:
            continue

        try:
            pages = extract_pdf_pages(receipt)
        except ValueError as exc:
            extraction_receipts.append(
                PDFExtractionReceipt(
                    document_id=receipt.document_id,
                    source_path=source_path,
                    document_sha256=document_sha256,
                    page_count=0,
                    nonempty_page_count=0,
                    status="failed",
                    error=str(exc),
                )
            )
            continue

        all_pages.extend(pages)

        extraction_receipts.append(
            PDFExtractionReceipt(
                document_id=receipt.document_id,
                source_path=source_path,
                document_sha256=document_sha256,
                page_count=len(pages),
                nonempty_page_count=sum(page.extraction_status == "ok" for page in pages),
                status="processed",
            )
        )

    return all_pages, extraction_receipts


def write_page_records(
    path: Path,
    pages: list[PDFPageRecord],
) -> None:
    """Write page records as JSON Lines."""

    _write_jsonl(path, pages)


def write_extraction_receipts(
    path: Path,
    receipts: list[PDFExtractionReceipt],
) -> None:
    """Write PDF extraction receipts as JSON Lines."""

    _write_jsonl(path, receipts)


def _write_jsonl(
    path: Path,
    records: Sequence[BaseModel],
) -> None:
    """Write Pydantic records to a JSONL file."""

    path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
        )
        for record in records
    ]

    content = "\n".join(rows)

    if content:
        content += "\n"

    path.write_text(content, encoding="utf-8")
