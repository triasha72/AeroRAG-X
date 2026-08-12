"""Tests for the LangChain AeroRAG-X reranked retrieval adapter."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aeroragx.orchestration.langchain_retriever import (
    LangChainRerankedRetriever,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


class StaticRerankedIndex:
    """Small deterministic index used to test the LangChain adapter."""

    def __init__(
        self,
        hits: Sequence[RerankedSearchHit],
    ) -> None:
        self.hits = list(hits)
        self.calls: list[tuple[str, int]] = []

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RerankedSearchHit]:
        self.calls.append((query, top_k))
        return self.hits[:top_k]


def _hit(
    *,
    chunk_id: str = "chunk-1",
) -> RerankedSearchHit:
    """Build one complete reranked hit with dual-retrieval provenance."""

    return RerankedSearchHit(
        rank=1,
        score=0.91,
        chunk=ChunkRecord(
            chunk_id=chunk_id,
            document_id=42,
            chunk_index=0,
            page_start=3,
            page_end=4,
            page_ids=["document-42-page-3", "document-42-page-4"],
            text="Thermal protection evidence from a NASA technical report.",
            word_count=9,
            character_count=58,
            token_estimate=15,
            citation_url="https://ntrs.nasa.gov/citations/42",
            source_url="https://ntrs.nasa.gov/api/citations/42/downloads/report.pdf",
            document_sha256="a" * 64,
        ),
        hybrid_rank=2,
        hybrid_score=0.73,
        retrieved_by=["bm25", "dense"],
        bm25_rank=3,
        bm25_score=4.2,
        dense_rank=4,
        dense_score=0.81,
    )


def test_retriever_returns_langchain_documents_with_provenance() -> None:
    """The adapter returns Documents without dropping retrieval provenance."""

    index = StaticRerankedIndex([_hit()])
    retriever = LangChainRerankedRetriever(index=index, top_k=3)

    documents = retriever.invoke("thermal protection")

    assert index.calls == [("thermal protection", 3)]
    assert len(documents) == 1

    document = documents[0]

    assert document.id == "chunk-1"
    assert document.page_content == "Thermal protection evidence from a NASA technical report."
    assert document.metadata["document_id"] == 42
    assert document.metadata["page_start"] == 3
    assert document.metadata["page_end"] == 4
    assert document.metadata["document_sha256"] == "a" * 64
    assert document.metadata["reranker_rank"] == 1
    assert document.metadata["reranker_score"] == 0.91
    assert document.metadata["hybrid_rank"] == 2
    assert document.metadata["hybrid_score"] == 0.73
    assert document.metadata["retrieved_by"] == ["bm25", "dense"]
    assert document.metadata["bm25_rank"] == 3
    assert document.metadata["dense_score"] == 0.81


def test_retriever_strips_the_query_before_search() -> None:
    """Whitespace around a valid query is not passed to the source index."""

    index = StaticRerankedIndex([_hit()])
    retriever = LangChainRerankedRetriever(index=index)

    retriever.invoke("  thermal protection  ")

    assert index.calls == [("thermal protection", 5)]


def test_retriever_rejects_blank_queries() -> None:
    """Blank queries fail before retrieval occurs."""

    index = StaticRerankedIndex([_hit()])
    retriever = LangChainRerankedRetriever(index=index)

    with pytest.raises(ValueError, match="query must not be blank"):
        retriever.invoke("   ")

    assert index.calls == []


def test_retriever_rejects_duplicate_chunk_ids() -> None:
    """Duplicate chunk IDs cannot become ambiguous LangChain documents."""

    index = StaticRerankedIndex([_hit(), _hit()])
    retriever = LangChainRerankedRetriever(index=index)

    with pytest.raises(
        ValueError,
        match="duplicate chunk IDs",
    ):
        retriever.invoke("thermal protection")
