"""Regression tests against obvious reward-hacking patterns."""

from aeroragx.training.grpo.config import RewardWeights
from aeroragx.training.grpo.rewards import (
    GroundedRewardInput,
    score_grounded_rollout,
)


def test_fake_citation_caps_reward() -> None:
    weights = RewardWeights()
    score = score_grounded_rollout(
        GroundedRewardInput(
            answerable=True,
            answered=True,
            refused=False,
            answer_correct=True,
            citation_valid=False,
            evidence_supported=True,
            structured_output_valid=True,
            required_tool_selected=True,
            tool_call_count=1,
            necessary_tool_calls=1,
        ),
        weights=weights,
    )
    assert score.total <= weights.structured_output


def test_unnecessary_tools_are_penalized() -> None:
    weights = RewardWeights(unnecessary_tool_penalty=0.5)
    efficient = score_grounded_rollout(
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
        weights=weights,
    )
    wasteful = score_grounded_rollout(
        GroundedRewardInput(
            answerable=True,
            answered=True,
            refused=False,
            answer_correct=True,
            citation_valid=True,
            evidence_supported=True,
            structured_output_valid=True,
            required_tool_selected=True,
            tool_call_count=5,
            necessary_tool_calls=2,
        ),
        weights=weights,
    )
    assert wasteful.total < efficient.total
