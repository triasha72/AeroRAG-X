"""Explicit registry of tools allowed in the AeroRAG-X agent."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.agent.contracts import AgentToolName

ToolCategory = Literal[
    "retrieval",
    "evidence",
    "validation",
    "comparison",
]


class AgentToolDefinition(BaseModel):
    """Static capability metadata used by future planning and routing nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    name: AgentToolName
    category: ToolCategory
    description: str = Field(min_length=1)
    counts_as_retrieval_attempt: bool = False


class AgentToolRegistry:
    """Immutable-by-interface registry of explicitly allowed agent tools."""

    def __init__(self, definitions: Sequence[AgentToolDefinition]) -> None:
        by_name: dict[AgentToolName, AgentToolDefinition] = {}

        for definition in definitions:
            if definition.name in by_name:
                raise ValueError(f"Duplicate agent tool definition: {definition.name}.")
            by_name[definition.name] = definition

        if not by_name:
            raise ValueError("Agent tool registry must contain at least one tool.")

        self._definitions = by_name

    def get(self, name: AgentToolName) -> AgentToolDefinition:
        """Return one registered tool definition."""

        try:
            return self._definitions[name]
        except KeyError as exc:
            raise KeyError(f"Agent tool is not registered: {name}.") from exc

    def names(self) -> tuple[AgentToolName, ...]:
        """Return stable tool names in registration order."""

        return tuple(self._definitions)

    def definitions(self) -> tuple[AgentToolDefinition, ...]:
        """Return all registered definitions in stable order."""

        return tuple(self._definitions.values())


def build_default_agent_tool_registry() -> AgentToolRegistry:
    """Return the bounded Phase 36 tool registry."""

    return AgentToolRegistry(
        [
            AgentToolDefinition(
                name="hybrid_retrieve",
                category="retrieval",
                description=(
                    "Retrieve provenance-preserving aerospace evidence through "
                    "the existing hybrid retrieval stack."
                ),
                counts_as_retrieval_attempt=True,
            ),
            AgentToolDefinition(
                name="fetch_source_context",
                category="evidence",
                description=("Resolve known evidence identifiers to authoritative source context."),
            ),
            AgentToolDefinition(
                name="check_evidence_sufficiency",
                category="evidence",
                description=(
                    "Assess whether the current evidence is sufficient before generation."
                ),
            ),
            AgentToolDefinition(
                name="validate_citations",
                category="validation",
                description=(
                    "Reject unknown or duplicated evidence identifiers in candidate citations."
                ),
            ),
            AgentToolDefinition(
                name="compare_sources",
                category="comparison",
                description=(
                    "Compare evidence spanning multiple source documents without "
                    "removing provenance."
                ),
            ),
        ]
    )
