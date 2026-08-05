import json
from pathlib import Path

from aeroragx.ingestion.corpus import (
    CorpusDefinition,
    build_manifest,
    load_corpus_definition,
    write_manifest,
)
from aeroragx.ingestion.ntrs import NTRSRecord


class FakeNTRSClient:
    """Predictable search client used by corpus tests."""

    def __init__(
        self,
        results: dict[str, list[NTRSRecord]],
    ) -> None:
        self.results = results

    def search(
        self,
        query: str,
        limit: int = 100,
        page_size: int = 50,
    ) -> list[NTRSRecord]:
        del page_size
        return self.results.get(query, [])[:limit]


def test_load_corpus_definition(tmp_path: Path) -> None:
    config_path = tmp_path / "corpus.yaml"

    config_path.write_text(
        """
corpus_name: test-corpus
version: "0.1"
description: Test aerospace corpus
queries:
  - electric aircraft
  - thermal management
max_records_per_query: 10
""".strip(),
        encoding="utf-8",
    )

    definition = load_corpus_definition(config_path)

    assert definition.corpus_name == "test-corpus"
    assert definition.max_records_per_query == 10
    assert len(definition.queries) == 2


def test_build_manifest_deduplicates_records() -> None:
    shared_record = NTRSRecord.model_validate(
        {
            "id": 20240015017,
            "title": "Thermal Management for Electric Aircraft",
            "abstract": "Technical report.",
            "downloadsAvailable": True,
            "keywords": ["Thermal Management"],
            "subjectCategories": ["Aircraft Propulsion and Power"],
        }
    )

    second_record = NTRSRecord.model_validate(
        {
            "id": 20220005430,
            "title": "Electrified Aircraft Systems",
            "keywords": ["Electric Aircraft"],
        }
    )

    client = FakeNTRSClient(
        {
            "electric aircraft": [
                shared_record,
                second_record,
            ],
            "thermal management": [
                shared_record,
            ],
        }
    )

    definition = CorpusDefinition(
        corpus_name="test-corpus",
        version="0.1",
        description="Test corpus",
        queries=[
            "electric aircraft",
            "thermal management",
        ],
        max_records_per_query=10,
    )

    manifest = build_manifest(client, definition)

    assert len(manifest) == 2

    shared_entry = next(entry for entry in manifest if entry.document_id == 20240015017)

    assert shared_entry.source_queries == [
        "electric aircraft",
        "thermal management",
    ]
    assert shared_entry.citation_url.endswith("20240015017")


def test_write_manifest_creates_jsonl(
    tmp_path: Path,
) -> None:
    definition = CorpusDefinition(
        corpus_name="test-corpus",
        version="0.1",
        description="Test corpus",
        queries=["electric aircraft"],
        max_records_per_query=10,
    )

    record = NTRSRecord.model_validate(
        {
            "id": 123,
            "title": "Example Report",
        }
    )

    client = FakeNTRSClient({"electric aircraft": [record]})

    entries = build_manifest(client, definition)
    output_path = tmp_path / "manifest.jsonl"

    write_manifest(output_path, entries)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    stored_record = json.loads(lines[0])

    assert stored_record["document_id"] == 123
    assert stored_record["title"] == "Example Report"
