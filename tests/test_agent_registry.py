"""Tests for the explicit Phase 36 agent tool registry."""

import pytest

from aeroragx.agent.registry import (
    AgentToolDefinition,
    AgentToolRegistry,
    build_default_agent_tool_registry,
)


def test_default_registry_contains_only_bounded_phase36_tools() -> None:
    registry = build_default_agent_tool_registry()

    assert registry.names() == (
        "hybrid_retrieve",
        "fetch_source_context",
        "check_evidence_sufficiency",
        "validate_citations",
        "compare_sources",
    )


def test_registry_marks_hybrid_retrieval_as_retrieval_attempt() -> None:
    definition = build_default_agent_tool_registry().get("hybrid_retrieve")

    assert definition.counts_as_retrieval_attempt is True


def test_registry_rejects_duplicate_definitions() -> None:
    definition = AgentToolDefinition(
        name="hybrid_retrieve",
        category="retrieval",
        description="Retrieve evidence.",
        counts_as_retrieval_attempt=True,
    )

    with pytest.raises(ValueError, match="Duplicate agent tool definition"):
        AgentToolRegistry([definition, definition])
