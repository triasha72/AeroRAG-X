"""Tests for non-prescriptive orchestrator comparison."""

from aeroragx.evaluation.agent_comparison import AgentOrchestratorComparison


def test_comparison_allows_missing_baselines_until_recorded() -> None:
    comparison = AgentOrchestratorComparison()
    assert comparison.stateful_agent is None
