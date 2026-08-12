# LangChain retriever adapter v0.1

## Purpose

This adapter exposes AeroRAG-X reranked retrieval through LangChain's `BaseRetriever` interface.

It converts each `RerankedSearchHit` into a LangChain `Document` without dropping the source, page, integrity, reranking, hybrid-retrieval, BM25, or dense-retrieval provenance needed by AeroRAG-X.

The adapter is an opt-in integration boundary. It does not replace AeroRAG-X's native retrieval or evidence-validation behavior.

## Retrieval boundary

```text
AeroRAG-X reranked index
        |
        v
RerankedSearchHit
        |
        v
LangChainRerankedRetriever
        |
        v
LangChain Document