"""Tests for deterministic AeroRAG-X load-test summaries."""

from __future__ import annotations

import pytest

from aeroragx.observability.load_test import (
    RequestResult,
    percentile,
    summarize_results,
)


def test_percentile_interpolates_small_sample() -> None:
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 0.0) == 10.0
    assert percentile(values, 0.5) == 25.0
    assert percentile(values, 1.0) == 40.0


def test_percentile_rejects_invalid_inputs() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        percentile([], 0.5)

    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        percentile([1.0], 1.5)


def test_summarize_results_reports_latency_status_and_refusal() -> None:
    results = [
        RequestResult(
            elapsed_ms=100.0,
            status_code=200,
            insufficient_evidence=False,
            transport_error=False,
        ),
        RequestResult(
            elapsed_ms=200.0,
            status_code=200,
            insufficient_evidence=True,
            transport_error=False,
        ),
        RequestResult(
            elapsed_ms=300.0,
            status_code=503,
            insufficient_evidence=None,
            transport_error=False,
        ),
        RequestResult(
            elapsed_ms=400.0,
            status_code=None,
            insufficient_evidence=None,
            transport_error=True,
        ),
    ]

    report = summarize_results(
        base_url="http://127.0.0.1:8000",
        request_count=4,
        concurrency=2,
        warmup_count=1,
        wall_seconds=2.0,
        results=results,
    )

    assert report.success_count == 2
    assert report.failure_count == 2
    assert report.success_rate == 0.5
    assert report.status_2xx_count == 2
    assert report.status_5xx_count == 1
    assert report.transport_error_count == 1
    assert report.insufficient_evidence_count == 1
    assert report.refusal_rate == 0.5
    assert report.requests_per_second == 2.0

    assert report.latency_ms.minimum_ms == 100.0
    assert report.latency_ms.mean_ms == 250.0
    assert report.latency_ms.p50_ms == 250.0
    assert report.latency_ms.maximum_ms == 400.0


def test_summarize_results_rejects_length_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="results length must equal request_count",
    ):
        summarize_results(
            base_url="http://127.0.0.1:8000",
            request_count=2,
            concurrency=1,
            warmup_count=0,
            wall_seconds=1.0,
            results=[
                RequestResult(
                    elapsed_ms=100.0,
                    status_code=200,
                    insufficient_evidence=False,
                    transport_error=False,
                )
            ],
        )
