"""Validate and launch the matched Megatron-LM tensor-parallel treatment."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "distributed_training/configs/megatron_qwen_v0_1.yaml",
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    megatron_root = os.environ.get("MEGATRON_LM_ROOT")
    if not megatron_root:
        raise ValueError("Set MEGATRON_LM_ROOT to a pinned Megatron-LM checkout.")
    script = Path(megatron_root) / "pretrain_gpt.py"
    if not script.is_file():
        raise ValueError(f"Megatron pretrain entry point was not found: {script}")
    world_size = int(config["tensor_parallel_size"]) * int(config["pipeline_parallel_size"])
    command = [
        "torchrun", "--standalone", f"--nproc_per_node={world_size}", str(script),
        "--tensor-model-parallel-size", str(config["tensor_parallel_size"]),
        "--pipeline-model-parallel-size", str(config["pipeline_parallel_size"]),
        "--micro-batch-size", str(config["micro_batch_size"]),
        "--global-batch-size", str(config["global_batch_size"]),
        "--seq-length", str(config["sequence_length"]),
        "--max-position-embeddings", str(config["sequence_length"]),
        "--train-iters", str(config["train_steps"]),
        "--lr", str(config["learning_rate"]),
        "--min-lr", str(config["min_learning_rate"]),
        "--seed", str(config["seed"]),
        "--data-path", str(ROOT / config["dataset_prefix"]),
        "--tokenizer-type", "HuggingFaceTokenizer",
        "--tokenizer-model", str(ROOT / config["tokenizer_model"]),
        "--save", str(ROOT / config["checkpoint_dir"]),
        "--load", str(ROOT / config["checkpoint_dir"]),
        "--bf16",
        "--use-distributed-optimizer",
        "--sequence-parallel",
        "--recompute-granularity", "full",
        "--recompute-method", "uniform",
        "--recompute-num-layers", "1",
    ]
    print(" ".join(command))
    if args.execute:
        subprocess.run(command, cwd=megatron_root, check=True)


if __name__ == "__main__":
    main()
