"""Metrics for reproducible distributed reliability/load experiments."""

from __future__ import annotations

from statistics import median

from pydantic import BaseModel, ConfigDict, Field


class DistributedRequestObservation(BaseModel):
    """One measured request under a named fault scenario."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scenario: str = Field(min_length=1)
    latency_ms: float = Field(ge=0.0)
    success: bool
    timed_out: bool = False
    recovery_attempted: bool = False
    recovered: bool = False
    safe_refusal: bool = False
    unsafe_answer: bool = False


class DistributedReliabilityMetrics(BaseModel):
    """Aggregate reliability/load metrics."""

    model_config = ConfigDict(extra="forbid")

    request_count: int = Field(ge=1)
    success_rate: float = Field(ge=0.0, le=1.0)
    timeout_rate: float = Field(ge=0.0, le=1.0)
    recovery_rate: float = Field(ge=0.0, le=1.0)
    safe_refusal_rate: float = Field(ge=0.0, le=1.0)
    unsafe_answer_rate: float = Field(ge=0.0, le=1.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)


def summarize_distributed_reliability(
    observations: list[DistributedRequestObservation],
) -> DistributedReliabilityMetrics:
    if not observations:
        raise ValueError("Reliability metrics require at least one observation.")

    count = len(observations)
    latencies = sorted(item.latency_ms for item in observations)
    p95_index = max(int(round(0.95 * (count - 1))), 0)
    recovery_attempts = sum(item.recovery_attempted for item in observations)
    recovery_successes = sum(
        item.recovered for item in observations if item.recovery_attempted
    )

    return DistributedReliabilityMetrics(
        request_count=count,
        success_rate=sum(item.success for item in observations) / count,
        timeout_rate=sum(item.timed_out for item in observations) / count,
        recovery_rate=(
            1.0
            if recovery_attempts == 0
            else recovery_successes / recovery_attempts
        ),
        safe_refusal_rate=sum(item.safe_refusal for item in observations) / count,
        unsafe_answer_rate=sum(item.unsafe_answer for item in observations) / count,
        p50_latency_ms=float(median(latencies)),
        p95_latency_ms=latencies[p95_index],
    )
