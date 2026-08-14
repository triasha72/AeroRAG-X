"""Tests for structured service error contracts."""

from aeroragx.services.errors import ServiceErrorEnvelope


def test_dependency_failure_can_be_marked_retryable() -> None:
    error = ServiceErrorEnvelope(
        code="dependency_unavailable",
        message="retrieval service unavailable",
        retryable=True,
    )
    assert error.retryable is True
