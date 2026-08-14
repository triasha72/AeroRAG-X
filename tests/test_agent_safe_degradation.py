"""Tests for failure behavior that must not become unsupported generation."""

from aeroragx.agent.contracts import AgentToolError, ToolCallRecord
from aeroragx.agent.recovery import safe_failure_termination
from aeroragx.agent.state import AgentState


def test_dependency_failure_preserves_empty_evidence() -> None:
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
    )
    failed = state.record_tool_call(
        ToolCallRecord(
            tool_call_id="call-1",
            tool_name="hybrid_retrieve",
            status="error",
            latency_ms=1.0,
            error=AgentToolError(
                code="backend_error",
                message="retrieval connection unavailable",
            ),
        )
    )
    terminal = safe_failure_termination(failed)

    assert terminal.evidence_ids == []
    assert terminal.termination_reason == "unrecoverable_tool_failure"
