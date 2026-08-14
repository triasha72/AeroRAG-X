"""Lazy TRL integration for the bounded GRPO experiment."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aeroragx.training.grpo.config import GRPOExperimentConfig
from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.environment import GroundedAgentEnvironment


def build_environment_factory(
    cases: list[GroundedAgentTrainingCase],
    config: GRPOExperimentConfig,
) -> Callable[[], GroundedAgentEnvironment]:
    """Return a fresh environment factory for TRL rollouts."""

    def factory() -> GroundedAgentEnvironment:
        return GroundedAgentEnvironment(
            cases=cases,
            reward_weights=config.reward_weights,
        )

    return factory


def run_grpo_training(
    *,
    cases: list[GroundedAgentTrainingCase],
    config: GRPOExperimentConfig,
    output_dir: Path,
) -> None:
    """Run TRL GRPOTrainer only when explicitly invoked by the training script."""

    try:
        from trl.trainer.grpo_config import GRPOConfig
        from trl.trainer.grpo_trainer import GRPOTrainer
    except ImportError as exc:
        raise RuntimeError('TRL is required. Install with: pip install -e ".[rl]"') from exc

    training_args = GRPOConfig(
        output_dir=str(output_dir),
        max_steps=config.max_steps,
        num_generations=config.num_generations,
        seed=config.seed,
        report_to="none",
        chat_template_kwargs={"enable_thinking": False},
        max_tool_calling_iterations=config.maximum_tool_calls,
    )

    trainer = GRPOTrainer(
        model=config.model_id,
        args=training_args,
        environment_factory=build_environment_factory(cases, config),
    )
    trainer.train()
