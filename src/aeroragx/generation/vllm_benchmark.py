"""Concurrency benchmark and aggregation for policy-prefix vLLM workloads."""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ConfigDict, Field


class VLLMRequestMetric(BaseModel):
    """Measurements for one streaming request."""

    model_config = ConfigDict(extra="forbid")
    latency_seconds: float = Field(ge=0)
    ttft_seconds: float | None = Field(default=None, ge=0)
    output_tokens: int = Field(ge=0)
    succeeded: bool

    @property
    def tpot_seconds(self) -> float | None:
        if not self.succeeded or self.output_tokens <= 1 or self.ttft_seconds is None:
            return None
        return max(0.0, self.latency_seconds - self.ttft_seconds) / (self.output_tokens - 1)


class VLLMBenchmarkSummary(BaseModel):
    """Aggregate measurements for one concurrency/prefix condition."""

    model_config = ConfigDict(extra="forbid")
    concurrency: int = Field(ge=1)
    shared_policy_prefix: bool
    request_count: int = Field(ge=1)
    request_throughput: float = Field(ge=0)
    output_tokens_per_second: float = Field(ge=0)
    p50_latency_seconds: float = Field(ge=0)
    p95_latency_seconds: float = Field(ge=0)
    p50_ttft_seconds: float | None = Field(default=None, ge=0)
    mean_tpot_seconds: float | None = Field(default=None, ge=0)
    failure_rate: float = Field(ge=0, le=1)
    peak_gpu_memory_bytes: int | None = Field(default=None, ge=0)


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot compute a percentile of an empty sequence.")
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def summarize_vllm_metrics(
    metrics: Sequence[VLLMRequestMetric],
    *,
    concurrency: int,
    shared_policy_prefix: bool,
    wall_seconds: float,
    peak_gpu_memory_bytes: int | None = None,
) -> VLLMBenchmarkSummary:
    """Aggregate request metrics with failures retained in the denominator."""

    if not metrics or wall_seconds <= 0:
        raise ValueError("Metrics must be non-empty and wall_seconds must be positive.")
    successful = [metric for metric in metrics if metric.succeeded]
    latencies = [metric.latency_seconds for metric in successful]
    if not latencies:
        latencies = [0.0]
    ttfts = [metric.ttft_seconds for metric in successful if metric.ttft_seconds is not None]
    tpots = [metric.tpot_seconds for metric in successful if metric.tpot_seconds is not None]
    output_tokens = sum(metric.output_tokens for metric in successful)
    return VLLMBenchmarkSummary(
        concurrency=concurrency,
        shared_policy_prefix=shared_policy_prefix,
        request_count=len(metrics),
        request_throughput=len(successful) / wall_seconds,
        output_tokens_per_second=output_tokens / wall_seconds,
        p50_latency_seconds=_percentile(latencies, 0.50),
        p95_latency_seconds=_percentile(latencies, 0.95),
        p50_ttft_seconds=_percentile(ttfts, 0.50) if ttfts else None,
        mean_tpot_seconds=sum(tpots) / len(tpots) if tpots else None,
        failure_rate=(len(metrics) - len(successful)) / len(metrics),
        peak_gpu_memory_bytes=peak_gpu_memory_bytes,
    )


@dataclass(frozen=True)
class BenchmarkPrompt:
    system: str
    content: str


async def _stream_request(
    client: httpx.AsyncClient,
    *,
    endpoint_url: str,
    model_name: str,
    prompt: BenchmarkPrompt,
    max_tokens: int,
    clock: Callable[[], float] = time.perf_counter,
) -> VLLMRequestMetric:
    started = clock()
    first_token_at: float | None = None
    output_tokens = 0
    try:
        async with client.stream(
            "POST",
            endpoint_url,
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.content},
                ],
                "stream": True,
                "stream_options": {"include_usage": True},
                "temperature": 0.0,
                "max_tokens": max_tokens,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                event = json.loads(line[6:])
                choices = event.get("choices", [])
                if choices and choices[0].get("delta", {}).get("content"):
                    if first_token_at is None:
                        first_token_at = clock()
                    output_tokens += 1
                usage = event.get("usage")
                if usage and usage.get("completion_tokens") is not None:
                    output_tokens = int(usage["completion_tokens"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return VLLMRequestMetric(
            latency_seconds=max(0.0, clock() - started),
            ttft_seconds=None,
            output_tokens=0,
            succeeded=False,
        )
    ended = clock()
    return VLLMRequestMetric(
        latency_seconds=max(0.0, ended - started),
        ttft_seconds=None if first_token_at is None else max(0.0, first_token_at - started),
        output_tokens=output_tokens,
        succeeded=first_token_at is not None,
    )


async def run_vllm_benchmark(
    *,
    endpoint_url: str,
    model_name: str,
    prompts: Sequence[BenchmarkPrompt],
    concurrency: int,
    max_tokens: int,
    shared_policy_prefix: bool,
) -> VLLMBenchmarkSummary:
    """Run a bounded concurrent streaming benchmark."""

    if not prompts:
        raise ValueError("At least one prompt is required.")
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=None) as client:

        async def execute(prompt: BenchmarkPrompt) -> VLLMRequestMetric:
            async with semaphore:
                return await _stream_request(
                    client,
                    endpoint_url=endpoint_url,
                    model_name=model_name,
                    prompt=prompt,
                    max_tokens=max_tokens,
                )

        started = time.perf_counter()
        metrics = await asyncio.gather(*(execute(prompt) for prompt in prompts))
        wall_seconds = time.perf_counter() - started
    return summarize_vllm_metrics(
        metrics,
        concurrency=concurrency,
        shared_policy_prefix=shared_policy_prefix,
        wall_seconds=wall_seconds,
    )
