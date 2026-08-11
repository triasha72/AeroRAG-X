"""Tiny-overfit gate for the AeroRAG-X Qwen LoRA training path."""

from __future__ import annotations

import argparse
import gc
import json
import math
import random
from pathlib import Path
from typing import Any

import torch
from peft import (
    LoraConfig,
    PeftModel,
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

PROVIDER_CONFIG_PATH = Path("configs/provider_v0_1.yaml")

ADAPTER_PATH = Path("artifacts/training/adapters/aeroragx_lora_tiny_overfit_v0_1")

REPORT_PATH = Path("artifacts/evaluation/aeroragx_lora_tiny_overfit_v0_1.json")

SEED = 20260810


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--steps",
        type=int,
        default=32,
    )

    parser.add_argument(
        "--examples",
        type=int,
        default=4,
    )

    return parser.parse_args()


def make_tensors(
    tokenized: AssistantOnlyTokenization,
    *,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    """Convert one tokenized example into a batch of size one."""

    return {
        "input_ids": torch.tensor(
            [tokenized.input_ids],
            dtype=torch.long,
            device=device,
        ),
        "attention_mask": torch.tensor(
            [tokenized.attention_mask],
            dtype=torch.long,
            device=device,
        ),
        "labels": torch.tensor(
            [tokenized.labels],
            dtype=torch.long,
            device=device,
        ),
    }


@torch.no_grad()
def evaluate_mean_loss(
    model: Any,
    encoded: list[
        tuple[
            str,
            AssistantOnlyTokenization,
        ]
    ],
    *,
    device: torch.device,
) -> float:
    """Evaluate teacher-forced assistant-only loss."""

    model.eval()

    losses: list[float] = []

    for _, tokenized in encoded:
        outputs = model(
            **make_tensors(
                tokenized,
                device=device,
            )
        )

        value = float(outputs.loss.detach().cpu())

        if not math.isfinite(value):
            raise RuntimeError("Evaluation produced a non-finite loss.")

        losses.append(value)

    return sum(losses) / len(losses)


def main() -> None:
    """Run tiny-overfit training, save, and reload the adapter."""

    args = parse_args()

    if args.steps <= 0:
        raise ValueError("--steps must be positive.")

    if args.examples <= 0:
        raise ValueError("--examples must be positive.")

    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS is not available.")

    random.seed(SEED)
    torch.manual_seed(SEED)

    device = torch.device("mps")

    torch.mps.empty_cache()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    provider_config = load_provider_hardening_config(PROVIDER_CONFIG_PATH)

    examples = load_training_examples(TRAIN_PATH)

    encoded_all: list[
        tuple[
            str,
            AssistantOnlyTokenization,
        ]
    ] = []

    for example in examples:
        tokenized = tokenize_assistant_only(
            example,
            tokenizer=tokenizer,
            provider_config=provider_config,
            max_sequence_tokens=4096,
        )

        encoded_all.append(
            (
                example.example_id,
                tokenized,
            )
        )

    encoded_all.sort(
        key=lambda item: (
            item[1].sequence_tokens,
            item[0],
        )
    )

    selected = encoded_all[: args.examples]

    if len(selected) != args.examples:
        raise RuntimeError("Could not select requested tiny-overfit examples.")

    print()
    print("=== TINY OVERFIT DATA ===")

    for example_id, tokenized in selected:
        print(
            example_id,
            "sequence=",
            tokenized.sequence_tokens,
            "supervised=",
            tokenized.supervised_tokens,
        )

    model: Any = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16,
    )

    model.config.use_cache = False

    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={
            "use_reentrant": False,
        }
    )

    print()
    print(
        "Gradient checkpointing:",
        model.is_gradient_checkpointing,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
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

    model.to(device)

    trainable_parameters = [
        parameter for parameter in model.parameters() if parameter.requires_grad
    ]

    model.print_trainable_parameters()

    optimizer = torch.optim.AdamW(
        trainable_parameters,
        lr=2e-4,
    )

    initial_loss = evaluate_mean_loss(
        model,
        selected,
        device=device,
    )

    print()
    print(
        "Initial mean loss:",
        initial_loss,
    )

    history: list[float] = []

    for step in range(
        1,
        args.steps + 1,
    ):
        example_id, tokenized = selected[(step - 1) % len(selected)]

        model.train()

        optimizer.zero_grad(set_to_none=True)

        outputs = model(
            **make_tensors(
                tokenized,
                device=device,
            )
        )

        loss = outputs.loss

        value = float(loss.detach().cpu())

        if not math.isfinite(value):
            raise RuntimeError(f"Step {step}: non-finite loss.")

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            trainable_parameters,
            max_norm=1.0,
        )

        optimizer.step()

        history.append(value)

        if step == 1 or step % 4 == 0 or step == args.steps:
            print(
                f"step={step:02d}",
                f"example={example_id}",
                f"loss={value:.6f}",
            )

    final_loss = evaluate_mean_loss(
        model,
        selected,
        device=device,
    )

    reduction_fraction = (initial_loss - final_loss) / initial_loss

    print()
    print("=== TINY OVERFIT RESULT ===")

    print(
        "Initial mean loss:",
        initial_loss,
    )

    print(
        "Final mean loss:",
        final_loss,
    )

    print(
        "Loss reduction:",
        reduction_fraction,
    )

    if final_loss >= initial_loss:
        raise RuntimeError("Tiny-overfit loss did not decrease.")

    if reduction_fraction < 0.10:
        raise RuntimeError("Tiny-overfit loss decreased by less than 10%.")

    ADAPTER_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model.save_pretrained(
        ADAPTER_PATH,
        safe_serialization=True,
    )

    print()
    print(
        "Adapter saved:",
        ADAPTER_PATH,
    )

    del optimizer
    del model

    gc.collect()
    torch.mps.empty_cache()

    print()
    print("Reloading base model + adapter...")

    base_model: Any = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16,
    )

    base_model.config.use_cache = False

    reloaded: Any = PeftModel.from_pretrained(
        base_model,
        ADAPTER_PATH,
    )

    reloaded.to(device)

    reload_loss = evaluate_mean_loss(
        reloaded,
        selected,
        device=device,
    )

    print(
        "Reloaded mean loss:",
        reload_loss,
    )

    reload_difference = abs(reload_loss - final_loss)

    print(
        "Reload difference:",
        reload_difference,
    )

    if reload_difference > 0.02:
        raise RuntimeError("Reloaded adapter loss differs too much from pre-save loss.")

    report = {
        "version": "0.1",
        "base_model": MODEL_NAME,
        "seed": SEED,
        "device": "mps",
        "dtype": "float16",
        "steps": args.steps,
        "examples": [
            {
                "example_id": example_id,
                "sequence_tokens": tokenized.sequence_tokens,
                "supervised_tokens": tokenized.supervised_tokens,
            }
            for example_id, tokenized in selected
        ],
        "lora": {
            "rank": 16,
            "alpha": 32,
            "dropout": 0.05,
            "target_modules": [
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
            ],
        },
        "learning_rate": 2e-4,
        "gradient_checkpointing": True,
        "initial_mean_loss": initial_loss,
        "final_mean_loss": final_loss,
        "loss_reduction_fraction": reduction_fraction,
        "reload_mean_loss": reload_loss,
        "reload_difference": reload_difference,
        "step_losses": history,
        "adapter_path": str(ADAPTER_PATH),
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Report:",
        REPORT_PATH,
    )

    print()
    print("TINY OVERFIT + ADAPTER RELOAD: PASS")


if __name__ == "__main__":
    main()
