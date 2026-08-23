"""Tests for environment-factory construction without starting training."""

from pathlib import Path

import pytest

from aeroragx.training.grpo.config import GRPOExperimentConfig
from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.trainer import (
    build_environment_factory,
    latest_checkpoint,
    training_argument_values,
)


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


def test_kaggle_argument_values_are_explicit() -> None:
    config = GRPOExperimentConfig(
        num_generations=2,
        per_device_train_batch_size=2,
        fp16=True,
        quantization_4bit=True,
    )
    values = training_argument_values(config, Path("out"))
    assert values["per_device_train_batch_size"] == 2
    assert values["fp16"] is True


def test_batch_size_must_be_divisible_by_generation_count() -> None:
    config = GRPOExperimentConfig(num_generations=4, per_device_train_batch_size=2)
    with pytest.raises(ValueError, match="divisible"):
        training_argument_values(config, Path("out"))


def test_latest_checkpoint_uses_numeric_order(tmp_path: Path) -> None:
    (tmp_path / "checkpoint-9").mkdir()
    expected = tmp_path / "checkpoint-10"
    expected.mkdir()
    (tmp_path / "checkpoint-bad").mkdir()
    assert latest_checkpoint(tmp_path) == expected
