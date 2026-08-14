"""Tests for bounded Phase 36 agent state."""

import pytest
from pydantic import ValidationError

from aeroragx.agent.contracts import AgentToolError, ToolCallRecord
from aeroragx.agent.state import AgentState


def make_state() -> AgentState:
    return AgentState(
        request_id="request-1",
        thread_id="thread-1",
        original_query="What does the report say?",
        current_query="What does the report say?",
    )


def test_advance_step_tracks_selected_tool() -> None:
    state = make_state().advance_step(selected_tool="hybrid_retrieve")

    assert state.step_number == 1
    assert state.selected_tool == "hybrid_retrieve"


def test_state_rejects_exhausted_step_budget() -> None:
    state = AgentState(
        request_id="request-1",
        thread_id="thread-1",
        original_query="Question",
        current_query="Question",
        step_number=1,
        maximum_steps=1,
    )

    with pytest.raises(ValueError, match="step budget"):
        state.advance_step()


def test_record_tool_call_tracks_evidence_and_retrieval_budget() -> None:
    state = make_state()
    call = ToolCallRecord(
        tool_call_id="call-1",
        tool_name="hybrid_retrieve",
        status="success",
        latency_ms=2.0,
    )

    updated = state.record_tool_call(
        call,
        retrieval_attempt=True,
        evidence_ids=["e-1", "e-2"],
        document_ids=[123, 456],
    )

    assert updated.tool_call_count == 1
    assert updated.retrieval_attempt_count == 1
    assert updated.evidence_ids == ["e-1", "e-2"]
    assert updated.document_ids == [123, 456]


def test_record_failed_tool_call_preserves_failure() -> None:
    state = make_state()
    call = ToolCallRecord(
        tool_call_id="call-1",
        tool_name="hybrid_retrieve",
        status="error",
        latency_ms=2.0,
        error=AgentToolError(
            code="backend_error",
            message="retrieval unavailable",
        ),
    )

    updated = state.record_tool_call(call)

    assert len(updated.previous_failures) == 1
    assert updated.previous_failures[0].error_code == "backend_error"


def test_state_rejects_history_count_mismatch() -> None:
    with pytest.raises(ValidationError, match="tool_call_count"):
        AgentState(
            request_id="request-1",
            thread_id="thread-1",
            original_query="Question",
            current_query="Question",
            tool_call_count=1,
        )
