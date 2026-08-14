"""Tests for Phase 41 service contracts."""

from aeroragx.services.contracts import (
    RetrievalServiceRequest,
    ServiceEvidence,
)
from aeroragx.services.request_context import RequestContext


def test_retrieval_contract_preserves_cross_service_ids() -> None:
    context = RequestContext(
        request_id="r1",
        trace_id="trace1",
        thread_id="thread1",
    )
    request = RetrievalServiceRequest(
        context=context,
        query="thermal protection",
        top_k=5,
    )
    assert request.context == context


def test_service_evidence_preserves_document_identity() -> None:
    evidence = ServiceEvidence(
        evidence_id="e1",
        document_id=123,
        text="source text",
        citation_url="https://example.com/citation",
        page_start=4,
        page_end=4,
    )
    assert evidence.document_id == 123
