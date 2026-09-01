"""Train the AeroRAG-X grounded Qwen3 LoRA adapter."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import random
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import accelerate
import peft
import torch
import transformers
import yaml
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

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG = REPO_ROOT / "configs/training/lora_v0_1.yaml"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--smoke",
        action="store_true",
        help=("Run one short end-to-end training-script validation."),
    )

    parser.add_argument(
        "--base-model",
        type=Path,
        default=None,
        help="Use a checksum-pinned local base-model directory without changing the frozen config.",
    )

    parser.add_argument(
        "--adapter-output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def utc_now() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def sha256_file(
    path: Path,
) -> str:
    """Compute one file SHA-256."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def git_head() -> str | None:
    """Return the current Git commit."""

    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def repo_path(
    value: str,
) -> Path:
    """Resolve a repository-relative path."""

    path = Path(value)

    if path.is_absolute():
        return path

    return REPO_ROOT / path


def load_config(
    path: Path,
) -> dict[str, Any]:
    """Load and validate the experiment config."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError("LoRA configuration must be a mapping.")

    return payload


def encode_dataset(
    path: Path,
    *,
    tokenizer: Any,
    provider_config: Any,
    max_sequence_tokens: int,
) -> list[
    tuple[
        str,
        AssistantOnlyTokenization,
    ]
]:
    """Load and tokenize one dataset."""

    examples = load_training_examples(path)

    encoded = []

    for example in examples:
        tokenized = tokenize_assistant_only(
            example,
            tokenizer=tokenizer,
            provider_config=(provider_config),
            max_sequence_tokens=(max_sequence_tokens),
        )

        encoded.append(
            (
                example.example_id,
                tokenized,
            )
        )

    return encoded


def select_spread(
    rows: list[
        tuple[
            str,
            AssistantOnlyTokenization,
        ]
    ],
    count: int,
) -> list[
    tuple[
        str,
        AssistantOnlyTokenization,
    ]
]:
    """Select examples spanning sequence lengths."""

    if count >= len(rows):
        return list(rows)

    ordered = sorted(
        rows,
        key=lambda item: (
            item[1].sequence_tokens,
            item[0],
        ),
    )

    if count == 1:
        return [ordered[len(ordered) // 2]]

    indices = [round(position * (len(ordered) - 1) / (count - 1)) for position in range(count)]

    selected = [ordered[index] for index in indices]

    if len(selected) != count:
        raise RuntimeError("Smoke selection count mismatch.")

    return selected


def make_tensors(
    tokenized: AssistantOnlyTokenization,
    *,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    """Create one batch of size one."""

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
def evaluate_token_loss(
    model: Any,
    rows: list[
        tuple[
            str,
            AssistantOnlyTokenization,
        ]
    ],
    *,
    device: torch.device,
) -> float:
    """Evaluate token-weighted assistant loss."""

    model.eval()

    total_negative_log_likelihood = 0.0
    total_tokens = 0

    for position, (example_id, tokenized) in enumerate(rows, start=1):
        batch = make_tensors(
            tokenized,
            device=device,
        )

        outputs = model(**batch)

        loss_value = float(outputs.loss.detach().cpu())

        if not math.isfinite(loss_value):
            raise RuntimeError("Evaluation produced non-finite loss.")

        supervised_tokens = tokenized.supervised_tokens

        total_negative_log_likelihood += loss_value * supervised_tokens

        total_tokens += supervised_tokens

        # MPS retains freed allocations in its caching allocator. Explicitly
        # release each variable-length evaluation batch so a sequence of dev
        # examples cannot accumulate enough cached memory for macOS jetsam to
        # terminate the process. This changes only memory lifecycle, not the
        # evaluated examples, token limit, precision, or loss calculation.
        del outputs
        del batch

        if device.type == "mps":
            torch.mps.empty_cache()

        print(
            "evaluation",
            f"example={position}/{len(rows)}",
            f"id={example_id}",
            f"loss={loss_value:.6f}",
        )

    if total_tokens <= 0:
        raise RuntimeError("Evaluation had zero supervised tokens.")

    return total_negative_log_likelihood / total_tokens


def save_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    """Write a deterministic JSON report."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Run the LoRA experiment."""

    args = parse_args()

    config_path = args.config.resolve()

    config = load_config(config_path)

    training = config["training"]
    lora = config["lora"]
    dataset = config["dataset"]
    outputs = config["outputs"]

    if training["status"] != "ready_for_training":
        raise RuntimeError("Training config is not marked ready_for_training.")

    if training["per_device_batch_size"] != 1:
        raise RuntimeError("This MPS training path requires batch size 1.")

    if training["device"] != "mps":
        raise RuntimeError("This experiment is configured for MPS.")

    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS is unavailable.")

    seed = int(training["seed"])

    random.seed(seed)
    torch.manual_seed(seed)

    device = torch.device("mps")

    torch.mps.empty_cache()

    base_model_name = str(
        args.base_model.resolve() if args.base_model is not None else config["base_model"]
    )

    train_path = repo_path(dataset["train_input"])

    dev_path = repo_path(dataset["dev_input"])

    provider_config_path = repo_path(config["provider_config"]["path"])

    max_sequence_tokens = int(training["max_sequence_tokens"])

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    provider_config = load_provider_hardening_config(provider_config_path)

    print()
    print("Tokenizing training set...")

    train_rows = encode_dataset(
        train_path,
        tokenizer=tokenizer,
        provider_config=(provider_config),
        max_sequence_tokens=(max_sequence_tokens),
    )

    print("Tokenizing dev set...")

    dev_rows = encode_dataset(
        dev_path,
        tokenizer=tokenizer,
        provider_config=(provider_config),
        max_sequence_tokens=(max_sequence_tokens),
    )

    if len(train_rows) != 106:
        raise RuntimeError(f"Expected 106 training examples, got {len(train_rows)}.")

    if len(dev_rows) != 12:
        raise RuntimeError(f"Expected 12 dev examples, got {len(dev_rows)}.")

    epochs = int(training["epochs"])

    gradient_accumulation_steps = int(training["gradient_accumulation_steps"])

    if args.smoke:
        train_rows = select_spread(
            train_rows,
            8,
        )

        dev_rows = select_spread(
            dev_rows,
            4,
        )

        epochs = 1

        gradient_accumulation_steps = min(
            4,
            gradient_accumulation_steps,
        )

        adapter_path = REPO_ROOT / "artifacts/training/adapters/aeroragx_lora_v0_1_smoke"

        report_path = REPO_ROOT / "artifacts/evaluation/aeroragx_lora_training_smoke_v0_1.json"

    else:
        adapter_path = (
            args.adapter_output.resolve()
            if args.adapter_output is not None
            else repo_path(outputs["best_adapter"])
        )

        report_path = (
            args.report_output.resolve()
            if args.report_output is not None
            else repo_path(outputs["report"])
        )

    if adapter_path.exists():
        shutil.rmtree(adapter_path)

    model: Any = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        dtype=torch.float16,
    )

    model.config.use_cache = False

    if bool(training["gradient_checkpointing"]):
        model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={
                "use_reentrant": False,
            }
        )

    lora_bias_value = str(lora["bias"])

    if lora_bias_value not in {
        "none",
        "all",
        "lora_only",
    }:
        raise ValueError(f"Invalid LoRA bias setting: {lora_bias_value!r}.")

    lora_bias = cast(
        Literal[
            "none",
            "all",
            "lora_only",
        ],
        lora_bias_value,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=int(lora["rank"]),
        lora_alpha=int(lora["alpha"]),
        lora_dropout=float(lora["dropout"]),
        bias=lora_bias,
        target_modules=list(lora["target_modules"]),
    )

    model = get_peft_model(
        model,
        lora_config,
    )

    model.to(device)

    trainable_parameters = [
        parameter for parameter in model.parameters() if parameter.requires_grad
    ]

    trainable_count = sum(parameter.numel() for parameter in trainable_parameters)

    total_count = sum(parameter.numel() for parameter in model.parameters())

    optimizer = torch.optim.AdamW(
        trainable_parameters,
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )

    expected_optimizer_steps = math.ceil(len(train_rows) / gradient_accumulation_steps) * epochs

    report: dict[str, Any] = {
        "version": "0.1",
        "status": "running",
        "smoke": args.smoke,
        "started_at_utc": utc_now(),
        "experiment_name": config["experiment_name"],
        "base_model": base_model_name,
        "git_commit": git_head(),
        "config": {
            "path": str(config_path.relative_to(REPO_ROOT)),
            "sha256": sha256_file(config_path),
        },
        "environment": {
            "torch": str(torch.__version__),
            "transformers": transformers.__version__,
            "peft": peft.__version__,
            "accelerate": accelerate.__version__,
            "device": "mps",
            "dtype": "float16",
        },
        "dataset": {
            "train_path": str(train_path.relative_to(REPO_ROOT)),
            "train_sha256": sha256_file(train_path),
            "train_examples": len(train_rows),
            "dev_path": str(dev_path.relative_to(REPO_ROOT)),
            "dev_sha256": sha256_file(dev_path),
            "dev_examples": len(dev_rows),
        },
        "training": {
            "epochs": epochs,
            "learning_rate": float(training["learning_rate"]),
            "weight_decay": float(training["weight_decay"]),
            "per_device_batch_size": 1,
            "gradient_accumulation_steps": gradient_accumulation_steps,
            "gradient_checkpointing": bool(training["gradient_checkpointing"]),
            "gradient_clip_norm": float(training["gradient_clip_norm"]),
            "expected_optimizer_steps": expected_optimizer_steps,
        },
        "lora": {
            "rank": int(lora["rank"]),
            "alpha": int(lora["alpha"]),
            "dropout": float(lora["dropout"]),
            "bias": str(lora["bias"]),
            "target_modules": list(lora["target_modules"]),
            "trainable_parameters": trainable_count,
            "total_parameters": total_count,
            "trainable_fraction": (trainable_count / total_count),
        },
        "epochs": [],
    }

    print()
    print("=== FULL LORA TRAINING ===")

    print(
        "Smoke:",
        args.smoke,
    )

    print(
        "Train examples:",
        len(train_rows),
    )

    print(
        "Dev examples:",
        len(dev_rows),
    )

    print(
        "Epochs:",
        epochs,
    )

    print(
        "Gradient accumulation:",
        gradient_accumulation_steps,
    )

    print(
        "Expected optimizer steps:",
        expected_optimizer_steps,
    )

    print(
        "Trainable parameters:",
        trainable_count,
    )

    print(
        "Total parameters:",
        total_count,
    )

    print()
    print("Evaluating initial dev loss...")

    initial_dev_loss = evaluate_token_loss(
        model,
        dev_rows,
        device=device,
    )

    report["initial_dev_token_loss"] = initial_dev_loss

    print(
        "Initial dev token loss:",
        initial_dev_loss,
    )

    best_dev_loss = math.inf
    best_epoch = 0
    optimizer_steps = 0

    for epoch_index in range(epochs):
        epoch_number = epoch_index + 1

        model.train()

        indices = list(range(len(train_rows)))

        epoch_rng = random.Random(seed + epoch_number)

        epoch_rng.shuffle(indices)

        optimizer.zero_grad(set_to_none=True)

        window_supervised_tokens = 0
        microbatches_in_window = 0

        epoch_nll = 0.0
        epoch_tokens = 0

        print()
        print(f"=== EPOCH {epoch_number}/{epochs} ===")

        for position, row_index in enumerate(
            indices,
            start=1,
        ):
            (
                example_id,
                tokenized,
            ) = train_rows[row_index]

            outputs = model(
                **make_tensors(
                    tokenized,
                    device=device,
                )
            )

            loss = outputs.loss

            loss_value = float(loss.detach().cpu())

            if not math.isfinite(loss_value):
                raise RuntimeError(f"{example_id}: non-finite loss.")

            supervised_tokens = tokenized.supervised_tokens

            (loss * supervised_tokens).backward()

            window_supervised_tokens += supervised_tokens

            microbatches_in_window += 1

            epoch_nll += loss_value * supervised_tokens

            epoch_tokens += supervised_tokens

            is_window_end = microbatches_in_window >= gradient_accumulation_steps

            is_epoch_end = position == len(indices)

            if is_window_end or is_epoch_end:
                if window_supervised_tokens <= 0:
                    raise RuntimeError("Gradient window contains no tokens.")

                for parameter in trainable_parameters:
                    if parameter.grad is not None:
                        parameter.grad.div_(window_supervised_tokens)

                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    trainable_parameters,
                    max_norm=float(training["gradient_clip_norm"]),
                )

                gradient_norm_value = float(gradient_norm.detach().cpu())

                if not math.isfinite(gradient_norm_value):
                    raise RuntimeError("Non-finite gradient norm.")

                optimizer.step()

                optimizer.zero_grad(set_to_none=True)

                optimizer_steps += 1

                window_supervised_tokens = 0
                microbatches_in_window = 0

            if position == 1 or position % 10 == 0 or is_epoch_end:
                print(
                    f"epoch={epoch_number}",
                    f"example={position}/{len(indices)}",
                    f"id={example_id}",
                    f"loss={loss_value:.6f}",
                    f"optimizer_steps={optimizer_steps}",
                )

            del outputs
            del loss

        train_token_loss = epoch_nll / epoch_tokens

        print()
        print("Evaluating dev loss...")

        dev_token_loss = evaluate_token_loss(
            model,
            dev_rows,
            device=device,
        )

        epoch_record = {
            "epoch": epoch_number,
            "train_token_loss": train_token_loss,
            "dev_token_loss": dev_token_loss,
            "optimizer_steps": optimizer_steps,
            "train_supervised_tokens": epoch_tokens,
        }

        report["epochs"].append(epoch_record)

        print()
        print(
            "Epoch train token loss:",
            train_token_loss,
        )

        print(
            "Epoch dev token loss:",
            dev_token_loss,
        )

        if dev_token_loss < best_dev_loss:
            best_dev_loss = dev_token_loss

            best_epoch = epoch_number

            if adapter_path.exists():
                shutil.rmtree(adapter_path)

            model.save_pretrained(
                adapter_path,
                safe_serialization=True,
            )

            print(
                "Saved new best adapter:",
                adapter_path,
            )

        report["best_epoch"] = best_epoch

        report["best_dev_token_loss"] = best_dev_loss

        report["optimizer_steps_completed"] = optimizer_steps

        save_json(
            report_path,
            report,
        )

        gc.collect()
        torch.mps.empty_cache()

    if optimizer_steps != expected_optimizer_steps:
        raise RuntimeError(
            "Optimizer-step count "
            "does not match expectation: "
            f"{optimizer_steps} vs "
            f"{expected_optimizer_steps}."
        )

    if not adapter_path.exists():
        raise RuntimeError("Best adapter was not saved.")

    print()
    print("Training complete.")

    print(
        "Best epoch:",
        best_epoch,
    )

    print(
        "Best dev token loss:",
        best_dev_loss,
    )

    del optimizer
    del model

    gc.collect()
    torch.mps.empty_cache()

    print()
    print("Reloading best adapter...")

    base_model: Any = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        dtype=torch.float16,
    )

    base_model.config.use_cache = False

    reloaded: Any = PeftModel.from_pretrained(
        base_model,
        adapter_path,
    )

    reloaded.to(device)

    reloaded_dev_loss = evaluate_token_loss(
        reloaded,
        dev_rows,
        device=device,
    )

    reload_difference = abs(reloaded_dev_loss - best_dev_loss)

    print(
        "Reloaded dev token loss:",
        reloaded_dev_loss,
    )

    print(
        "Reload difference:",
        reload_difference,
    )

    if reload_difference > 0.02:
        raise RuntimeError("Reloaded adapter differs too much from saved best.")

    report["status"] = "complete"

    report["completed_at_utc"] = utc_now()

    report["best_epoch"] = best_epoch

    report["best_dev_token_loss"] = best_dev_loss

    report["reloaded_best_dev_token_loss"] = reloaded_dev_loss

    report["reload_difference"] = reload_difference

    report["optimizer_steps_completed"] = optimizer_steps

    report["adapter_path"] = str(adapter_path.relative_to(REPO_ROOT))

    save_json(
        report_path,
        report,
    )

    print()
    print(
        "Report:",
        report_path,
    )

    print()
    print("FULL LORA TRAINING + BEST-ADAPTER RELOAD: PASS")


if __name__ == "__main__":
    main()
