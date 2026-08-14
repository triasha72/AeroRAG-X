"""Cross-service OpenTelemetry trace-context helpers."""

from __future__ import annotations

from opentelemetry import propagate, trace

TRACER = trace.get_tracer("aeroragx.distributed")


def inject_trace_headers() -> dict[str, str]:
    """Inject the active OpenTelemetry context into HTTP headers."""

    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


def extract_trace_context(headers: dict[str, str]) -> object:
    """Extract remote trace context for server-side span creation."""

    return propagate.extract(headers)
