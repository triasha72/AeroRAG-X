"""Tests for assistant-only LoRA tokenization."""

from pathlib import Path

from transformers import (
    AutoTokenizer,
)

from aeroragx.generation.prompting import (
    load_provider_hardening_config,
)
from aeroragx.training.dataset import (
    load_training_examples,
)
from aeroragx.training.tokenization import (
    tokenize_assistant_only,
)


def test_real_qwen_assistant_only_tokenization() -> None:
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")

    provider_config = load_provider_hardening_config(Path("configs/provider_v0_1.yaml"))

    examples = load_training_examples(
        Path("data/training/splits/aeroragx_lora_v0_1_train_eligible.jsonl")
    )

    example = examples[0]

    result = tokenize_assistant_only(
        example,
        tokenizer=tokenizer,
        provider_config=(provider_config),
        max_sequence_tokens=4096,
    )

    assert result.sequence_tokens > result.supervised_tokens > 0

    assert len(result.input_ids) == len(result.labels)

    assert len(result.input_ids) == len(result.attention_mask)

    assert all(label == -100 for label in result.labels[: result.assistant_start_token])

    assert all(label != -100 for label in result.labels[result.assistant_start_token :])
