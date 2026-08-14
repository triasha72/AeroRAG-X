"""Resume helpers for checkpointed human-review interruptions."""

from __future__ import annotations

from aeroragx.agent.human_review import HumanReviewResponse
from aeroragx.agent.state import AgentState


def clear_terminal_state(state: AgentState) -> AgentState:
    """Return a resumable copy of a human-review terminal state."""

    payload = state.model_dump(mode="python")
    payload["termination_reason"] = None
    payload["human_review_required"] = False
    payload["selected_tool"] = None
    return AgentState.model_validate(payload)


def apply_human_review(
    state: AgentState,
    response: HumanReviewResponse,
) -> AgentState:
    """Apply approve/reject/edit semantics without mutating the original state."""

    if state.termination_reason != "human_review_required":
        raise ValueError("Human-review responses require a human-review terminal state.")

    if response.decision == "reject":
        payload = state.model_dump(mode="python")
        payload["termination_reason"] = "grounded_refusal"
        payload["human_review_required"] = False
        return AgentState.model_validate(payload)

    resumed = clear_terminal_state(state)

    if response.decision == "edit":
        payload = resumed.model_dump(mode="python")
        payload["current_query"] = response.edited_query
        return AgentState.model_validate(payload)

    return resumed
