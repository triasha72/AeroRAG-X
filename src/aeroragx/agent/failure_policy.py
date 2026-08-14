"""Explicit bounded failure and retry policy for agent tool execution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.agent.contracts import AgentToolName

FailureClass = Literal[
    "timeout",
    "service_error",
    "malformed_response",
    "unknown_evidence",
    "dependency_unavailable",
]


class ToolRetryRule(BaseModel):
    """Retry rule for one failure class."""

    model_config = ConfigDict(extra="forbid")

    failure_class: FailureClass
    maximum_retries: int = Field(ge=0, le=5)


class AgentFailurePolicy(BaseModel):
    """Versioned retry policy applied before graph-level refusal."""

    model_config = ConfigDict(extra="forbid")

    rules: dict[AgentToolName, list[ToolRetryRule]]

    def retries_for(
        self,
        tool_name: AgentToolName,
        failure_class: FailureClass,
    ) -> int:
        for rule in self.rules.get(tool_name, []):
            if rule.failure_class == failure_class:
                return rule.maximum_retries
        return 0
