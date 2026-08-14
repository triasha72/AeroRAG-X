"""Validated bounded state contract for the future stateful AeroRAG-X agent."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.agent.contracts import AgentToolName, ToolCallRecord

AgentTerminationReason = Literal[
    "answer_completed",
    "grounded_refusal",
    "insufficient_evidence",
    "tool_budget_exhausted",
    "step_budget_exhausted",
    "human_review_required",
    "unrecoverable_tool_failure",
    "citation_validation_failure",
]


class AgentFailureRecord(BaseModel):
    """One structured failure preserved in agent state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    step_number: int = Field(ge=0)
    tool_name: AgentToolName | None = None
    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=500)


class AgentState(BaseModel):
    """State and explicit budgets shared by future LangGraph agent nodes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    original_query: str = Field(min_length=1)
    current_query: str = Field(min_length=1)

    step_number: int = Field(default=0, ge=0)
    maximum_steps: int = Field(default=12, ge=1)

    tool_call_count: int = Field(default=0, ge=0)
    maximum_tool_calls: int = Field(default=8, ge=1)

    retrieval_attempt_count: int = Field(default=0, ge=0)
    maximum_retrieval_attempts: int = Field(default=3, ge=1)

    selected_tool: AgentToolName | None = None
    tool_history: list[ToolCallRecord] = Field(default_factory=list)

    evidence_ids: list[str] = Field(default_factory=list)
    document_ids: list[int] = Field(default_factory=list)
    evidence_sufficient: bool | None = None

    previous_failures: list[AgentFailureRecord] = Field(default_factory=list)

    human_review_required: bool = False
    termination_reason: AgentTerminationReason | None = None

    @model_validator(mode="after")
    def validate_state_invariants(self) -> Self:
        """Protect state budgets and deterministic evidence identity."""

        if self.step_number > self.maximum_steps:
            raise ValueError("step_number cannot exceed maximum_steps.")
        if self.tool_call_count > self.maximum_tool_calls:
            raise ValueError("tool_call_count cannot exceed maximum_tool_calls.")
        if self.retrieval_attempt_count > self.maximum_retrieval_attempts:
            raise ValueError("retrieval_attempt_count cannot exceed maximum_retrieval_attempts.")
        if self.tool_call_count != len(self.tool_history):
            raise ValueError("tool_call_count must equal the number of tool_history records.")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique.")
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("document_ids must be unique.")
        if self.human_review_required and self.termination_reason not in (
            None,
            "human_review_required",
        ):
            raise ValueError(
                "human_review_required cannot be combined with an unrelated termination reason."
            )
        return self

    def advance_step(
        self,
        *,
        selected_tool: AgentToolName | None = None,
    ) -> Self:
        """Return a revalidated state advanced by exactly one graph step."""

        if self.step_number >= self.maximum_steps:
            raise ValueError("Agent step budget is exhausted.")

        return self._validated_update(
            {
                "step_number": self.step_number + 1,
                "selected_tool": selected_tool,
            }
        )

    def record_tool_call(
        self,
        call: ToolCallRecord,
        *,
        retrieval_attempt: bool = False,
        evidence_ids: list[str] | None = None,
        document_ids: list[int] | None = None,
    ) -> Self:
        """Return state with one completed tool call and optional new evidence."""

        if self.tool_call_count >= self.maximum_tool_calls:
            raise ValueError("Agent tool-call budget is exhausted.")

        next_retrieval_count = self.retrieval_attempt_count + int(retrieval_attempt)
        if next_retrieval_count > self.maximum_retrieval_attempts:
            raise ValueError("Agent retrieval-attempt budget is exhausted.")

        next_evidence_ids = _merge_unique(
            self.evidence_ids,
            evidence_ids or [],
        )
        next_document_ids = _merge_unique_int(
            self.document_ids,
            document_ids or [],
        )

        next_failures = list(self.previous_failures)
        if call.status == "error":
            if call.error is None:
                raise ValueError("Failed tool calls require structured error metadata.")
            next_failures.append(
                AgentFailureRecord(
                    step_number=self.step_number,
                    tool_name=call.tool_name,
                    error_code=call.error.code,
                    message=call.error.message,
                )
            )

        return self._validated_update(
            {
                "tool_call_count": self.tool_call_count + 1,
                "retrieval_attempt_count": next_retrieval_count,
                "tool_history": [*self.tool_history, call],
                "evidence_ids": next_evidence_ids,
                "document_ids": next_document_ids,
                "previous_failures": next_failures,
                "selected_tool": call.tool_name,
            }
        )

    def terminate(self, reason: AgentTerminationReason) -> Self:
        """Return a terminal state with a validated termination reason."""

        return self._validated_update(
            {
                "termination_reason": reason,
                "human_review_required": reason == "human_review_required",
            }
        )

    def _validated_update(self, updates: dict[str, object]) -> Self:
        payload = self.model_dump(mode="python")
        payload.update(updates)
        return self.__class__.model_validate(payload)


def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    return list(dict.fromkeys([*existing, *incoming]))


def _merge_unique_int(existing: list[int], incoming: list[int]) -> list[int]:
    return list(dict.fromkeys([*existing, *incoming]))
