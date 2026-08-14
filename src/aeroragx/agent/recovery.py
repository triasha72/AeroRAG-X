"""Safe graph-level recovery decisions after bounded tool failures."""

from __future__ import annotations

from aeroragx.agent.state import AgentState


def safe_failure_termination(state: AgentState) -> AgentState:
    """Refuse instead of fabricating when a required dependency cannot recover."""

    if not state.previous_failures:
        raise ValueError("Recovery termination requires at least one recorded failure.")

    return state.terminate("unrecoverable_tool_failure")
