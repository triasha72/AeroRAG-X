"""Run one real LoRA optimization step on Apple MPS."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import torch
from peft import (
    LoraConfig,
    TaskType,
    get_peft_model,
)
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

from aeroragx.generation.prompting import (
    load_provider_hardening_config,
)
from aeroragx.training.dataset import (
    load_training_examples,
)
from aeroragx.training.tokenization import (
    AssistantOnlyTokenization,
    tokenize_assistant_only,
)

MODEL_NAME = "Qwen/Qwen3-0.6B"

TRAIN_PATH = Path("data/training/splits/aeroragx_lora_v0_1_train_eligible.jsonl")


def parse_args() -> argparse.Namespace:
    """Parse smoke-test arguments."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--example",
        choices=[
            "shortest",
            "longest",
        ],
        default="shortest",
    )

    return parser.parse_args()


def main() -> None:
    """Run one LoRA optimization step."""

    args = parse_args()

    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS is not available.")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    provider_config = load_provider_hardening_config(Path("configs/provider_v0_1.yaml"))

    examples = load_training_examples(TRAIN_PATH)

    encoded: list[
        tuple[
            str,
            AssistantOnlyTokenization,
        ]
    ] = []

    for example in examples:
        tokenized = tokenize_assistant_only(
            example,
            tokenizer=tokenizer,
            provider_config=(provider_config),
            max_sequence_tokens=4096,
        )

        encoded.append(
            (
                example.example_id,
                tokenized,
            )
        )

    if args.example == "shortest":
        example_id, tokenized = min(
            encoded,
            key=lambda item: item[1].sequence_tokens,
        )

    else:
        example_id, tokenized = max(
            encoded,
            key=lambda item: item[1].sequence_tokens,
        )

    print()
    print("=== MPS LORA SMOKE ===")
    print(
        "Selection:",
        args.example,
    )
    print(
        "Example:",
        example_id,
    )
    print(
        "Sequence tokens:",
        tokenized.sequence_tokens,
    )
    print(
        "Supervised tokens:",
        tokenized.supervised_tokens,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16,
    )

    model.config.use_cache = False

    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={
            "use_reentrant": False,
        }
    )

    print(
        "Gradient checkpointing:",
        model.is_gradient_checkpointing,
    )

    lora_config = LoraConfig(
        task_type=(TaskType.CAUSAL_LM),
        inference_mode=False,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
        ],
    )

    model = get_peft_model(
        model,
        lora_config,
    )

    model.to(torch.device("mps"))

    model.train()

    trainable = {
        name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad
    }

    print(
        "Trainable parameter tensors:",
        len(trainable),
    )

    before = {name: parameter.detach().cpu().clone() for name, parameter in trainable.items()}

    optimizer = torch.optim.AdamW(
        list(trainable.values()),
        lr=2e-4,
    )

    input_ids = torch.tensor(
        [tokenized.input_ids],
        dtype=torch.long,
        device="mps",
    )

    attention_mask = torch.tensor(
        [tokenized.attention_mask],
        dtype=torch.long,
        device="mps",
    )

    labels = torch.tensor(
        [tokenized.labels],
        dtype=torch.long,
        device="mps",
    )

    optimizer.zero_grad(set_to_none=True)

    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        labels=labels,
    )

    loss = outputs.loss

    loss_value = float(loss.detach().cpu())

    print(
        "Loss:",
        loss_value,
    )

    if not math.isfinite(loss_value):
        raise RuntimeError("Loss is not finite.")

    loss.backward()

    gradient_squared = 0.0

    tensors_with_gradient = 0

    for parameter in trainable.values():
        if parameter.grad is None:
            continue

        gradient_squared += float(parameter.grad.detach().float().pow(2).sum().cpu())

        tensors_with_gradient += 1

    gradient_norm = math.sqrt(gradient_squared)

    print(
        "Tensors with gradient:",
        tensors_with_gradient,
    )
    print(
        "Gradient norm:",
        gradient_norm,
    )

    if tensors_with_gradient == 0 or not math.isfinite(gradient_norm) or gradient_norm <= 0.0:
        raise RuntimeError("LoRA gradients are missing or invalid.")

    optimizer.step()

    maximum_delta = 0.0
    maximum_delta_name = ""

    for name, parameter in trainable.items():
        delta = parameter.detach().cpu().sub(before[name]).abs().max().item()

        if delta > maximum_delta:
            maximum_delta = delta
            maximum_delta_name = name

    print(
        "Max adapter parameter delta:",
        maximum_delta,
    )
    print(
        "Largest-update parameter:",
        maximum_delta_name,
    )

    if maximum_delta <= 0.0:
        raise RuntimeError("No LoRA parameter changed after optimizer.step().")

    print()
    print("MPS LORA ONE-STEP SMOKE: PASS")


if __name__ == "__main__":
    main()
