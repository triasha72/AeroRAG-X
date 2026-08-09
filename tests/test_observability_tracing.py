"""Tests for AeroRAG-X OpenTelemetry tracing primitives."""

from __future__ import annotations

import pytest
from opentelemetry import context, trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from aeroragx.observability.tracing import (
    create_configured_tracing_runtime,
    create_tracing_runtime,
    current_trace_ids,
    current_tracer,
    load_tracing_settings,
    trace_span,
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


def test_trace_span_is_noop_without_bound_tracer() -> None:
    with trace_span(
        "aeroragx.test.noop",
    ) as span:
        assert span is None


def test_trace_span_rejects_blank_name() -> None:
    with pytest.raises(
        ValueError,
        match="span name must not be blank",
    ):
        with trace_span("   "):
            pass


def test_load_tracing_settings_defaults_to_disabled() -> None:
    settings = load_tracing_settings({})

    assert settings.enabled is False
    assert settings.endpoint == "http://127.0.0.1:4318/v1/traces"
    assert settings.service_name == "aeroragx"
    assert settings.service_version == "0.1.0"
    assert settings.environment == "local"
    assert settings.sample_ratio == 1.0


def test_load_tracing_settings_reads_otlp_environment() -> None:
    settings = load_tracing_settings(
        {
            "AERORAGX_OTEL_ENABLED": "true",
            "AERORAGX_OTEL_ENDPOINT": ("http://collector:4318/v1/traces"),
            "AERORAGX_OTEL_SERVICE_NAME": "aeroragx-api",
            "AERORAGX_OTEL_SERVICE_VERSION": "0.1.0-test",
            "AERORAGX_OTEL_ENVIRONMENT": "test",
            "AERORAGX_OTEL_SAMPLE_RATIO": "0.25",
        }
    )

    assert settings.enabled is True
    assert settings.endpoint == "http://collector:4318/v1/traces"
    assert settings.service_name == "aeroragx-api"
    assert settings.service_version == "0.1.0-test"
    assert settings.environment == "test"
    assert settings.sample_ratio == 0.25


@pytest.mark.parametrize(
    "raw_value",
    ["maybe", "enabled", "2"],
)
def test_load_tracing_settings_rejects_invalid_enabled_value(
    raw_value: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="AERORAGX_OTEL_ENABLED",
    ):
        load_tracing_settings(
            {
                "AERORAGX_OTEL_ENABLED": raw_value,
            }
        )


@pytest.mark.parametrize(
    "raw_value",
    ["invalid", "-0.1", "1.1"],
)
def test_load_tracing_settings_rejects_invalid_sample_ratio(
    raw_value: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="AERORAGX_OTEL_SAMPLE_RATIO",
    ):
        load_tracing_settings(
            {
                "AERORAGX_OTEL_SAMPLE_RATIO": raw_value,
            }
        )


def test_configured_tracing_runtime_is_no_exporter_when_disabled() -> None:
    runtime = create_configured_tracing_runtime(
        {
            "AERORAGX_OTEL_ENABLED": "false",
            "AERORAGX_OTEL_ENVIRONMENT": "test",
        }
    )

    with runtime.tracer.start_as_current_span(
        "aeroragx.test.disabled_export",
    ):
        pass

    assert runtime.force_flush()

    runtime.shutdown()
