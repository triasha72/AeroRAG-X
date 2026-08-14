"""Planner contracts for the stateful AeroRAG-X agent graph."""

from __future__ import annotations

from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.agent.contracts import AgentToolName
from aeroragx.agent.state import AgentState

PlannerAction = Literal["tool", "generate", "refuse", "human_review"]


class PlannerDecision(BaseModel):
    """One bounded planner decision consumed by the graph router."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: PlannerAction
    selected_tool: AgentToolName | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_selected_tool(self) -> Self:
        if self.action == "tool" and self.selected_tool is None:
            raise ValueError("Tool actions require selected_tool.")
        if self.action != "tool" and self.selected_tool is not None:
            raise ValueError("Only tool actions may include selected_tool.")
        return self


class AgentPlanner(Protocol):
    """Planner interface used by the stateful graph."""

    def decide(self, state: AgentState) -> PlannerDecision:
        """Return the next bounded graph action."""

        ...


class DeterministicEvidencePlanner:
    """Reference policy used for regression tests and deterministic fallback."""

    def decide(self, state: AgentState) -> PlannerDecision:
        if state.termination_reason is not None:
            return PlannerDecision(
                action="refuse",
                reason="State is already terminal.",
            )

        if not state.evidence_ids:
            return PlannerDecision(
                action="tool",
                selected_tool="hybrid_retrieve",
                reason="No evidence has been retrieved.",
            )

        if state.evidence_sufficient is None:
            return PlannerDecision(
                action="tool",
                selected_tool="check_evidence_sufficiency",
                reason="Retrieved evidence has not been assessed.",
            )

        if state.evidence_sufficient:
            return PlannerDecision(
                action="generate",
                reason="Current evidence is sufficient for grounded generation.",
            )

        if state.retrieval_attempt_count < state.maximum_retrieval_attempts:
            return PlannerDecision(
                action="tool",
                selected_tool="hybrid_retrieve",
                reason="Evidence is insufficient and retrieval budget remains.",
            )

        return PlannerDecision(
            action="refuse",
            reason="Evidence remains insufficient after the retrieval budget.",
        )
