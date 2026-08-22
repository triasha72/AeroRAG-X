"""Tests for process-local API request guardrails."""

from __future__ import annotations

import pytest

from aeroragx.api.guardrails import SlidingWindowRateLimiter


def test_sliding_window_releases_capacity_after_window() -> None:
    limiter = SlidingWindowRateLimiter(
        limit=2,
        window_seconds=10,
    )

    assert limiter.check(key="client", now=0.0).allowed is True
    assert limiter.check(key="client", now=1.0).allowed is True

    blocked = limiter.check(key="client", now=2.0)

    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds == 9

    recovered = limiter.check(key="client", now=11.1)

    assert recovered.allowed is True
    assert recovered.remaining == 1


def test_sliding_window_isolated_by_client_key() -> None:
    limiter = SlidingWindowRateLimiter(
        limit=1,
        window_seconds=60,
    )

    assert limiter.check(key="client-a", now=0.0).allowed is True
    assert limiter.check(key="client-a", now=1.0).allowed is False
    assert limiter.check(key="client-b", now=1.0).allowed is True


@pytest.mark.parametrize(
    ("limit", "window_seconds"),
    [
        (0, 1),
        (1, 0),
    ],
)
def test_sliding_window_rejects_invalid_configuration(
    limit: int,
    window_seconds: int,
) -> None:
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(
            limit=limit,
            window_seconds=window_seconds,
        )
