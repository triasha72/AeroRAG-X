#!/usr/bin/env python3
"""Run a bounded concurrent HTTP benchmark against the distributed Agent API."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

from aeroragx.evaluation.distributed_reliability import (
    DistributedRequestObservation,
    summarize_distributed_reliability,
)


async def run_one(
    client: httpx.AsyncClient,
    url: str,
    *,
    scenario: str,
    query: str,
) -> DistributedRequestObservation:
    request_id = str(uuid4())
    payload = {
        "context": {
            "request_id": request_id,
            "trace_id": request_id,
            "thread_id": request_id,
        },
        "query": query,
    }
    started = perf_counter()
    try:
        response = await client.post(url, json=payload)
        latency_ms = (perf_counter() - started) * 1000.0
        response.raise_for_status()
        body = response.json()
        termination = body.get("termination_reason")
        answer = body.get("answer")
        safe_refusal = answer is None and termination != "answer_completed"
        unsafe_answer = bool(answer) and termination != "answer_completed"
        return DistributedRequestObservation(
            scenario=scenario,
            latency_ms=latency_ms,
            success=True,
            safe_refusal=safe_refusal,
            unsafe_answer=unsafe_answer,
        )
    except httpx.TimeoutException:
        return DistributedRequestObservation(
            scenario=scenario,
            latency_ms=(perf_counter() - started) * 1000.0,
            success=False,
            timed_out=True,
        )
    except Exception:
        return DistributedRequestObservation(
            scenario=scenario,
            latency_ms=(perf_counter() - started) * 1000.0,
            success=False,
        )


async def run(args: argparse.Namespace) -> None:
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    async with httpx.AsyncClient(
        timeout=args.timeout_seconds,
        limits=limits,
    ) as client:
        semaphore = asyncio.Semaphore(args.concurrency)

        async def bounded() -> DistributedRequestObservation:
            async with semaphore:
                return await run_one(
                    client,
                    args.url,
                    scenario=args.scenario,
                    query=args.query,
                )

        observations = await asyncio.gather(
            *(bounded() for _ in range(args.requests))
        )

    metrics = summarize_distributed_reliability(observations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "metrics": metrics.model_dump(mode="json"),
                "observations": [
                    item.model_dump(mode="json") for item in observations
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(args.output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/v1/query")
    parser.add_argument("--scenario", default="healthy")
    parser.add_argument("--query", default="thermal protection")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/evaluation/distributed_reliability_v0_1.json"),
    )
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1:
        raise SystemExit("requests and concurrency must be positive")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
