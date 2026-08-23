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
    per_device_train_batch_size: int = Field(default=4, ge=1)
    gradient_accumulation_steps: int = Field(default=1, ge=1)
    max_completion_length: int = Field(default=256, ge=32)
    learning_rate: float = Field(default=5e-6, gt=0.0)
    logging_steps: int = Field(default=1, ge=1)
    save_steps: int = Field(default=10, ge=1)
    save_total_limit: int = Field(default=2, ge=1)
    fp16: bool = False
    bf16: bool = False
    gradient_checkpointing: bool = False
    optim: str = "adamw_torch"
    quantization_4bit: bool = False
    lora_r: int = Field(default=16, ge=1)
    lora_alpha: int = Field(default=32, ge=1)
    lora_dropout: float = Field(default=0.05, ge=0.0, lt=1.0)
    lora_target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    reward_weights: RewardWeights = Field(default_factory=RewardWeights)
