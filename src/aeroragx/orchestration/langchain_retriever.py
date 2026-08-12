"""LangChain retrieval adapter for provenance-preserving AeroRAG-X hits."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from aeroragx.retrieval.reranker import RerankedSearchHit


class LangChainRerankedRetriever(BaseRetriever):
    """Expose AeroRAG-X reranked retrieval through LangChain's retriever API.

    Every returned Document retains the source, page, integrity, and
    retrieval-stage provenance required for grounded answer generation.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: Any
    top_k: int = Field(default=5, ge=1, le=100)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """Retrieve bounded LangChain Documents from reranked AeroRAG-X hits."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query must not be blank.")

        hits: Sequence[RerankedSearchHit] = self.index.search(
            query=normalized_query,
            top_k=self.top_k,
        )

        chunk_ids = [hit.chunk.chunk_id for hit in hits]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Reranked retrieval returned duplicate chunk IDs.")

        return [
            Document(
                id=hit.chunk.chunk_id,
                page_content=hit.chunk.text,
                metadata={
                    "chunk_id": hit.chunk.chunk_id,
                    "document_id": hit.chunk.document_id,
                    "chunk_index": hit.chunk.chunk_index,
                    "page_start": hit.chunk.page_start,
                    "page_end": hit.chunk.page_end,
                    "page_ids": hit.chunk.page_ids,
                    "word_count": hit.chunk.word_count,
                    "character_count": hit.chunk.character_count,
                    "token_estimate": hit.chunk.token_estimate,
                    "citation_url": hit.chunk.citation_url,
                    "source_url": hit.chunk.source_url,
                    "document_sha256": hit.chunk.document_sha256,
                    "reranker_rank": hit.rank,
                    "reranker_score": hit.score,
                    "hybrid_rank": hit.hybrid_rank,
                    "hybrid_score": hit.hybrid_score,
                    "retrieved_by": hit.retrieved_by,
                    "bm25_rank": hit.bm25_rank,
                    "bm25_score": hit.bm25_score,
                    "dense_rank": hit.dense_rank,
                    "dense_score": hit.dense_score,
                },
            )
            for hit in hits
        ]
