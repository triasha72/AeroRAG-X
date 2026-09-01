"""Citation-preserving overlapping chunks for aerospace documents."""

import json
import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from aeroragx.processing.pdf import PDFPageRecord


class ChunkingConfig(BaseModel):
    """Configuration for deterministic word-based chunking."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    chunk_words: int = Field(
        default=300,
        ge=2,
        le=5000,
    )
    overlap_words: int = Field(
        default=60,
        ge=0,
        le=2500,
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        """Ensure overlapping windows always advance."""

        if self.overlap_words >= self.chunk_words:
            raise ValueError("overlap_words must be smaller than chunk_words.")

        return self


class ChunkRecord(BaseModel):
    """One retrieval-ready text chunk with complete provenance."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    chunk_id: str
    parent_chunk_id: str | None = None
    document_id: int
    chunk_index: int = Field(ge=0)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    page_ids: list[str]
    text: str
    word_count: int = Field(ge=1)
    character_count: int = Field(ge=1)
    token_estimate: int = Field(ge=1)
    citation_url: str
    source_url: str
    document_sha256: str
    title: str | None = None
    publication_year: int | None = Field(default=None, ge=1900, le=2200)
    subject_categories: list[str] = Field(default_factory=list)
    document_type: str | None = None
    programs: list[str] = Field(default_factory=list)
    report_family: str | None = None


class ChunkingReceipt(BaseModel):
    """Summary of chunk generation for one document."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int
    page_count: int = Field(ge=0)
    nonempty_page_count: int = Field(ge=0)
    total_words: int = Field(ge=0)
    chunk_count: int = Field(ge=0)


@dataclass(frozen=True, slots=True)
class _PageWord:
    """One word associated with its source page."""

    value: str
    page_number: int
    page_id: str


def load_chunking_config(
    path: Path,
) -> ChunkingConfig:
    """Load and validate a YAML chunking configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Chunking configuration must contain a YAML mapping.")

    return ChunkingConfig.model_validate(raw_data)


def load_page_records(
    path: Path,
) -> list[PDFPageRecord]:
    """Load page records from a JSONL file."""

    pages: list[PDFPageRecord] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            page = PDFPageRecord.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid page record row {line_number}: {exc}") from exc

        pages.append(page)

    return pages


def build_chunks(
    pages: list[PDFPageRecord],
    config: ChunkingConfig,
) -> tuple[
    list[ChunkRecord],
    list[ChunkingReceipt],
]:
    """Build deterministic overlapping chunks by document."""

    pages_by_document: dict[
        int,
        list[PDFPageRecord],
    ] = defaultdict(list)

    for page in pages:
        pages_by_document[page.document_id].append(page)

    chunks: list[ChunkRecord] = []
    receipts: list[ChunkingReceipt] = []

    for document_id in sorted(pages_by_document):
        document_pages = sorted(
            pages_by_document[document_id],
            key=lambda page: page.page_number,
        )

        nonempty_pages = [
            page for page in document_pages if page.extraction_status == "ok" and page.text.strip()
        ]

        if not nonempty_pages:
            receipts.append(
                ChunkingReceipt(
                    document_id=document_id,
                    page_count=len(document_pages),
                    nonempty_page_count=0,
                    total_words=0,
                    chunk_count=0,
                )
            )
            continue

        first_page = nonempty_pages[0]

        _validate_document_provenance(
            pages=nonempty_pages,
            reference_page=first_page,
        )

        page_words: list[_PageWord] = []

        for page in nonempty_pages:
            page_words.extend(
                _PageWord(
                    value=word,
                    page_number=page.page_number,
                    page_id=page.page_id,
                )
                for word in page.text.split()
            )

        document_chunks = _chunk_document_words(
            document_id=document_id,
            page_words=page_words,
            config=config,
            citation_url=first_page.citation_url,
            source_url=first_page.source_url,
            document_sha256=(first_page.document_sha256),
        )

        chunks.extend(document_chunks)

        receipts.append(
            ChunkingReceipt(
                document_id=document_id,
                page_count=len(document_pages),
                nonempty_page_count=len(nonempty_pages),
                total_words=len(page_words),
                chunk_count=len(document_chunks),
            )
        )

    return chunks, receipts


def _validate_document_provenance(
    pages: list[PDFPageRecord],
    reference_page: PDFPageRecord,
) -> None:
    """Ensure pages from one document share provenance."""

    for page in pages:
        if page.document_sha256 != reference_page.document_sha256:
            raise ValueError(f"Inconsistent checksum for document {page.document_id}.")

        if page.citation_url != reference_page.citation_url:
            raise ValueError(f"Inconsistent citation URL for document {page.document_id}.")

        if page.source_url != reference_page.source_url:
            raise ValueError(f"Inconsistent source URL for document {page.document_id}.")


def _chunk_document_words(
    document_id: int,
    page_words: list[_PageWord],
    config: ChunkingConfig,
    citation_url: str,
    source_url: str,
    document_sha256: str,
) -> list[ChunkRecord]:
    """Create overlapping chunks for one document."""

    if not page_words:
        return []

    document_chunks: list[ChunkRecord] = []
    start = 0
    chunk_index = 0

    while start < len(page_words):
        end = min(
            start + config.chunk_words,
            len(page_words),
        )
        window = page_words[start:end]

        text = " ".join(page_word.value for page_word in window)

        page_ids = list(dict.fromkeys(page_word.page_id for page_word in window))

        document_chunks.append(
            ChunkRecord(
                chunk_id=(f"{document_id}:chunk:{chunk_index:05d}"),
                document_id=document_id,
                chunk_index=chunk_index,
                page_start=min(word.page_number for word in window),
                page_end=max(word.page_number for word in window),
                page_ids=page_ids,
                text=text,
                word_count=len(window),
                character_count=len(text),
                token_estimate=max(
                    1,
                    math.ceil(len(text) / 4),
                ),
                citation_url=citation_url,
                source_url=source_url,
                document_sha256=(document_sha256),
            )
        )

        if end == len(page_words):
            break

        start = end - config.overlap_words
        chunk_index += 1

    return document_chunks


def write_chunk_records(
    path: Path,
    chunks: list[ChunkRecord],
) -> None:
    """Write retrieval chunks as JSON Lines."""

    _write_jsonl(path, chunks)


def write_chunking_receipts(
    path: Path,
    receipts: list[ChunkingReceipt],
) -> None:
    """Write per-document chunking summaries."""

    _write_jsonl(path, receipts)


def _write_jsonl(
    path: Path,
    records: Sequence[BaseModel],
) -> None:
    """Write Pydantic records using JSON Lines."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    path.write_text(
        content,
        encoding="utf-8",
    )
