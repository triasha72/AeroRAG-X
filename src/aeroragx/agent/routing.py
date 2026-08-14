"""Pure routing helpers for the stateful agent graph."""

from __future__ import annotations

from typing import Literal

from aeroragx.agent.planner import PlannerDecision
from aeroragx.agent.state import AgentState

PlanRoute = Literal[
    "execute_tool",
    "generate",
    "grounded_refusal",
    "human_review",
    "tool_budget_exhausted",
]


def route_planner_decision(
    state: AgentState,
    decision: PlannerDecision,
) -> PlanRoute:
    """Convert a bounded planner decision into one graph route.

    Step-budget exhaustion is checked before the graph advances into a new
    planning step. This helper only routes the validated decision produced for
    the current step.
    """

    if decision.action == "tool":
        if state.tool_call_count >= state.maximum_tool_calls:
            return "tool_budget_exhausted"
        return "execute_tool"

    if decision.action == "generate":
        return "generate"

    if decision.action == "human_review":
        return "human_review"

    return "grounded_refusal"
