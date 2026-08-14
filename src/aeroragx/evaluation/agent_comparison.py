"""Comparison contract for deterministic, adaptive, and stateful agent baselines."""

from pydantic import BaseModel, ConfigDict

from aeroragx.evaluation.agent_metrics import AgentTrajectoryMetrics


class AgentOrchestratorComparison(BaseModel):
    """Metrics reported without assuming the stateful agent wins."""

    model_config = ConfigDict(extra="forbid")

    deterministic: AgentTrajectoryMetrics | None = None
    bounded_adaptive: AgentTrajectoryMetrics | None = None
    stateful_agent: AgentTrajectoryMetrics | None = None
