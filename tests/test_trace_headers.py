"""Smoke test for OpenTelemetry carrier creation."""

from aeroragx.observability.distributed_tracing import inject_trace_headers


def test_trace_header_injection_returns_mapping() -> None:
    assert isinstance(inject_trace_headers(), dict)
