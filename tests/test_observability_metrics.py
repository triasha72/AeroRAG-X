"""Tests for AeroRAG-X Prometheus metrics primitives."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from aeroragx.observability.metrics import ServiceMetrics


def render_metrics(metrics: ServiceMetrics) -> str:
    """Render one isolated registry in Prometheus text format."""

    return generate_latest(
        metrics.registry,
    ).decode("utf-8")


def test_http_metrics_use_bounded_labels_and_status_class() -> None:
    metrics = ServiceMetrics(
        CollectorRegistry(),
    )

    metrics.record_http_request(
        method="post",
        route="/v1/query",
        status_code=200,
        duration_seconds=0.25,
    )

    rendered = render_metrics(metrics)

    assert (
        "aeroragx_http_requests_total{"
        'method="POST",route="/v1/query",status_class="2xx"} 1.0' in rendered
    )
    assert (
        "aeroragx_http_request_duration_seconds_count{"
        'method="POST",route="/v1/query"} 1.0' in rendered
    )
    assert "request_id=" not in rendered
    assert "query=" not in rendered


def test_query_metrics_record_success_refusal_and_durations() -> None:
    metrics = ServiceMetrics(
        CollectorRegistry(),
    )

    metrics.record_query_started()
    metrics.record_query_completed(
        insufficient_evidence=True,
        rag_duration_seconds=1.25,
        retrieval_duration_seconds=0.4,
        reranker_duration_seconds=0.2,
    )

    rendered = render_metrics(metrics)

    assert "aeroragx_query_requests_total 1.0" in rendered
    assert "aeroragx_query_success_total 1.0" in rendered
    assert "aeroragx_insufficient_evidence_total 1.0" in rendered
    assert "aeroragx_rag_duration_seconds_count 1.0" in rendered
    assert "aeroragx_retrieval_duration_seconds_count 1.0" in rendered
    assert "aeroragx_reranker_duration_seconds_count 1.0" in rendered


def test_query_error_is_counted_separately() -> None:
    metrics = ServiceMetrics(
        CollectorRegistry(),
    )

    metrics.record_query_started()
    metrics.record_query_error()

    rendered = render_metrics(metrics)

    assert "aeroragx_query_requests_total 1.0" in rendered
    assert "aeroragx_query_errors_total 1.0" in rendered
    assert "aeroragx_query_success_total 0.0" in rendered


def test_provider_metrics_track_calls_errors_latency_and_bypass() -> None:
    metrics = ServiceMetrics(
        CollectorRegistry(),
    )

    metrics.record_provider_call(
        provider="openai-responses",
        duration_seconds=0.75,
        succeeded=False,
    )
    metrics.record_provider_bypass()

    rendered = render_metrics(metrics)

    assert 'aeroragx_provider_calls_total{provider="openai-responses"} 1.0' in rendered
    assert 'aeroragx_provider_errors_total{provider="openai-responses"} 1.0' in rendered
    assert 'aeroragx_provider_duration_seconds_count{provider="openai-responses"} 1.0' in rendered
    assert "aeroragx_provider_bypasses_total 1.0" in rendered
    assert "provider_request_id=" not in rendered


def test_separate_registries_do_not_collide() -> None:
    first = ServiceMetrics(
        CollectorRegistry(),
    )
    second = ServiceMetrics(
        CollectorRegistry(),
    )

    first.record_query_started()
    second.record_query_started()

    assert "aeroragx_query_requests_total 1.0" in render_metrics(first)
    assert "aeroragx_query_requests_total 1.0" in render_metrics(second)


@pytest.mark.parametrize(
    "recorder",
    [
        lambda metrics: metrics.record_http_request(
            method="GET",
            route="/health",
            status_code=200,
            duration_seconds=-0.1,
        ),
        lambda metrics: metrics.record_query_completed(
            insufficient_evidence=False,
            rag_duration_seconds=-0.1,
        ),
        lambda metrics: metrics.record_provider_call(
            provider="fake",
            duration_seconds=-0.1,
            succeeded=True,
        ),
    ],
)
def test_negative_durations_are_rejected(
    recorder: Callable[[ServiceMetrics], None],
) -> None:
    metrics = ServiceMetrics(
        CollectorRegistry(),
    )

    with pytest.raises(
        ValueError,
        match="duration_seconds must be non-negative",
    ):
        recorder(metrics)
