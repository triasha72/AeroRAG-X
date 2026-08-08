"""Prometheus metrics primitives for AeroRAG-X service observability."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram

_DEFAULT_DURATION_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    20.0,
    30.0,
)


def _validate_duration_seconds(value: float) -> None:
    if value < 0.0:
        raise ValueError("duration_seconds must be non-negative.")


def _status_class(status_code: int) -> str:
    if 100 <= status_code <= 599:
        return f"{status_code // 100}xx"

    return "other"


class ServiceMetrics:
    """Low-cardinality Prometheus metrics owned by one AeroRAG-X app."""

    def __init__(
        self,
        registry: CollectorRegistry | None = None,
    ) -> None:
        self.registry = registry if registry is not None else CollectorRegistry()

        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests handled by AeroRAG-X.",
            labelnames=("method", "route", "status_class"),
            namespace="aeroragx",
            registry=self.registry,
        )
        self.query_requests_total = Counter(
            "query_requests_total",
            "Total grounded query requests started.",
            namespace="aeroragx",
            registry=self.registry,
        )
        self.query_success_total = Counter(
            "query_success_total",
            "Total grounded query requests completed successfully.",
            namespace="aeroragx",
            registry=self.registry,
        )
        self.query_errors_total = Counter(
            "query_errors_total",
            "Total grounded query requests that failed.",
            namespace="aeroragx",
            registry=self.registry,
        )
        self.insufficient_evidence_total = Counter(
            "insufficient_evidence_total",
            "Total grounded queries refused for insufficient evidence.",
            namespace="aeroragx",
            registry=self.registry,
        )
        self.provider_calls_total = Counter(
            "provider_calls_total",
            "Total generation-provider calls.",
            labelnames=("provider",),
            namespace="aeroragx",
            registry=self.registry,
        )
        self.provider_bypasses_total = Counter(
            "provider_bypasses_total",
            "Total grounded queries that bypassed generation providers.",
            namespace="aeroragx",
            registry=self.registry,
        )
        self.provider_errors_total = Counter(
            "provider_errors_total",
            "Total failed generation-provider calls.",
            labelnames=("provider",),
            namespace="aeroragx",
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds.",
            labelnames=("method", "route"),
            namespace="aeroragx",
            registry=self.registry,
            buckets=_DEFAULT_DURATION_BUCKETS,
        )
        self.rag_duration_seconds = Histogram(
            "rag_duration_seconds",
            "End-to-end grounded RAG duration in seconds.",
            namespace="aeroragx",
            registry=self.registry,
            buckets=_DEFAULT_DURATION_BUCKETS,
        )
        self.retrieval_duration_seconds = Histogram(
            "retrieval_duration_seconds",
            "Grounded retrieval duration in seconds.",
            namespace="aeroragx",
            registry=self.registry,
            buckets=_DEFAULT_DURATION_BUCKETS,
        )
        self.reranker_duration_seconds = Histogram(
            "reranker_duration_seconds",
            "Cross-encoder reranker duration in seconds.",
            namespace="aeroragx",
            registry=self.registry,
            buckets=_DEFAULT_DURATION_BUCKETS,
        )
        self.provider_duration_seconds = Histogram(
            "provider_duration_seconds",
            "Generation-provider duration in seconds.",
            labelnames=("provider",),
            namespace="aeroragx",
            registry=self.registry,
            buckets=_DEFAULT_DURATION_BUCKETS,
        )

    def record_http_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record one HTTP request using only bounded-cardinality labels."""

        _validate_duration_seconds(duration_seconds)

        normalized_method = method.upper()
        status_class = _status_class(status_code)

        self.http_requests_total.labels(
            method=normalized_method,
            route=route,
            status_class=status_class,
        ).inc()
        self.http_request_duration_seconds.labels(
            method=normalized_method,
            route=route,
        ).observe(duration_seconds)

    def record_query_started(self) -> None:
        """Increment the grounded-query request counter."""

        self.query_requests_total.inc()

    def record_query_completed(
        self,
        *,
        insufficient_evidence: bool,
        rag_duration_seconds: float | None = None,
        retrieval_duration_seconds: float | None = None,
        reranker_duration_seconds: float | None = None,
    ) -> None:
        """Record a successfully completed grounded query."""

        for value in (
            rag_duration_seconds,
            retrieval_duration_seconds,
            reranker_duration_seconds,
        ):
            if value is not None:
                _validate_duration_seconds(value)

        self.query_success_total.inc()

        if insufficient_evidence:
            self.insufficient_evidence_total.inc()

        if rag_duration_seconds is not None:
            self.rag_duration_seconds.observe(
                rag_duration_seconds,
            )

        if retrieval_duration_seconds is not None:
            self.retrieval_duration_seconds.observe(
                retrieval_duration_seconds,
            )

        if reranker_duration_seconds is not None:
            self.reranker_duration_seconds.observe(
                reranker_duration_seconds,
            )

    def record_query_error(self) -> None:
        """Increment the grounded-query error counter."""

        self.query_errors_total.inc()

    def record_provider_call(
        self,
        *,
        provider: str,
        duration_seconds: float | None = None,
        succeeded: bool,
    ) -> None:
        """Record one provider call and optional latency."""

        if duration_seconds is not None:
            _validate_duration_seconds(duration_seconds)

        self.provider_calls_total.labels(
            provider=provider,
        ).inc()

        if duration_seconds is not None:
            self.provider_duration_seconds.labels(
                provider=provider,
            ).observe(duration_seconds)

        if not succeeded:
            self.provider_errors_total.labels(
                provider=provider,
            ).inc()

    def record_provider_bypass(self) -> None:
        """Increment the provider-bypass counter."""

        self.provider_bypasses_total.inc()
