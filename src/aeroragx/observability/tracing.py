"""OpenTelemetry tracing primitives for AeroRAG-X."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import (
    ParentBased,
    TraceIdRatioBased,
)
from opentelemetry.trace import Span, Tracer

_DEFAULT_SERVICE_NAME = "aeroragx"
_DEFAULT_SERVICE_VERSION = "0.1.0"

_CURRENT_TRACER: ContextVar[Tracer | None] = ContextVar(
    "aeroragx_current_tracer",
    default=None,
)


@dataclass(frozen=True, slots=True)
class TracingSettings:
    """Validated environment-driven tracing settings."""

    enabled: bool = False
    endpoint: str = "http://127.0.0.1:4318/v1/traces"
    service_name: str = _DEFAULT_SERVICE_NAME
    service_version: str = _DEFAULT_SERVICE_VERSION
    environment: str = "local"
    sample_ratio: float = 1.0


@dataclass(slots=True)
class TracingRuntime:
    """Own one isolated OpenTelemetry tracer provider and tracer."""

    provider: TracerProvider
    tracer: Tracer

    def force_flush(
        self,
        timeout_millis: int = 30_000,
    ) -> bool:
        """Flush pending spans to configured processors."""

        return self.provider.force_flush(
            timeout_millis=timeout_millis,
        )

    def shutdown(self) -> None:
        """Shut down tracing processors and exporters."""

        self.provider.shutdown()


def _parse_enabled(
    raw_value: str,
) -> bool:
    """Parse a strict boolean tracing environment variable."""

    normalized = raw_value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError("AERORAGX_OTEL_ENABLED must be one of: true, false, 1, 0, yes, no, on, off.")


def _parse_sample_ratio(
    raw_value: str,
) -> float:
    """Parse and validate the tracing sample ratio."""

    try:
        sample_ratio = float(raw_value)

    except ValueError as exc:
        raise ValueError("AERORAGX_OTEL_SAMPLE_RATIO must be a number.") from exc

    if not 0.0 <= sample_ratio <= 1.0:
        raise ValueError("AERORAGX_OTEL_SAMPLE_RATIO must be between 0 and 1.")

    return sample_ratio


def load_tracing_settings(
    environ: Mapping[str, str] | None = None,
) -> TracingSettings:
    """Load OpenTelemetry tracing settings from environment variables."""

    env = os.environ if environ is None else environ

    enabled = _parse_enabled(
        env.get(
            "AERORAGX_OTEL_ENABLED",
            "false",
        )
    )
    endpoint = env.get(
        "AERORAGX_OTEL_ENDPOINT",
        "http://127.0.0.1:4318/v1/traces",
    ).strip()
    service_name = env.get(
        "AERORAGX_OTEL_SERVICE_NAME",
        _DEFAULT_SERVICE_NAME,
    ).strip()
    service_version = env.get(
        "AERORAGX_OTEL_SERVICE_VERSION",
        _DEFAULT_SERVICE_VERSION,
    ).strip()
    environment = env.get(
        "AERORAGX_OTEL_ENVIRONMENT",
        "local",
    ).strip()
    sample_ratio = _parse_sample_ratio(
        env.get(
            "AERORAGX_OTEL_SAMPLE_RATIO",
            "1.0",
        )
    )

    if enabled and not endpoint:
        raise ValueError("AERORAGX_OTEL_ENDPOINT must not be blank when tracing is enabled.")

    if not service_name:
        raise ValueError("AERORAGX_OTEL_SERVICE_NAME must not be blank.")

    if not service_version:
        raise ValueError("AERORAGX_OTEL_SERVICE_VERSION must not be blank.")

    if not environment:
        raise ValueError("AERORAGX_OTEL_ENVIRONMENT must not be blank.")

    return TracingSettings(
        enabled=enabled,
        endpoint=endpoint,
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        sample_ratio=sample_ratio,
    )


def create_configured_tracing_runtime(
    environ: Mapping[str, str] | None = None,
) -> TracingRuntime:
    """Create the default tracing runtime from environment settings."""

    settings = load_tracing_settings(environ)

    exporter: SpanExporter | None = None

    if settings.enabled:
        exporter = OTLPSpanExporter(
            endpoint=settings.endpoint,
        )

    return create_tracing_runtime(
        exporter=exporter,
        service_name=settings.service_name,
        service_version=settings.service_version,
        environment=settings.environment,
        sample_ratio=settings.sample_ratio,
        batch_export=True,
    )


def create_tracing_runtime(
    *,
    exporter: SpanExporter | None = None,
    service_name: str = _DEFAULT_SERVICE_NAME,
    service_version: str = _DEFAULT_SERVICE_VERSION,
    environment: str = "local",
    sample_ratio: float = 1.0,
    batch_export: bool = True,
) -> TracingRuntime:
    """Create an isolated tracing runtime without mutating global state."""

    normalized_service_name = service_name.strip()
    normalized_service_version = service_version.strip()
    normalized_environment = environment.strip()

    if not normalized_service_name:
        raise ValueError("service_name must not be blank.")

    if not normalized_service_version:
        raise ValueError("service_version must not be blank.")

    if not normalized_environment:
        raise ValueError("environment must not be blank.")

    if not 0.0 <= sample_ratio <= 1.0:
        raise ValueError("sample_ratio must be between 0 and 1.")

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": normalized_service_name,
                "service.version": normalized_service_version,
                "deployment.environment.name": normalized_environment,
            }
        ),
        sampler=ParentBased(
            TraceIdRatioBased(sample_ratio),
        ),
    )

    if exporter is not None:
        processor = BatchSpanProcessor(exporter) if batch_export else SimpleSpanProcessor(exporter)
        provider.add_span_processor(processor)

    tracer = provider.get_tracer(
        "aeroragx",
        normalized_service_version,
    )

    return TracingRuntime(
        provider=provider,
        tracer=tracer,
    )


def current_trace_ids() -> tuple[str | None, str | None]:
    """Return lowercase hexadecimal trace/span IDs for the active span."""

    span = trace.get_current_span()
    context = span.get_span_context()

    if not context.is_valid:
        return None, None

    return (
        f"{context.trace_id:032x}",
        f"{context.span_id:016x}",
    )


def current_tracer() -> Tracer | None:
    """Return the request-local AeroRAG-X tracer when one is active."""

    return _CURRENT_TRACER.get()


@contextmanager
def use_tracer(
    tracer: Tracer,
) -> Iterator[None]:
    """Bind one tracer to the current execution context."""

    token = _CURRENT_TRACER.set(tracer)

    try:
        yield
    finally:
        _CURRENT_TRACER.reset(token)


@contextmanager
def trace_span(
    name: str,
) -> Iterator[Span | None]:
    """Create one request-local span, or no-op when tracing is inactive."""

    normalized_name = name.strip()

    if not normalized_name:
        raise ValueError("span name must not be blank.")

    tracer = current_tracer()

    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(
        normalized_name,
    ) as span:
        yield span
