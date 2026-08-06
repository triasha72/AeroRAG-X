from pathlib import Path

import pytest

from aeroragx.processing.chunking import (
    ChunkRecord,
)
from aeroragx.retrieval.bm25 import (
    BM25Config,
    BM25Index,
    load_bm25_config,
    load_chunk_records,
    tokenize,
    write_search_results,
)


def make_chunk(
    chunk_id: str,
    text: str,
    document_id: int = 123,
) -> ChunkRecord:
    """Create a retrieval test chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        page_ids=[f"{document_id}:page:1"],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(
            1,
            len(text) // 4,
        ),
        citation_url=(f"https://ntrs.nasa.gov/citations/{document_id}"),
        source_url=(f"https://example.com/{document_id}.pdf"),
        document_sha256="test-checksum",
    )


def test_tokenize_normalizes_text() -> None:
    assert tokenize("Battery-Thermal Management, NASA!") == [
        "battery-thermal",
        "management",
        "nasa",
    ]


def test_load_bm25_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bm25.yaml"

    path.write_text(
        """
version: "0.1"
k1: 1.4
b: 0.7
default_top_k: 5
""".strip(),
        encoding="utf-8",
    )

    config = load_bm25_config(path)

    assert config.k1 == 1.4
    assert config.b == 0.7
    assert config.default_top_k == 5


def test_bm25_ranks_relevant_chunk_first() -> None:
    chunks = [
        make_chunk(
            "123:chunk:00000",
            ("battery thermal management battery cooling thermal runaway"),
        ),
        make_chunk(
            "124:chunk:00000",
            ("air traffic control and airport operations"),
            document_id=124,
        ),
    ]

    index = BM25Index(
        chunks,
        BM25Config(),
    )

    hits = index.search(
        "battery thermal management",
        top_k=2,
    )

    assert len(hits) == 1
    assert hits[0].chunk.chunk_id == ("123:chunk:00000")
    assert hits[0].rank == 1
    assert hits[0].score > 0


def test_bm25_preserves_citation_metadata() -> None:
    chunk = make_chunk(
        "123:chunk:00000",
        "fuel cell thermal management",
    )

    hits = BM25Index([chunk]).search(
        "fuel cell",
    )

    assert hits[0].chunk.document_id == 123
    assert hits[0].chunk.page_start == 1
    assert hits[0].chunk.citation_url.endswith("/123")


def test_bm25_empty_query_returns_no_hits() -> None:
    chunk = make_chunk(
        "123:chunk:00000",
        "aircraft propulsion",
    )

    assert BM25Index([chunk]).search("   ") == []


def test_bm25_rejects_invalid_top_k() -> None:
    index = BM25Index(
        [
            make_chunk(
                "123:chunk:00000",
                "aircraft propulsion",
            )
        ]
    )

    with pytest.raises(ValueError):
        index.search(
            "aircraft",
            top_k=0,
        )


def test_chunk_loading_and_result_writing(
    tmp_path: Path,
) -> None:
    chunk = make_chunk(
        "123:chunk:00000",
        "hybrid electric propulsion",
    )

    chunk_path = tmp_path / "chunks.jsonl"
    chunk_path.write_text(
        chunk.model_dump_json() + "\n",
        encoding="utf-8",
    )

    chunks = load_chunk_records(chunk_path)
    hits = BM25Index(chunks).search(
        "electric propulsion",
    )

    output_path = tmp_path / "results.jsonl"

    write_search_results(
        output_path,
        hits,
    )

    assert len(chunks) == 1
    assert output_path.exists()
    assert '"rank": 1' in output_path.read_text(encoding="utf-8")
