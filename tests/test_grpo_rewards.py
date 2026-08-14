"""Tests for transparent multi-objective GRPO rewards."""

from aeroragx.training.grpo.config import RewardWeights
from aeroragx.training.grpo.rewards import (
    GroundedRewardInput,
    score_grounded_rollout,
)


def test_correct_grounded_answer_receives_positive_reward() -> None:
    score = score_grounded_rollout(
        GroundedRewardInput(
            answerable=True,
            answered=True,
            refused=False,
            answer_correct=True,
            citation_valid=True,
            evidence_supported=True,
            structured_output_valid=True,
            required_tool_selected=True,
            tool_call_count=2,
            necessary_tool_calls=2,
        ),
        weights=RewardWeights(),
    )
    assert score.total > 0


def test_unsupported_assertion_is_not_rewarded() -> None:
    score = score_grounded_rollout(
        GroundedRewardInput(
            answerable=False,
            answered=True,
            refused=False,
            answer_correct=False,
            citation_valid=True,
            evidence_supported=False,
            structured_output_valid=True,
            required_tool_selected=True,
            tool_call_count=1,
            necessary_tool_calls=1,
        ),
        weights=RewardWeights(),
    )
    assert score.total <= 0
