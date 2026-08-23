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


def training_argument_values(config: GRPOExperimentConfig, output_dir: Path) -> dict[str, object]:
    """Build the explicit, testable TRL argument set."""

    if config.per_device_train_batch_size % config.num_generations:
        raise ValueError("per_device_train_batch_size must be divisible by num_generations")
    return {
        "output_dir": str(output_dir),
        "max_steps": config.max_steps,
        "num_generations": config.num_generations,
        "per_device_train_batch_size": config.per_device_train_batch_size,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "max_completion_length": config.max_completion_length,
        "learning_rate": config.learning_rate,
        "logging_steps": config.logging_steps,
        "save_steps": config.save_steps,
        "save_total_limit": config.save_total_limit,
        "fp16": config.fp16,
        "bf16": config.bf16,
        "gradient_checkpointing": config.gradient_checkpointing,
        "optim": config.optim,
        "seed": config.seed,
        "report_to": "none",
        "chat_template_kwargs": {"enable_thinking": False},
        "max_tool_calling_iterations": config.maximum_tool_calls,
    }


def latest_checkpoint(output_dir: Path) -> Path | None:
    """Return the numerically latest Transformers checkpoint, if present."""

    checkpoints = []
    for path in output_dir.glob("checkpoint-*"):
        try:
            checkpoints.append((int(path.name.removeprefix("checkpoint-")), path))
        except ValueError:
            continue
    return max(checkpoints, default=(0, None))[1]


def run_grpo_training(
    *,
    cases: list[GroundedAgentTrainingCase],
    config: GRPOExperimentConfig,
    output_dir: Path,
    resume_from_checkpoint: Path | None = None,
) -> Path | None:
    """Run TRL GRPOTrainer only when explicitly invoked by the training script."""

    try:
        import torch
        from peft import LoraConfig
        from transformers import BitsAndBytesConfig
        from trl.trainer.grpo_config import GRPOConfig
        from trl.trainer.grpo_trainer import GRPOTrainer
    except ImportError as exc:
        raise RuntimeError('TRL is required. Install with: pip install -e ".[rl]"') from exc

    training_args = GRPOConfig(  # type: ignore[arg-type]
        **training_argument_values(config, output_dir)
    )
    quantization_config = None
    if config.quantization_4bit:
        quantization_config = BitsAndBytesConfig(  # type: ignore[no-untyped-call]
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    peft_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=config.lora_target_modules,
    )

    trainer = GRPOTrainer(
        model=config.model_id,
        args=training_args,
        quantization_config=quantization_config,
        peft_config=peft_config,
        environment_factory=build_environment_factory(cases, config),
    )
    resume_path = str(resume_from_checkpoint) if resume_from_checkpoint else None
    trainer.train(resume_from_checkpoint=resume_path)
    trainer.save_model(str(output_dir / "final_adapter"))
    return latest_checkpoint(output_dir)
