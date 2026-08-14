"""GRPO reward and dataset contracts for grounded agent post-training."""

from aeroragx.training.grpo.config import GRPOExperimentConfig, RewardWeights
from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.rewards import (
    GroundedRewardInput,
    RewardBreakdown,
    score_grounded_rollout,
)
from aeroragx.training.grpo.rollout import GroundedRolloutRecord
from aeroragx.training.grpo.validation import validate_disjoint_case_ids

__all__ = [
    "GRPOExperimentConfig",
    "GroundedAgentTrainingCase",
    "GroundedRewardInput",
    "GroundedRolloutRecord",
    "RewardBreakdown",
    "RewardWeights",
    "score_grounded_rollout",
    "validate_disjoint_case_ids",
]
