"""Bounded retry wrapper for registered agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep

from aeroragx.agent.contracts import AgentToolName
from aeroragx.agent.execution import AgentToolExecutor, ToolExecutionResult
from aeroragx.agent.failure_policy import AgentFailurePolicy, FailureClass
from aeroragx.agent.state import AgentState


@dataclass(slots=True)
class RetryingToolExecutor:
    """Retry structured tool failures according to an explicit policy."""

    executor: AgentToolExecutor
    policy: AgentFailurePolicy
    backoff_seconds: float = 0.0

    def execute(
        self,
        tool_name: AgentToolName,
        state: AgentState,
    ) -> ToolExecutionResult:
        attempt = 0
        while True:
            result = self.executor.execute(tool_name, state)
            if result.call.status == "success":
                return result

            failure_class = classify_error_message(
                "" if result.call.error is None else result.call.error.message
            )
            maximum_retries = self.policy.retries_for(
                tool_name,
                failure_class,
            )
            if attempt >= maximum_retries:
                return result

            attempt += 1
            if self.backoff_seconds > 0:
                sleep(self.backoff_seconds * attempt)


def classify_error_message(message: str) -> FailureClass:
    normalized = message.casefold()
    if "timeout" in normalized:
        return "timeout"
    if "malformed" in normalized or "invalid" in normalized:
        return "malformed_response"
    if "unavailable" in normalized or "connection" in normalized:
        return "dependency_unavailable"
    return "service_error"
