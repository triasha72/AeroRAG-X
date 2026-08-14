"""Tests for dependency-failure safe degradation."""

from aeroragx.services.contracts import AgentServiceRequest
from aeroragx.services.degradation import dependency_failure_response
from aeroragx.services.request_context import RequestContext


def test_dependency_failure_never_returns_an_answer() -> None:
    request = AgentServiceRequest(
        context=RequestContext(
            request_id="r1",
            trace_id="trace1",
            thread_id="thread1",
        ),
        query="q",
    )
    response = dependency_failure_response(request)

    assert response.answer is None
    assert response.cited_evidence_ids == []
    assert response.termination_reason == "unrecoverable_tool_failure"
