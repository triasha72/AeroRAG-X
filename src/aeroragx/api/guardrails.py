"""Process-local API guardrails for bounded public request handling."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True, slots=True)
class ApiGuardrailSettings:
    """Validated request guardrails applied to the query endpoint."""

    max_request_bytes: int = 16_384
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """One deterministic rate-limit decision."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    """Bound request volume per client within one process.

    This limiter protects local and single-instance deployments. Distributed
    deployments must also enforce a shared limit at the ingress layer.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1.")

        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1.")

        self._limit = limit
        self._window_seconds = window_seconds
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        *,
        key: str,
        now: float | None = None,
    ) -> RateLimitDecision:
        """Consume one request slot when capacity remains."""

        current = monotonic() if now is None else now
        cutoff = current - self._window_seconds

        with self._lock:
            timestamps = self._requests[key]

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self._limit:
                retry_after = max(
                    1,
                    int(self._window_seconds - (current - timestamps[0])) + 1,
                )

                return RateLimitDecision(
                    allowed=False,
                    limit=self._limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            timestamps.append(current)

            return RateLimitDecision(
                allowed=True,
                limit=self._limit,
                remaining=self._limit - len(timestamps),
                retry_after_seconds=0,
            )
