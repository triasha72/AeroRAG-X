"""Tests for safe failure termination."""

from aeroragx.agent.contracts import AgentToolError, ToolCallRecord
from aeroragx.agent.recovery import safe_failure_termination
from aeroragx.agent.state import AgentState


def test_unrecoverable_failure_terminates_without_answer_claim() -> None:
    call = ToolCallRecord(
        tool_call_id="call-1",
        tool_name="hybrid_retrieve",
        status="error",
        latency_ms=1.0,
        error=AgentToolError(
            code="backend_error",
            message="dependency unavailable",
        ),
    )
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
    ).record_tool_call(call)

    terminal = safe_failure_termination(state)
    assert terminal.termination_reason == "unrecoverable_tool_failure"
