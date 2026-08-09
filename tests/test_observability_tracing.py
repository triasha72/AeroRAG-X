"""Tests for AeroRAG-X OpenTelemetry tracing primitives."""

from __future__ import annotations

import pytest
from opentelemetry import context, trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from aeroragx.observability.tracing import (
    create_tracing_runtime,
    current_trace_ids,
    current_tracer,
    use_tracer,
)


def test_tracing_runtime_exports_isolated_span() -> None:
    exporter = InMemorySpanExporter()
    runtime = create_tracing_runtime(
        exporter=exporter,
        environment="test",
        batch_export=False,
    )

    with runtime.tracer.start_as_current_span(
        "aeroragx.test.operation",
    ) as span:
        span.set_attribute(
            "aeroragx.test.value",
            7,
        )

        trace_id, span_id = current_trace_ids()

        assert trace_id is not None
        assert len(trace_id) == 32
        assert span_id is not None
        assert len(span_id) == 16

    spans = exporter.get_finished_spans()

    assert len(spans) == 1
    assert spans[0].name == "aeroragx.test.operation"
    assert spans[0].attributes["aeroragx.test.value"] == 7
    assert spans[0].resource.attributes["service.name"] == "aeroragx"
    assert spans[0].resource.attributes["service.version"] == "0.1.0"
    assert spans[0].resource.attributes["deployment.environment.name"] == "test"

    runtime.shutdown()


def test_tracing_runtime_does_not_replace_global_provider() -> None:
    before = trace.get_tracer_provider()
    runtime = create_tracing_runtime(
        environment="test",
    )

    after = trace.get_tracer_provider()

    assert after is before

    runtime.shutdown()


def test_current_trace_ids_are_empty_without_active_valid_span() -> None:
    token = context.attach(
        context.Context(),
    )

    try:
        assert current_trace_ids() == (None, None)
    finally:
        context.detach(token)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("service_name", "   ", "service_name must not be blank"),
        (
            "service_version",
            "",
            "service_version must not be blank",
        ),
        ("environment", " ", "environment must not be blank"),
    ],
)
def test_tracing_runtime_rejects_blank_resource_fields(
    field: str,
    value: str,
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        if field == "service_name":
            create_tracing_runtime(
                service_name=value,
            )
        elif field == "service_version":
            create_tracing_runtime(
                service_version=value,
            )
        else:
            create_tracing_runtime(
                environment=value,
            )


@pytest.mark.parametrize(
    "sample_ratio",
    [-0.01, 1.01],
)
def test_tracing_runtime_rejects_invalid_sample_ratio(
    sample_ratio: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="sample_ratio must be between 0 and 1",
    ):
        create_tracing_runtime(
            sample_ratio=sample_ratio,
        )


def test_use_tracer_binds_and_restores_request_local_tracer() -> None:
    runtime = create_tracing_runtime(
        environment="test",
    )

    assert current_tracer() is None

    with use_tracer(runtime.tracer):
        assert current_tracer() is runtime.tracer

    assert current_tracer() is None

    runtime.shutdown()
