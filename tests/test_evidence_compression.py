"""Tests for source-preserving extractive evidence compression."""

from __future__ import annotations

from aeroragx.generation.evidence_compression import (
    CompressedEvidenceIndex,
    EvidenceCompressionConfig,
    compress_evidence_text,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


class Index:
    def __init__(self, hit: RerankedSearchHit) -> None:
        self.hit = hit

    def search(self, query: str, top_k: int = 10):
        return [self.hit][:top_k]


def make_hit(text: str) -> RerankedSearchHit:
    chunk = ChunkRecord(
        chunk_id="100:chunk:00000",
        document_id=100,
        chunk_index=0,
        page_start=1,
        page_end=1,
        page_ids=["100:page:1"],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url="https://ntrs.nasa.gov/citations/100",
        source_url="https://ntrs.nasa.gov/api/citations/100/downloads/report.pdf",
        document_sha256="a" * 64,
    )
    return RerankedSearchHit(
        rank=1,
        score=1.0,
        chunk=chunk,
        hybrid_rank=1,
        hybrid_score=0.1,
        retrieved_by=["bm25"],
        bm25_rank=1,
        bm25_score=1.0,
    )


def test_selects_query_relevant_sentences_in_source_order() -> None:
    text = (
        "The program began in 2010. "
        "Battery thermal management removes heat from aircraft systems. "
        "The report also lists administrative contacts. "
        "Cooling protects battery performance during flight."
    )
    result = compress_evidence_text(
        query="How does aircraft battery cooling manage heat?",
        text=text,
        config=EvidenceCompressionConfig(max_sentences_per_evidence=2),
    )
    assert result == (
        "Battery thermal management removes heat from aircraft systems. "
        "Cooling protects battery performance during flight."
    )


def test_never_returns_empty_text() -> None:
    result = compress_evidence_text(
        query="battery",
        text="short fragment",
        config=EvidenceCompressionConfig(minimum_sentence_characters=20),
    )
    assert result == "short fragment"


def test_respects_character_bound() -> None:
    result = compress_evidence_text(
        query="aircraft heat",
        text=("Aircraft heat management " + "x" * 300 + "."),
        config=EvidenceCompressionConfig(max_characters_per_evidence=100),
    )
    assert 0 < len(result) <= 100


def test_index_preserves_source_identity_and_records_reduction() -> None:
    hit = make_hit(
        "Administrative introduction with unrelated details. "
        "Aircraft battery cooling removes heat during flight. "
        "A final unrelated sentence contains extra words."
    )
    index = CompressedEvidenceIndex(Index(hit), EvidenceCompressionConfig())
    result = list(index.search("How does aircraft battery cooling remove heat?", top_k=1))
    assert len(result) == 1
    assert result[0].chunk.chunk_id == hit.chunk.chunk_id
    assert result[0].chunk.document_id == hit.chunk.document_id
    assert result[0].chunk.document_sha256 == hit.chunk.document_sha256
    assert result[0].chunk.text != hit.chunk.text
    assert index.decisions[0].removed_characters > 0
