"""Safe distributed degradation helpers."""

from aeroragx.services.contracts import (
    AgentServiceRequest,
    AgentServiceResponse,
)


def dependency_failure_response(
    request: AgentServiceRequest,
) -> AgentServiceResponse:
    """Return a non-assertive terminal response after a required dependency fails."""

    return AgentServiceResponse(
        context=request.context,
        answer=None,
        cited_evidence_ids=[],
        termination_reason="unrecoverable_tool_failure",
    )
