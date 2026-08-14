"""Execution contracts for stateful agent tools and grounded generation."""

from __future__ import annotations

from typing import Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.agent.contracts import AgentToolName, ToolCallRecord
from aeroragx.agent.state import AgentState


class ToolExecutionResult(BaseModel):
    """State updates returned by one registered tool execution."""

    model_config = ConfigDict(extra="forbid")

    call: ToolCallRecord
    evidence_ids: list[str] = Field(default_factory=list)
    document_ids: list[int] = Field(default_factory=list)
    evidence_sufficient: bool | None = None

    @model_validator(mode="after")
    def validate_unique_ids(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("ToolExecutionResult evidence_ids must be unique.")
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("ToolExecutionResult document_ids must be unique.")
        return self


class GenerationResult(BaseModel):
    """Candidate grounded answer produced by the generation adapter."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    answer: str = Field(min_length=1)
    cited_evidence_ids: list[str] = Field(default_factory=list)


class CitationValidationResult(BaseModel):
    """Deterministic validation result for a generated answer."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    unknown_evidence_ids: list[str] = Field(default_factory=list)
    duplicate_evidence_ids: list[str] = Field(default_factory=list)


class AgentToolExecutor(Protocol):
    """Execute exactly one registered agent tool."""

    def execute(
        self,
        tool_name: AgentToolName,
        state: AgentState,
    ) -> ToolExecutionResult:
        """Execute the selected tool and return typed updates."""

        ...


class AgentGenerator(Protocol):
    """Generate a grounded answer from the current validated state."""

    def generate(self, state: AgentState) -> GenerationResult:
        """Generate a candidate answer."""

        ...


class AgentCitationValidator(Protocol):
    """Validate generated evidence references against the current state."""

    def validate(
        self,
        generation: GenerationResult,
        state: AgentState,
    ) -> CitationValidationResult:
        """Validate candidate citations."""

        ...
