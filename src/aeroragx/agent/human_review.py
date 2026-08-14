"""Human-review interruption and decision contracts."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.agent.state import AgentState

HumanReviewDecision = Literal["approve", "reject", "edit"]


class HumanReviewRequest(BaseModel):
    """Persisted request for bounded human review."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    review_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)
    state: AgentState


class HumanReviewResponse(BaseModel):
    """One explicit decision used to resume or terminate a paused run."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    review_id: str = Field(min_length=1)
    decision: HumanReviewDecision
    edited_query: str | None = None
    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_edit(self) -> Self:
        if self.decision == "edit" and not self.edited_query:
            raise ValueError("Edit decisions require edited_query.")
        if self.decision != "edit" and self.edited_query is not None:
            raise ValueError("Only edit decisions may include edited_query.")
        return self
