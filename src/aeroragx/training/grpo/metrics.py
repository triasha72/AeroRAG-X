"""Simple aggregate reward diagnostics."""

from pydantic import BaseModel, ConfigDict, Field


class RewardDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rollout_count: int = Field(ge=1)
    mean_reward: float
    minimum_reward: float
    maximum_reward: float


def summarize_rewards(rewards: list[float]) -> RewardDiagnostics:
    if not rewards:
        raise ValueError("Reward diagnostics require at least one reward.")
    return RewardDiagnostics(
        rollout_count=len(rewards),
        mean_reward=sum(rewards) / len(rewards),
        minimum_reward=min(rewards),
        maximum_reward=max(rewards),
    )
