"""Matched single-GPU/FSDP grounded fine-tuning experiment.

Launch baseline with ``python distributed_training/train_fsdp.py --no-fsdp`` and
two-GPU sharding with ``torchrun --standalone --nproc_per_node=2 ...``.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.distributed as dist
import yaml
from torch.distributed.fsdp import (
    FullyShardedDataParallel as FSDP,
)
from torch.distributed.fsdp import (
    MixedPrecision,
    ShardedStateDictConfig,
    StateDictType,
)
from torch.distributed.fsdp.wrap import size_based_auto_wrap_policy
from torch.utils.data import DataLoader, Dataset, DistributedSampler
from transformers import AutoModelForCausalLM, AutoTokenizer

from aeroragx.generation.prompting import load_provider_hardening_config
from aeroragx.training.dataset import load_training_examples
from aeroragx.training.tokenization import tokenize_assistant_only

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Context:
    rank: int
    local_rank: int
    world_size: int
    device: torch.device


class TokenDataset(Dataset[dict[str, list[int]]]):
    def __init__(self, rows: list[dict[str, list[int]]]) -> None:
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.rows[index]


def initialize_distributed() -> Context:
    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if not torch.cuda.is_available():
        raise RuntimeError("The controlled FSDP experiment requires CUDA.")
    torch.cuda.set_device(local_rank)
    if world_size > 1 and not dist.is_initialized():
        dist.init_process_group(backend="nccl")
    return Context(rank, local_rank, world_size, torch.device("cuda", local_rank))


def seed_everything(seed: int, rank: int) -> None:
    random.seed(seed + rank)
    np.random.seed(seed + rank)
    torch.manual_seed(seed + rank)
    torch.cuda.manual_seed_all(seed + rank)


def collate(rows: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
    width = max(len(row["input_ids"]) for row in rows)
    output: dict[str, list[list[int]]] = {"input_ids": [], "attention_mask": [], "labels": []}
    for row in rows:
        padding = width - len(row["input_ids"])
        output["input_ids"].append(row["input_ids"] + [0] * padding)
        output["attention_mask"].append(row["attention_mask"] + [0] * padding)
        output["labels"].append(row["labels"] + [-100] * padding)
    return {name: torch.tensor(value, dtype=torch.long) for name, value in output.items()}


def load_rows(config: dict[str, Any], tokenizer: Any, key: str) -> TokenDataset:
    examples = load_training_examples(ROOT / config[key])
    provider = load_provider_hardening_config(ROOT / config["provider_config"])
    rows = []
    for example in examples:
        encoded = tokenize_assistant_only(
            example,
            tokenizer=tokenizer,
            provider_config=provider,
            max_sequence_tokens=int(config["max_sequence_tokens"]),
        )
        rows.append(
            {
                "input_ids": encoded.input_ids,
                "attention_mask": encoded.attention_mask,
                "labels": encoded.labels,
            }
        )
    return TokenDataset(rows)


def precision_policy(name: str) -> tuple[torch.dtype, MixedPrecision]:
    dtype = torch.bfloat16 if name == "bf16" else torch.float16
    return dtype, MixedPrecision(param_dtype=dtype, reduce_dtype=dtype, buffer_dtype=dtype)


def reduce_sum(value: float, context: Context) -> float:
    tensor = torch.tensor(value, dtype=torch.float64, device=context.device)
    if context.world_size > 1:
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    return float(tensor.item())


@torch.no_grad()
def evaluate(model: Any, loader: DataLoader[Any], context: Context) -> float:
    model.eval()
    loss_sum = 0.0
    batches = 0
    for batch in loader:
        batch = {key: value.to(context.device) for key, value in batch.items()}
        loss_sum += float(model(**batch).loss.detach())
        batches += 1
    model.train()
    return reduce_sum(loss_sum, context) / max(1.0, reduce_sum(float(batches), context))


def save_checkpoint(
    model: Any,
    optimizer: torch.optim.Optimizer,
    *,
    directory: Path,
    step: int,
    context: Context,
    fsdp_enabled: bool,
) -> tuple[float, int]:
    started = time.perf_counter()
    target = directory / f"step_{step:08d}"
    if context.rank == 0:
        target.mkdir(parents=True, exist_ok=True)
    if context.world_size > 1:
        dist.barrier()
    if fsdp_enabled:
        from torch.distributed.checkpoint import FileSystemWriter, save

        with FSDP.state_dict_type(
            model,
            StateDictType.SHARDED_STATE_DICT,
            ShardedStateDictConfig(offload_to_cpu=True),
        ):
            state = {"model": model.state_dict(), "optimizer": optimizer.state_dict()}
            save(state, storage_writer=FileSystemWriter(str(target)))
    elif context.rank == 0:
        torch.save(
            {"model": model.state_dict(), "optimizer": optimizer.state_dict()},
            target / "checkpoint.pt",
        )
    if context.rank == 0:
        (target / "trainer_state.json").write_text(
            json.dumps({"step": step, "world_size": context.world_size}) + "\n",
            encoding="utf-8",
        )
    if context.world_size > 1:
        dist.barrier()
    size = sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
    return time.perf_counter() - started, size


def load_checkpoint(
    model: Any,
    optimizer: torch.optim.Optimizer,
    *,
    directory: Path,
    context: Context,
    fsdp_enabled: bool,
) -> int:
    state_meta = json.loads((directory / "trainer_state.json").read_text(encoding="utf-8"))
    if fsdp_enabled:
        from torch.distributed.checkpoint import FileSystemReader, load

        with FSDP.state_dict_type(
            model,
            StateDictType.SHARDED_STATE_DICT,
            ShardedStateDictConfig(offload_to_cpu=True),
        ):
            state = {"model": model.state_dict(), "optimizer": optimizer.state_dict()}
            load(state, storage_reader=FileSystemReader(str(directory)))
            model.load_state_dict(state["model"])
            optimizer.load_state_dict(state["optimizer"])
    else:
        state = torch.load(
            directory / "checkpoint.pt",
            map_location=context.device,
            weights_only=True,
        )
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
    return int(state_meta["step"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=ROOT / "distributed_training/configs/fsdp_qwen_v0_1.yaml"
    )
    parser.add_argument("--no-fsdp", action="store_true")
    parser.add_argument("--resume-from", type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    context = initialize_distributed()
    fsdp_enabled = bool(config["fsdp"]["enabled"]) and not args.no_fsdp
    if fsdp_enabled != (context.world_size > 1):
        raise RuntimeError("Use --no-fsdp for one GPU and torchrun with >1 rank for FSDP.")
    seed_everything(int(config["seed"]), context.rank)
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"], use_fast=True)
    dtype, mixed_precision = precision_policy(config["mixed_precision"])
    model = AutoModelForCausalLM.from_pretrained(config["model_name"], torch_dtype=dtype)
    if config["gradient_checkpointing"]:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False
    if fsdp_enabled:
        model = FSDP(
            model,
            auto_wrap_policy=functools.partial(
                size_based_auto_wrap_policy, min_num_params=20_000_000
            ),
            device_id=context.device,
            mixed_precision=mixed_precision,
            use_orig_params=bool(config["fsdp"]["use_orig_params"]),
            limit_all_gathers=bool(config["fsdp"]["limit_all_gathers"]),
            forward_prefetch=bool(config["fsdp"]["forward_prefetch"]),
        )
    else:
        model.to(context.device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    train_dataset = load_rows(config, tokenizer, "train_input")
    validation_dataset = load_rows(config, tokenizer, "validation_input")
    train_sampler = DistributedSampler(
        train_dataset,
        num_replicas=context.world_size,
        rank=context.rank,
        shuffle=True,
        seed=int(config["seed"]),
    )
    validation_sampler = DistributedSampler(
        validation_dataset, num_replicas=context.world_size, rank=context.rank, shuffle=False
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=int(config["per_device_batch_size"]),
        sampler=train_sampler,
        collate_fn=collate,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=int(config["per_device_batch_size"]),
        sampler=validation_sampler,
        collate_fn=collate,
    )
    output_dir = ROOT / config["output_dir"]
    if context.rank == 0:
        output_dir.mkdir(parents=True, exist_ok=True)
    start_step = 0
    resume = args.resume_from or config["checkpoint"]["resume_from"]
    if resume:
        start_step = load_checkpoint(
            model, optimizer, directory=Path(resume), context=context, fsdp_enabled=fsdp_enabled
        )
    step = 0
    accumulation = int(config["gradient_accumulation_steps"])
    model.train()
    final_training_loss: float | None = None
    for epoch in range(int(config["epochs"])):
        train_sampler.set_epoch(epoch)
        for batch in train_loader:
            step += 1
            if step <= start_step:
                continue
            started = time.perf_counter()
            tokens = int(batch["attention_mask"].sum())
            batch = {key: value.to(context.device) for key, value in batch.items()}
            loss = model(**batch).loss / accumulation
            loss.backward()
            if step % accumulation == 0:
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), float(config["gradient_clip_norm"])
                )
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            if context.device.type == "cuda":
                torch.cuda.synchronize(context.device)
            elapsed = time.perf_counter() - started
            record = {
                "step": step,
                "epoch": epoch,
                "training_loss": (
                    reduce_sum(float(loss.detach()) * accumulation, context) / context.world_size
                ),
                "step_time_seconds": elapsed,
                "tokens_per_second": reduce_sum(float(tokens), context) / elapsed,
                "samples_per_second": context.world_size * len(batch["input_ids"]) / elapsed,
                "peak_gpu_memory_bytes_per_rank": torch.cuda.max_memory_allocated(context.device),
            }
            final_training_loss = float(record["training_loss"])
            if step % int(config["checkpoint"]["every_steps"]) == 0:
                save_time, size = save_checkpoint(
                    model,
                    optimizer,
                    directory=output_dir / "checkpoints",
                    step=step,
                    context=context,
                    fsdp_enabled=fsdp_enabled,
                )
                record.update(checkpoint_save_seconds=save_time, checkpoint_size_bytes=size)
            if context.rank == 0:
                metrics_path = output_dir / config["logging"]["metrics_file"]
                with metrics_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
            if config["max_steps"] is not None and step >= int(config["max_steps"]):
                break
        if config["max_steps"] is not None and step >= int(config["max_steps"]):
            break
    validation_loss = evaluate(model, validation_loader, context)
    save_time, size = save_checkpoint(
        model,
        optimizer,
        directory=output_dir / "checkpoints",
        step=step,
        context=context,
        fsdp_enabled=fsdp_enabled,
    )
    if context.rank == 0:
        (output_dir / "summary.json").write_text(
            json.dumps(
                {
                    "configuration": "fsdp" if fsdp_enabled else "baseline",
                    "gpus": context.world_size,
                    "final_step": step,
                    "final_training_loss": final_training_loss,
                    "validation_loss": validation_loss,
                    "checkpoint_save_seconds": save_time,
                    "checkpoint_size_bytes": size,
                    "resume_validated": bool(resume),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if context.world_size > 1:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
