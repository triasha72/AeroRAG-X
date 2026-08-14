"""Frozen-case and observed-trajectory contracts for agent evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.agent.contracts import AgentToolName
from aeroragx.agent.graph import AgentRunResult
from aeroragx.agent.state import AgentTerminationReason

CaseCategory = Literal[
    "supported_single_source",
    "supported_multi_source",
    "unsupported",
    "ambiguous",
    "conflicting_evidence",
    "retrieval_retry",
    "source_comparison",
    "citation_failure",
    "dependency_failure",
    "budget_exhaustion",
    "human_review",
]


class AgentTrajectoryCase(BaseModel):
    """One frozen expected-behavior case."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    category: CaseCategory
    query: str = Field(min_length=1)
    answerable: bool
    required_tools: list[AgentToolName] = Field(default_factory=list)
    forbidden_tools: list[AgentToolName] = Field(default_factory=list)
    expected_termination: AgentTerminationReason
    maximum_tool_calls: int = Field(ge=0)
    notes: str | None = None


class AgentTrajectoryObservation(BaseModel):
    """One evaluated run paired to its frozen case."""

    model_config = ConfigDict(extra="forbid")

    case: AgentTrajectoryCase
    run: AgentRunResult
    latency_ms: float = Field(ge=0.0)
    retry_count: int = Field(default=0, ge=0)
    recovered_after_failure: bool = False
    human_review_triggered: bool = False
