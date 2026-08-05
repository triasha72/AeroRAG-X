"""Reproducible NTRS corpus definition and manifest generation."""

import json
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aeroragx.ingestion.ntrs import NTRSRecord


class CorpusDefinition(BaseModel):
    """Configuration describing a reproducible NTRS corpus."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    corpus_name: str
    version: str
    description: str
    queries: list[str]
    max_records_per_query: int = Field(
        default=25,
        ge=1,
        le=1000,
    )

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, queries: list[str]) -> list[str]:
        """Reject empty query lists and normalize duplicate queries."""

        cleaned_queries: list[str] = []

        for query in queries:
            normalized = query.strip()

            if normalized and normalized not in cleaned_queries:
                cleaned_queries.append(normalized)

        if not cleaned_queries:
            raise ValueError("At least one non-empty corpus query is required.")

        return cleaned_queries


class ManifestEntry(BaseModel):
    """One normalized NASA document in the corpus manifest."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int
    title: str
    abstract: str | None = None
    citation_url: str
    pdf_url: str | None = None
    fulltext_url: str | None = None
    downloads_available: bool | None = None
    keywords: list[str] = Field(default_factory=list)
    subject_categories: list[str] = Field(default_factory=list)
    sti_type: str | None = None
    distribution: str | None = None
    disseminated: str | None = None
    source_queries: list[str] = Field(default_factory=list)

    @classmethod
    def from_record(
        cls,
        record: NTRSRecord,
        source_query: str,
    ) -> "ManifestEntry":
        """Create a manifest entry from an NTRS record."""

        return cls(
            document_id=record.document_id,
            title=record.title,
            abstract=record.abstract or None,
            citation_url=record.citation_url,
            pdf_url=record.pdf_url(),
            fulltext_url=record.fulltext_url(),
            downloads_available=record.downloads_available,
            keywords=sorted(set(record.keywords)),
            subject_categories=sorted(set(record.subject_categories)),
            sti_type=record.sti_type,
            distribution=record.distribution,
            disseminated=record.disseminated,
            source_queries=[source_query],
        )


class NTRSSearchClient(Protocol):
    """Interface required by the corpus builder."""

    def search(
        self,
        query: str,
        limit: int = 100,
        page_size: int = 50,
    ) -> list[NTRSRecord]:
        """Search NTRS and return normalized records."""


def load_corpus_definition(path: Path) -> CorpusDefinition:
    """Load and validate a corpus YAML configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Corpus configuration must contain a YAML mapping.")

    return CorpusDefinition.model_validate(raw_data)


def build_manifest(
    client: NTRSSearchClient,
    definition: CorpusDefinition,
) -> list[ManifestEntry]:
    """Search all corpus queries and deduplicate by document ID."""

    entries_by_id: dict[int, ManifestEntry] = {}

    page_size = min(
        definition.max_records_per_query,
        100,
    )

    for query in definition.queries:
        records = client.search(
            query=query,
            limit=definition.max_records_per_query,
            page_size=page_size,
        )

        for record in records:
            existing = entries_by_id.get(record.document_id)

            if existing is None:
                entries_by_id[record.document_id] = ManifestEntry.from_record(
                    record=record,
                    source_query=query,
                )
                continue

            if query not in existing.source_queries:
                existing.source_queries.append(query)
                existing.source_queries.sort()

            existing.keywords = sorted(set(existing.keywords) | set(record.keywords))
            existing.subject_categories = sorted(
                set(existing.subject_categories) | set(record.subject_categories)
            )

            if existing.abstract is None and record.abstract:
                existing.abstract = record.abstract

            if existing.pdf_url is None:
                existing.pdf_url = record.pdf_url()

            if existing.fulltext_url is None:
                existing.fulltext_url = record.fulltext_url()

    return [entries_by_id[document_id] for document_id in sorted(entries_by_id)]


def write_manifest(
    path: Path,
    entries: list[ManifestEntry],
) -> None:
    """Write the manifest using JSON Lines format."""

    path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        json.dumps(
            entry.model_dump(mode="json"),
            sort_keys=True,
        )
        for entry in entries
    ]

    content = "\n".join(rows)

    if content:
        content += "\n"

    path.write_text(content, encoding="utf-8")
