"""DeepSpeed ZeRO-3 treatment for the matched grounded-Qwen workload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

from aeroragx.generation.prompting import load_provider_hardening_config
from aeroragx.training.dataset import load_training_examples
from aeroragx.training.tokenization import tokenize_assistant_only

ROOT = Path(__file__).resolve().parents[1]


class TokenDataset(torch.utils.data.Dataset[dict[str, list[int]]]):
    def __init__(self, rows: list[dict[str, list[int]]]) -> None:
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.rows[index]


def collate(rows: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
    width = max(len(row["input_ids"]) for row in rows)
    padded: dict[str, list[list[int]]] = {"input_ids": [], "attention_mask": [], "labels": []}
    for row in rows:
        extra = width - len(row["input_ids"])
        padded["input_ids"].append(row["input_ids"] + [0] * extra)
        padded["attention_mask"].append(row["attention_mask"] + [0] * extra)
        padded["labels"].append(row["labels"] + [-100] * extra)
    return {name: torch.tensor(values, dtype=torch.long) for name, values in padded.items()}


def dataset(path: Path, *, tokenizer: Any, config: dict[str, Any]) -> TokenDataset:
    provider = load_provider_hardening_config(ROOT / config["provider_config"])
    rows = []
    for example in load_training_examples(path):
        encoded = tokenize_assistant_only(
            example,
            tokenizer=tokenizer,
            provider_config=provider,
            max_sequence_tokens=int(config["max_sequence_tokens"]),
        )
        rows.append({
            "input_ids": encoded.input_ids,
            "attention_mask": encoded.attention_mask,
            "labels": encoded.labels,
        })
    return TokenDataset(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=ROOT / "distributed_training/configs/fsdp_qwen_v0_1.yaml"
    )
    parser.add_argument(
        "--deepspeed-config",
        type=Path,
        default=ROOT / "distributed_training/configs/deepspeed_zero3_v0_1.json",
    )
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    json.loads(args.deepspeed_config.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"], use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(config["model_name"], torch_dtype=torch.bfloat16)
    if config["gradient_checkpointing"]:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False
    output = ROOT / "artifacts/training/deepspeed_zero3_v0_1"
    arguments = TrainingArguments(
        output_dir=str(output),
        num_train_epochs=float(config["epochs"]),
        max_steps=-1 if config["max_steps"] is None else int(config["max_steps"]),
        per_device_train_batch_size=int(config["per_device_batch_size"]),
        per_device_eval_batch_size=int(config["per_device_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        learning_rate=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
        bf16=True,
        logging_steps=int(config["logging"]["every_steps"]),
        save_steps=int(config["checkpoint"]["every_steps"]),
        eval_strategy="steps",
        eval_steps=int(config["checkpoint"]["every_steps"]),
        deepspeed=str(args.deepspeed_config),
        seed=int(config["seed"]),
        data_seed=int(config["seed"]),
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=dataset(ROOT / config["train_input"], tokenizer=tokenizer, config=config),
        eval_dataset=dataset(ROOT / config["validation_input"], tokenizer=tokenizer, config=config),
        data_collator=collate,
    )
    trainer.train(resume_from_checkpoint=config["checkpoint"]["resume_from"])
    metrics = trainer.evaluate()
    if trainer.is_world_process_zero():
        output.mkdir(parents=True, exist_ok=True)
        (output / "summary.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
