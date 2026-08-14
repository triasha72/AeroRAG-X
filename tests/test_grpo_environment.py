"""Tests for the bounded tool-using GRPO environment."""

from aeroragx.services.contracts import ServiceEvidence
from aeroragx.training.grpo.config import RewardWeights
from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.environment import GroundedAgentEnvironment


def test_environment_rewards_grounded_submission() -> None:
    env = GroundedAgentEnvironment(
        cases=[
            GroundedAgentTrainingCase(
                case_id="c1",
                query="value?",
                answerable=True,
                evidence=[
                    ServiceEvidence(
                        evidence_id="e1",
                        document_id=1,
                        text="value is 42",
                        citation_url="https://example.invalid/1",
                    )
                ],
                reference_answer="42",
                expected_citation_ids=["e1"],
            )
        ],
        reward_weights=RewardWeights(),
    )
    assert env.reset() == "value?"
    env.retrieve()
    assert env.check_sufficiency() is True
    env.submit_answer("The value is 42.", ["e1"])
    assert env.get_reward() > 0
