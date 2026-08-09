"""Deterministic HTTP load-validation utilities for AeroRAG-X."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class RequestResult:
    """One measured HTTP query attempt."""

    elapsed_ms: float
    status_code: int | None
    insufficient_evidence: bool | None
    transport_error: bool


@dataclass(frozen=True, slots=True)
class LatencySummary:
    """Latency distribution in milliseconds."""

    minimum_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    maximum_ms: float


@dataclass(frozen=True, slots=True)
class LoadTestReport:
    """Machine-readable summary for one load-validation run."""

    base_url: str
    request_count: int
    concurrency: int
    warmup_count: int
    wall_seconds: float
    requests_per_second: float
    success_count: int
    failure_count: int
    success_rate: float
    status_2xx_count: int
    status_4xx_count: int
    status_5xx_count: int
    other_status_count: int
    transport_error_count: int
    insufficient_evidence_count: int
    refusal_rate: float
    latency_ms: LatencySummary


def percentile(
    values: Sequence[float],
    quantile: float,
) -> float:
    """Return a linearly interpolated quantile for a non-empty sample."""

    if not values:
        raise ValueError("values must not be empty.")

    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1.")

    ordered = sorted(float(value) for value in values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered[lower_index]

    fraction = position - lower_index

    return ordered[lower_index] * (1.0 - fraction) + ordered[upper_index] * fraction


def _status_class(
    status_code: int | None,
) -> str:
    if status_code is None:
        return "transport_error"

    if 200 <= status_code <= 299:
        return "2xx"

    if 400 <= status_code <= 499:
        return "4xx"

    if 500 <= status_code <= 599:
        return "5xx"

    return "other"


def summarize_results(
    *,
    base_url: str,
    request_count: int,
    concurrency: int,
    warmup_count: int,
    wall_seconds: float,
    results: Sequence[RequestResult],
) -> LoadTestReport:
    """Summarize measured requests into stable load-test metrics."""

    if request_count < 1:
        raise ValueError("request_count must be at least 1.")

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1.")

    if warmup_count < 0:
        raise ValueError("warmup_count must be non-negative.")

    if wall_seconds <= 0.0:
        raise ValueError("wall_seconds must be positive.")

    if len(results) != request_count:
        raise ValueError("results length must equal request_count.")

    latencies = [result.elapsed_ms for result in results]

    status_2xx_count = sum(_status_class(result.status_code) == "2xx" for result in results)
    status_4xx_count = sum(_status_class(result.status_code) == "4xx" for result in results)
    status_5xx_count = sum(_status_class(result.status_code) == "5xx" for result in results)
    other_status_count = sum(_status_class(result.status_code) == "other" for result in results)
    transport_error_count = sum(result.transport_error for result in results)

    success_count = status_2xx_count
    failure_count = request_count - success_count

    insufficient_evidence_count = sum(
        result.status_code is not None
        and 200 <= result.status_code <= 299
        and result.insufficient_evidence is True
        for result in results
    )

    refusal_rate = insufficient_evidence_count / success_count if success_count else 0.0

    return LoadTestReport(
        base_url=base_url,
        request_count=request_count,
        concurrency=concurrency,
        warmup_count=warmup_count,
        wall_seconds=round(wall_seconds, 6),
        requests_per_second=round(
            request_count / wall_seconds,
            6,
        ),
        success_count=success_count,
        failure_count=failure_count,
        success_rate=round(
            success_count / request_count,
            6,
        ),
        status_2xx_count=status_2xx_count,
        status_4xx_count=status_4xx_count,
        status_5xx_count=status_5xx_count,
        other_status_count=other_status_count,
        transport_error_count=transport_error_count,
        insufficient_evidence_count=insufficient_evidence_count,
        refusal_rate=round(refusal_rate, 6),
        latency_ms=LatencySummary(
            minimum_ms=round(min(latencies), 3),
            mean_ms=round(fmean(latencies), 3),
            p50_ms=round(percentile(latencies, 0.50), 3),
            p95_ms=round(percentile(latencies, 0.95), 3),
            p99_ms=round(percentile(latencies, 0.99), 3),
            maximum_ms=round(max(latencies), 3),
        ),
    )


async def _request_once(
    client: httpx.AsyncClient,
    *,
    query: str,
) -> RequestResult:
    started_at = perf_counter()

    try:
        response = await client.post(
            "/v1/query",
            json={
                "query": query,
            },
        )
    except httpx.HTTPError:
        return RequestResult(
            elapsed_ms=round(
                (perf_counter() - started_at) * 1000.0,
                3,
            ),
            status_code=None,
            insufficient_evidence=None,
            transport_error=True,
        )

    elapsed_ms = round(
        (perf_counter() - started_at) * 1000.0,
        3,
    )

    insufficient_evidence: bool | None = None

    if 200 <= response.status_code <= 299:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            candidate = payload.get(
                "insufficient_evidence",
            )

            if isinstance(candidate, bool):
                insufficient_evidence = candidate

    return RequestResult(
        elapsed_ms=elapsed_ms,
        status_code=response.status_code,
        insufficient_evidence=insufficient_evidence,
        transport_error=False,
    )


async def _check_service(
    client: httpx.AsyncClient,
) -> None:
    health = await client.get("/health")

    if health.status_code != 200:
        raise RuntimeError(f"/health returned HTTP {health.status_code}.")

    ready = await client.get("/ready")

    if ready.status_code != 200:
        raise RuntimeError(f"/ready returned HTTP {ready.status_code}.")

    payload: Any = ready.json()

    if not isinstance(payload, dict) or payload.get("ready") is not True:
        raise RuntimeError("AeroRAG-X is not ready for load validation.")


async def run_load_test(
    *,
    base_url: str,
    query: str,
    request_count: int,
    concurrency: int,
    warmup_count: int,
    timeout_seconds: float,
) -> LoadTestReport:
    """Execute one bounded-concurrency load validation."""

    if request_count < 1:
        raise ValueError("request_count must be at least 1.")

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1.")

    if warmup_count < 0:
        raise ValueError("warmup_count must be non-negative.")

    if timeout_seconds <= 0.0:
        raise ValueError("timeout_seconds must be positive.")

    normalized_base_url = base_url.rstrip("/")

    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )

    async with httpx.AsyncClient(
        base_url=normalized_base_url,
        timeout=timeout_seconds,
        limits=limits,
    ) as client:
        await _check_service(client)

        for _ in range(warmup_count):
            await _request_once(
                client,
                query=query,
            )

        semaphore = asyncio.Semaphore(concurrency)

        async def measured_request() -> RequestResult:
            async with semaphore:
                return await _request_once(
                    client,
                    query=query,
                )

        started_at = perf_counter()

        results = await asyncio.gather(*(measured_request() for _ in range(request_count)))

        wall_seconds = perf_counter() - started_at

    return summarize_results(
        base_url=normalized_base_url,
        request_count=request_count,
        concurrency=concurrency,
        warmup_count=warmup_count,
        wall_seconds=wall_seconds,
        results=results,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Run a deterministic local HTTP load validation against AeroRAG-X."),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--query",
        default=("What thermal-management challenges affect electrified aircraft?"),
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=20,
        dest="request_count",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=2,
        dest="warmup_count",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    return parser


def _report_json(
    report: LoadTestReport,
) -> str:
    return json.dumps(
        asdict(report),
        indent=2,
        sort_keys=True,
    )


def main() -> int:
    """Run the command-line load validator."""

    args = _parser().parse_args()

    report = asyncio.run(
        run_load_test(
            base_url=args.base_url,
            query=args.query,
            request_count=args.request_count,
            concurrency=args.concurrency,
            warmup_count=args.warmup_count,
            timeout_seconds=args.timeout_seconds,
        )
    )

    rendered = _report_json(report)
    print(rendered)

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    return 0 if report.failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
