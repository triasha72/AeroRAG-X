"""End-to-end LangChain retriever and LangGraph controller integration test."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.documents import Document

from aeroragx.generation.adaptive_retrieval import (
    AdaptiveEvidenceAssessment,
    AdaptiveEvidenceProvenance,
    AdaptiveRetrievalConfig,
)
from aeroragx.orchestration.langchain_retriever import (
    LangChainRerankedRetriever,
)
from aeroragx.orchestration.langgraph_adaptive import (
    LangGraphBoundedAdaptiveRetrievalController,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


class QueryMappedRerankedIndex:
    """Deterministic source index used for LangChain-LangGraph integration."""

    def __init__(
        self,
        results: dict[str, list[RerankedSearchHit]],
    ) -> None:
        self._results = results
        self.calls: list[tuple[str, int]] = []

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RerankedSearchHit]:
        self.calls.append((query, top_k))
        return self._results[query][:top_k]


def _hit(
    *,
    chunk_id: str,
) -> RerankedSearchHit:
    """Create a complete hit whose chunk ID controls the test assessment."""

    return RerankedSearchHit(
        rank=1,
        score=0.91,
        chunk=ChunkRecord(
            chunk_id=chunk_id,
            document_id=42,
            chunk_index=0,
            page_start=3,
            page_end=3,
            page_ids=["document-42-page-3"],
            text=f"Evidence for {chunk_id}.",
            word_count=3,
            character_count=25,
            token_estimate=6,
            citation_url="https://ntrs.nasa.gov/citations/42",
            source_url="https://ntrs.nasa.gov/api/citations/42/downloads/report.pdf",
            document_sha256="a" * 64,
        ),
        hybrid_rank=1,
        hybrid_score=0.73,
        retrieved_by=["bm25", "dense"],
        bm25_rank=1,
        bm25_score=4.2,
        dense_rank=1,
        dense_score=0.81,
    )


def _provenance(
    documents: Sequence[Document],
    attempt_number: int,
) -> list[AdaptiveEvidenceProvenance]:
    """Rebuild authoritative provenance from adapter metadata."""

    return [
        AdaptiveEvidenceProvenance(
            attempt_number=attempt_number,
            reranker_rank=document.metadata["reranker_rank"],
            chunk_id=document.metadata["chunk_id"],
            document_id=document.metadata["document_id"],
            page_start=document.metadata["page_start"],
            page_end=document.metadata["page_end"],
            citation_url=document.metadata["citation_url"],
            source_url=document.metadata["source_url"],
            document_sha256=document.metadata["document_sha256"],
            reranker_score=document.metadata["reranker_score"],
            hybrid_rank=document.metadata["hybrid_rank"],
            hybrid_score=document.metadata["hybrid_score"],
            retrieved_by=document.metadata["retrieved_by"],
            bm25_rank=document.metadata["bm25_rank"],
            bm25_score=document.metadata["bm25_score"],
            dense_rank=document.metadata["dense_rank"],
            dense_score=document.metadata["dense_score"],
        )
        for document in documents
    ]


def test_langgraph_runs_bounded_recovery_over_langchain_documents() -> None:
    """LangGraph can recover using Documents from the LangChain adapter."""

    original_query = "What protects a spacecraft during re-entry?"
    rewritten_query = "What protects a spacecraft during re-entry? NASA aerospace technical report"
    index = QueryMappedRerankedIndex(
        {
            original_query: [_hit(chunk_id="insufficient")],
            rewritten_query: [_hit(chunk_id="supported")],
        }
    )
    retriever = LangChainRerankedRetriever(index=index, top_k=2)
    controller = LangGraphBoundedAdaptiveRetrievalController[
        list[Document],
        Document,
    ](AdaptiveRetrievalConfig())

    outcome = controller.execute(
        original_query=original_query,
        retrieve=lambda query: retriever.invoke(query),
        build_evidence=lambda documents: documents,
        assess_evidence=lambda documents: AdaptiveEvidenceAssessment(
            sufficient=any(document.metadata["chunk_id"] == "supported" for document in documents),
            reasons=(
                []
                if any(document.metadata["chunk_id"] == "supported" for document in documents)
                else ["insufficient_support"]
            ),
        ),
        build_provenance=_provenance,
        returned_evidence_count=len,
    )

    assert index.calls == [
        (original_query, 2),
        (rewritten_query, 2),
    ]
    assert outcome.trace.retrieval_terminal_state == "generate"
    assert len(outcome.trace.attempts) == 2
    assert outcome.evidence[0].page_content == "Evidence for supported."
    assert outcome.evidence[0].metadata["document_sha256"] == "a" * 64
    assert outcome.trace.attempts[1].evidence_provenance[0].chunk_id == "supported"
