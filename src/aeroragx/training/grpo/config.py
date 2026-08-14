"""Validated configuration for bounded GRPO experiments."""

from pydantic import BaseModel, ConfigDict, Field


class RewardWeights(BaseModel):
    """Multi-objective reward weights."""

    model_config = ConfigDict(extra="forbid")

    supported_answer: float = Field(default=1.0, ge=0.0)
    refusal_correctness: float = Field(default=1.0, ge=0.0)
    citation_validity: float = Field(default=1.0, ge=0.0)
    evidence_support: float = Field(default=1.0, ge=0.0)
    structured_output: float = Field(default=0.25, ge=0.0)
    tool_selection: float = Field(default=0.5, ge=0.0)
    unnecessary_tool_penalty: float = Field(default=0.1, ge=0.0)


class GRPOExperimentConfig(BaseModel):
    """Small, reproducible post-training experiment configuration."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    model_id: str = "Qwen/Qwen3-0.6B"
    seed: int = 42
    max_steps: int = Field(default=100, ge=1)
    num_generations: int = Field(default=4, ge=2)
    maximum_tool_calls: int = Field(default=6, ge=1)
    reward_weights: RewardWeights = Field(default_factory=RewardWeights)
