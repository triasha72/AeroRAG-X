"""Tests for Phase 40 trajectory metrics."""

from aeroragx.agent.graph import AgentRunResult
from aeroragx.agent.state import AgentState
from aeroragx.evaluation.agent_metrics import evaluate_agent_trajectories
from aeroragx.evaluation.agent_trajectory import (
    AgentTrajectoryCase,
    AgentTrajectoryObservation,
)


def test_metrics_score_expected_terminal_state() -> None:
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
        termination_reason="grounded_refusal",
    )
    observation = AgentTrajectoryObservation(
        case=AgentTrajectoryCase(
            case_id="c1",
            category="unsupported",
            query="q",
            answerable=False,
            expected_termination="grounded_refusal",
            maximum_tool_calls=0,
        ),
        run=AgentRunResult(state=state),
        latency_ms=10.0,
    )
    metrics = evaluate_agent_trajectories([observation])

    assert metrics.termination_accuracy == 1.0
    assert metrics.safe_refusal_accuracy == 1.0
