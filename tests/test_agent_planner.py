"""Tests for Phase 37 planner behavior."""

from aeroragx.agent.planner import DeterministicEvidencePlanner
from aeroragx.agent.state import AgentState


def state() -> AgentState:
    return AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="query",
        current_query="query",
    )


def test_planner_retrieves_when_no_evidence_exists() -> None:
    decision = DeterministicEvidencePlanner().decide(state())
    assert decision.action == "tool"
    assert decision.selected_tool == "hybrid_retrieve"


def test_planner_generates_when_evidence_is_sufficient() -> None:
    payload = state().model_dump(mode="python")
    payload["evidence_ids"] = ["e1"]
    payload["evidence_sufficient"] = True
    decision = DeterministicEvidencePlanner().decide(AgentState.model_validate(payload))
    assert decision.action == "generate"
