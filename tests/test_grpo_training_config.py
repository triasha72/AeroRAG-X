"""Tests for environment-factory construction without starting training."""

from aeroragx.training.grpo.config import GRPOExperimentConfig
from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.trainer import build_environment_factory


def test_factory_returns_fresh_environment_instances() -> None:
    factory = build_environment_factory(
        [
            GroundedAgentTrainingCase(
                case_id="c1",
                query="q",
                answerable=False,
            )
        ],
        GRPOExperimentConfig(),
    )
    assert factory() is not factory()
