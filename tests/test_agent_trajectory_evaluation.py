"""Tests for frozen Phase 40 case validation."""

from aeroragx.evaluation.agent_trajectory import AgentTrajectoryCase


def test_case_preserves_required_tool_contract() -> None:
    case = AgentTrajectoryCase(
        case_id="c1",
        category="source_comparison",
        query="Compare two sources.",
        answerable=True,
        required_tools=["hybrid_retrieve", "compare_sources"],
        expected_termination="answer_completed",
        maximum_tool_calls=5,
    )
    assert "compare_sources" in case.required_tools
