import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aeroragx.processing.chunking import (
    ChunkingConfig,
    build_chunks,
    load_chunking_config,
    load_page_records,
    write_chunk_records,
    write_chunking_receipts,
)
from aeroragx.processing.pdf import PDFPageRecord


def make_page(
    page_number: int,
    text: str,
    status: str = "ok",
) -> PDFPageRecord:
    """Create a deterministic test page."""

    return PDFPageRecord(
        page_id=f"123:page:{page_number}",
        document_id=123,
        page_number=page_number,
        text=text,
        character_count=len(text),
        extraction_status=status,
        source_path="data/raw/123.pdf",
        source_url="https://example.com/123.pdf",
        citation_url=("https://ntrs.nasa.gov/citations/123"),
        document_sha256="test-checksum",
    )


def test_load_chunking_config(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "chunking.yaml"

    config_path.write_text(
        """
version: "0.1"
chunk_words: 10
overlap_words: 2
""".strip(),
        encoding="utf-8",
    )

    config = load_chunking_config(config_path)

    assert config.chunk_words == 10
    assert config.overlap_words == 2


def test_config_rejects_invalid_overlap() -> None:
    with pytest.raises(ValidationError):
        ChunkingConfig(
            chunk_words=10,
            overlap_words=10,
        )


def test_load_page_records(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pages.jsonl"
    page = make_page(1, "Example page text")

    path.write_text(
        page.model_dump_json() + "\n",
        encoding="utf-8",
    )

    pages = load_page_records(path)

    assert len(pages) == 1
    assert pages[0].page_id == "123:page:1"


def test_build_chunks_preserves_overlap() -> None:
    pages = [
        make_page(
            1,
            "one two three four five six seven eight",
        ),
        make_page(
            2,
            "nine ten eleven twelve thirteen fourteen fifteen sixteen",
        ),
    ]

    chunks, receipts = build_chunks(
        pages=pages,
        config=ChunkingConfig(
            chunk_words=10,
            overlap_words=2,
        ),
    )

    assert len(chunks) == 2

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()

    assert first_words[-2:] == second_words[:2]
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2
    assert chunks[0].chunk_id == ("123:chunk:00000")
    assert receipts[0].chunk_count == 2


def test_build_chunks_skips_empty_pages() -> None:
    pages = [
        make_page(
            1,
            "",
            status="empty",
        ),
        make_page(
            2,
            "one two three four",
        ),
    ]

    chunks, receipts = build_chunks(
        pages=pages,
        config=ChunkingConfig(
            chunk_words=10,
            overlap_words=2,
        ),
    )

    assert len(chunks) == 1
    assert chunks[0].page_start == 2
    assert receipts[0].page_count == 2
    assert receipts[0].nonempty_page_count == 1


def test_write_chunk_outputs(
    tmp_path: Path,
) -> None:
    chunks, receipts = build_chunks(
        pages=[
            make_page(
                1,
                "one two three four five",
            )
        ],
        config=ChunkingConfig(
            chunk_words=10,
            overlap_words=2,
        ),
    )

    chunks_path = tmp_path / "chunks.jsonl"
    receipts_path = tmp_path / "receipts.jsonl"

    write_chunk_records(
        chunks_path,
        chunks,
    )
    write_chunking_receipts(
        receipts_path,
        receipts,
    )

    stored_chunk = json.loads(chunks_path.read_text(encoding="utf-8").splitlines()[0])

    assert stored_chunk["document_id"] == 123
    assert stored_chunk["page_start"] == 1
    assert receipts_path.exists()
