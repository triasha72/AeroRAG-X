"""Termination helpers for bounded agent execution."""

from aeroragx.agent.state import AgentState, AgentTerminationReason


def terminate_agent(
    state: AgentState,
    reason: AgentTerminationReason,
) -> AgentState:
    """Return one terminal state while preserving validated budgets."""

    return state.terminate(reason)
