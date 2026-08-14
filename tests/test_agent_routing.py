"""Tests for Phase 37 routing invariants."""

from aeroragx.agent.contracts import ToolCallRecord
from aeroragx.agent.planner import PlannerDecision
from aeroragx.agent.routing import route_planner_decision
from aeroragx.agent.state import AgentState


def test_tool_route_stops_when_tool_budget_is_exhausted() -> None:
    call = ToolCallRecord(
        tool_call_id="call-1",
        tool_name="hybrid_retrieve",
        status="success",
        latency_ms=1.0,
    )
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
        tool_call_count=1,
        maximum_tool_calls=1,
        tool_history=[call],
    )
    decision = PlannerDecision(
        action="tool",
        selected_tool="hybrid_retrieve",
        reason="retrieve",
    )
    assert route_planner_decision(state, decision) == "tool_budget_exhausted"


def test_human_review_is_explicit_route() -> None:
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
    )
    decision = PlannerDecision(
        action="human_review",
        reason="Conflicting evidence.",
    )
    assert route_planner_decision(state, decision) == "human_review"
