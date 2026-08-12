"""Parity tests for native and LangGraph bounded adaptive retrieval."""

from __future__ import annotations

from aeroragx.generation.adaptive_retrieval import (
    AdaptiveEvidenceAssessment,
    AdaptiveEvidenceProvenance,
    AdaptiveRetrievalConfig,
    BoundedAdaptiveRetrievalController,
)
from aeroragx.orchestration.langgraph_adaptive import (
    LangGraphBoundedAdaptiveRetrievalController,
)


def _provenance(
    hit_set: list[str],
    attempt_number: int,
) -> list[AdaptiveEvidenceProvenance]:
    return [
        AdaptiveEvidenceProvenance(
            attempt_number=attempt_number,
            reranker_rank=index,
            chunk_id=f"chunk-{attempt_number}-{index}",
            document_id=index,
            page_start=1,
            page_end=1,
            citation_url=f"https://example.com/citation/{index}",
            source_url=f"https://example.com/source/{index}",
            document_sha256=f"sha-{attempt_number}-{index}",
            reranker_score=1.0,
            hybrid_rank=index,
            hybrid_score=1.0,
            retrieved_by=["bm25"],
            bm25_rank=index,
            bm25_score=1.0,
        )
        for index, _ in enumerate(hit_set, start=1)
    ]


def _assessment(evidence: list[str]) -> AdaptiveEvidenceAssessment:
    sufficient = "supported" in evidence
    return AdaptiveEvidenceAssessment(
        sufficient=sufficient,
        reasons=[] if sufficient else ["insufficient_support"],
    )


def _run_controllers(
    retrieval_results: dict[str, list[str]],
) -> tuple[object, object, list[str]]:
    config = AdaptiveRetrievalConfig()
    retrieval_queries: list[str] = []

    def retrieve(query: str) -> list[str]:
        retrieval_queries.append(query)
        return retrieval_results[query]

    kwargs = {
        "original_query": "What is the evidence?",
        "retrieve": retrieve,
        "build_evidence": lambda hit_set: hit_set,
        "assess_evidence": _assessment,
        "build_provenance": _provenance,
        "returned_evidence_count": len,
    }

    native = BoundedAdaptiveRetrievalController[list[str], str](config).execute(**kwargs)

    retrieval_queries.clear()

    graph = LangGraphBoundedAdaptiveRetrievalController[list[str], str](config).execute(**kwargs)

    return native, graph, retrieval_queries


def test_langgraph_matches_native_for_sufficient_first_attempt() -> None:
    native, graph, retrieval_queries = _run_controllers({"What is the evidence?": ["supported"]})

    assert graph == native
    assert retrieval_queries == ["What is the evidence?"]
    assert graph.trace.retrieval_terminal_state == "generate"
    assert len(graph.trace.attempts) == 1


def test_langgraph_matches_native_for_successful_recovery() -> None:
    rewritten_query = "What is the evidence? NASA aerospace technical report"
    native, graph, retrieval_queries = _run_controllers(
        {
            "What is the evidence?": ["insufficient"],
            rewritten_query: ["supported"],
        }
    )

    assert graph == native
    assert retrieval_queries == ["What is the evidence?", rewritten_query]
    assert graph.trace.retrieval_terminal_state == "generate"
    assert len(graph.trace.attempts) == 2


def test_langgraph_matches_native_for_grounded_refusal() -> None:
    rewritten_query = "What is the evidence? NASA aerospace technical report"
    native, graph, retrieval_queries = _run_controllers(
        {
            "What is the evidence?": ["insufficient"],
            rewritten_query: ["still_insufficient"],
        }
    )

    assert graph == native
    assert retrieval_queries == ["What is the evidence?", rewritten_query]
    assert graph.trace.retrieval_terminal_state == "grounded_refusal"
    assert len(graph.trace.attempts) == 2
