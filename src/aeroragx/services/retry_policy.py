"""Async bounded retries for cross-service HTTP operations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AsyncRetryPolicy:
    maximum_retries: int = 1
    base_delay_seconds: float = 0.05

    def __post_init__(self) -> None:
        if self.maximum_retries < 0:
            raise ValueError("maximum_retries must be non-negative.")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative.")


async def run_with_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    policy: AsyncRetryPolicy,
    retryable: Callable[[Exception], bool],
) -> T:
    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as exc:
            if attempt >= policy.maximum_retries or not retryable(exc):
                raise
            attempt += 1
            await asyncio.sleep(policy.base_delay_seconds * attempt)
