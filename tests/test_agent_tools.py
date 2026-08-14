"""Tests for bounded Phase 36 agent tool wrappers."""

from collections.abc import Sequence

from aeroragx.agent.contracts import (
    CheckEvidenceSufficiencyRequest,
    CompareSourcesRequest,
    EvidenceReference,
    FetchSourceContextRequest,
    HybridRetrieveRequest,
    SourceComparisonRecord,
    SourceContextRecord,
    SufficiencyAssessment,
    ValidateCitationsRequest,
)
from aeroragx.agent.tools import (
    check_evidence_sufficiency,
    compare_sources,
    fetch_source_context,
    hybrid_retrieve,
    validate_citations,
)


def retrieval_backend(query: str, top_k: int) -> Sequence[EvidenceReference]:
    assert query == "thermal barrier"
    assert top_k == 5
    return [
        EvidenceReference(
            evidence_id="e-1",
            document_id=123,
            page_start=4,
            page_end=4,
            citation_url="https://example.com/citation/123",
            score=0.9,
        )
    ]


def source_backend(evidence_ids: Sequence[str]) -> Sequence[SourceContextRecord]:
    assert list(evidence_ids) == ["e-1"]
    return [
        SourceContextRecord(
            evidence_id="e-1",
            document_id=123,
            text="Authoritative source context.",
            page_start=4,
            page_end=4,
            source_url="https://example.com/source.pdf",
            citation_url="https://example.com/citation/123",
            document_sha256="abc123",
        )
    ]


def sufficiency_backend(
    query: str,
    evidence_ids: Sequence[str],
) -> SufficiencyAssessment:
    assert query == "thermal barrier"
    assert list(evidence_ids) == ["e-1"]
    return SufficiencyAssessment(
        sufficient=True,
        reasons=[],
        coverage=1.0,
    )


def comparison_backend(
    evidence_ids: Sequence[str],
) -> Sequence[SourceComparisonRecord]:
    assert list(evidence_ids) == ["e-1", "e-2"]
    return [
        SourceComparisonRecord(
            comparison_id="comparison-1",
            evidence_ids=["e-1", "e-2"],
            document_ids=[123, 456],
            summary="The sources use different operating conditions.",
            conflict_detected=False,
        )
    ]


def test_hybrid_retrieve_preserves_evidence_provenance() -> None:
    result = hybrid_retrieve(
        HybridRetrieveRequest(query="thermal barrier", top_k=5),
        backend=retrieval_backend,
        tool_call_id="call-1",
    )

    assert result.call.status == "success"
    assert result.evidence[0].evidence_id == "e-1"
    assert result.evidence[0].document_id == 123


def test_hybrid_retrieve_converts_backend_failure_to_structured_error() -> None:
    def failing_backend(query: str, top_k: int) -> Sequence[EvidenceReference]:
        del query, top_k
        raise RuntimeError("backend unavailable")

    result = hybrid_retrieve(
        HybridRetrieveRequest(query="thermal barrier", top_k=5),
        backend=failing_backend,
        tool_call_id="call-1",
    )

    assert result.call.status == "error"
    assert result.call.error is not None
    assert result.call.error.code == "backend_error"
    assert result.evidence == []


def test_fetch_source_context_returns_only_requested_context() -> None:
    result = fetch_source_context(
        FetchSourceContextRequest(evidence_ids=["e-1"]),
        backend=source_backend,
        tool_call_id="call-2",
    )

    assert result.call.status == "success"
    assert result.contexts[0].evidence_id == "e-1"


def test_sufficiency_tool_preserves_structured_assessment() -> None:
    result = check_evidence_sufficiency(
        CheckEvidenceSufficiencyRequest(
            query="thermal barrier",
            evidence_ids=["e-1"],
        ),
        backend=sufficiency_backend,
        tool_call_id="call-3",
    )

    assert result.call.status == "success"
    assert result.assessment is not None
    assert result.assessment.sufficient is True


def test_validate_citations_rejects_unknown_and_duplicate_ids() -> None:
    result = validate_citations(
        ValidateCitationsRequest(
            cited_evidence_ids=["e-1", "e-1", "unknown"],
            known_evidence_ids=["e-1", "e-2"],
        ),
        tool_call_id="call-4",
    )

    assert result.valid is False
    assert result.duplicate_evidence_ids == ["e-1"]
    assert result.unknown_evidence_ids == ["unknown"]


def test_compare_sources_preserves_multi_document_identity() -> None:
    result = compare_sources(
        CompareSourcesRequest(evidence_ids=["e-1", "e-2"]),
        backend=comparison_backend,
        tool_call_id="call-5",
    )

    assert result.call.status == "success"
    assert result.comparisons[0].document_ids == [123, 456]
