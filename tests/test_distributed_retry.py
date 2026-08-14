"""Tests for bounded asynchronous service retries."""

import asyncio

from aeroragx.services.retry_policy import AsyncRetryPolicy, run_with_retry


def test_retry_stops_after_success() -> None:
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("timeout")
        return "ok"

    result = asyncio.run(
        run_with_retry(
            operation,
            policy=AsyncRetryPolicy(maximum_retries=1, base_delay_seconds=0),
            retryable=lambda exc: isinstance(exc, TimeoutError),
        )
    )

    assert result == "ok"
    assert calls == 2
