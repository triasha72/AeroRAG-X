"""Benchmark normal and shared-policy-prefix vLLM serving."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import threading
import time
from pathlib import Path

from aeroragx.generation.vllm_benchmark import BenchmarkPrompt, run_vllm_benchmark


class NvidiaMemoryMonitor:
    """Sample total used NVIDIA memory while one condition runs."""

    def __init__(self) -> None:
        self.peak_bytes: int | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.is_set():
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-compute-apps=used_memory",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError:
                return
            if result.returncode == 0:
                values = [
                    int(value.strip()) for value in result.stdout.splitlines() if value.strip()
                ]
                if values:
                    used_bytes = sum(values) * 1024 * 1024
                    self.peak_bytes = max(self.peak_bytes or 0, used_bytes)
            time.sleep(0.1)

    def __enter__(self) -> NvidiaMemoryMonitor:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--model", default="Qwen/Qwen3-4B-Instruct-2507")
    parser.add_argument("--input", type=Path, required=True, help="JSONL with content and policy")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()
    rows = [
        json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line
    ]
    rows = (rows * ((args.requests + len(rows) - 1) // len(rows)))[: args.requests]
    shared_policy = str(rows[0]["policy"])
    results = []
    for concurrency in (1, 8, 16, 32):
        for shared in (False, True):
            prompts = [
                BenchmarkPrompt(
                    system=(
                        shared_policy
                        if shared
                        else f"Request-specific context {index}.\n{row['policy']}"
                    ),
                    content=str(row["content"]),
                )
                for index, row in enumerate(rows)
            ]
            with NvidiaMemoryMonitor() as memory:
                summary = asyncio.run(
                    run_vllm_benchmark(
                        endpoint_url=args.endpoint,
                        model_name=args.model,
                        prompts=prompts,
                        concurrency=concurrency,
                        max_tokens=args.max_tokens,
                        shared_policy_prefix=shared,
                    )
                )
            summary.peak_gpu_memory_bytes = memory.peak_bytes
            results.append(summary.model_dump())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
