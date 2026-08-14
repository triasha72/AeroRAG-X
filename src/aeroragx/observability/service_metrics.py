"""Prometheus metrics for distributed service calls."""

from prometheus_client import Counter, Histogram

SERVICE_REQUESTS = Counter(
    "aeroragx_service_requests_total",
    "Cross-service request count.",
    ["service", "operation", "status"],
)

SERVICE_LATENCY = Histogram(
    "aeroragx_service_request_latency_seconds",
    "Cross-service request latency.",
    ["service", "operation"],
)

SAFE_DEGRADATIONS = Counter(
    "aeroragx_safe_degradations_total",
    "Requests terminated safely after dependency failure.",
    ["dependency"],
)
