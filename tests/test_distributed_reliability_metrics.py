"""Tests for Phase 44 reliability metrics."""

from aeroragx.evaluation.distributed_reliability import (
    DistributedRequestObservation,
    summarize_distributed_reliability,
)


def test_unsafe_answer_rate_is_explicit() -> None:
    metrics = summarize_distributed_reliability(
        [
            DistributedRequestObservation(
                scenario="dependency_failure",
                latency_ms=10,
                success=True,
                safe_refusal=True,
            ),
            DistributedRequestObservation(
                scenario="dependency_failure",
                latency_ms=20,
                success=True,
                unsafe_answer=True,
            ),
        ]
    )

    assert metrics.safe_refusal_rate == 0.5
    assert metrics.unsafe_answer_rate == 0.5
