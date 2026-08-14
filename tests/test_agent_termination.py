"""Tests for Phase 37 terminal states."""

from aeroragx.agent.state import AgentState
from aeroragx.agent.termination import terminate_agent


def test_termination_sets_exact_reason() -> None:
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
    )
    terminal = terminate_agent(state, "grounded_refusal")
    assert terminal.termination_reason == "grounded_refusal"
