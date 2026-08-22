"""FastAPI application for AeroRAG-X."""

from __future__ import annotations

import logging
from collections.abc import (
    AsyncIterator,
    Callable,
)
from contextlib import asynccontextmanager
from time import perf_counter
from typing import TypedDict, cast
from uuid import uuid4

from fastapi import (
    FastAPI,
    Request,
    status,
)
from fastapi.exceptions import (
    RequestValidationError,
)
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.base import (
    RequestResponseEndpoint,
)
from starlette.responses import Response

from aeroragx.api.errors import (
    ApiErrorDetail,
    ApiErrorResponse,
    RuntimeUnavailableError,
)
from aeroragx.api.guardrails import (
    ApiGuardrailSettings,
    SlidingWindowRateLimiter,
)
from aeroragx.api.schemas import (
    HealthResponse,
    QueryRequest,
    ReadinessResponse,
)
from aeroragx.api.service import (
    QueryService,
    load_query_service,
)
from aeroragx.api.settings import (
    load_api_runtime_settings,
)
from aeroragx.generation.grounded import (
    GroundedAnswer,
)
from aeroragx.generation.structured_provider import (
    StructuredProviderError,
)
from aeroragx.observability import (
    ServiceMetrics,
    TracingRuntime,
    configure_json_logger,
    create_configured_tracing_runtime,
    current_trace_ids,
    log_event,
    use_tracer,
)
from aeroragx.runtime import RuntimeConfig

type ServiceLoader = Callable[
    [RuntimeConfig],
    QueryService,
]

_DEFAULT_EVENT_LOGGER = configure_json_logger(
    name="aeroragx.api",
)


def _runtime_mode_label(
    config: RuntimeConfig,
) -> str:
    """Return the supported API runtime mode for observability."""

    if config.provider_config is None:
        return "local"

    if config.http_transport_config is not None:
        return "openai"

    return "transformers"


class _GroundedQueryLogFields(TypedDict):
    """Typed structured fields emitted for one grounded query."""

    insufficient_evidence: bool
    claim_count: int
    citation_count: int
    source_document_count: int
    retriever: str | None
    requested_evidence_top_k: int | None
    returned_evidence_count: int | None
    used_evidence_count: int | None
    reranker_model: str | None
    generation_provider: str | None
    generation_model: str | None
    evidence_sufficient: bool | None
    provider_called: bool | None
    provider_bypassed: bool | None
    provider_succeeded: bool | None
    provider_attempts: int | None
    provider_latency_ms: float | None
    provider_request_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    prompt_injection_safe: bool | None
    prompt_injection_findings: int | None
    provider_error_type: str | None
    rag_total_ms: float | None
    retrieval_ms: float | None
    bm25_ms: float | None
    dense_ms: float | None
    hybrid_fusion_ms: float | None
    reranker_scoring_ms: float | None
    retrieval_search_count: int | None
    facet_search_count: int | None
    facet_overhead_ms: float | None
    facet_used: bool | None
    evidence_build_ms: float | None
    sufficiency_ms: float | None
    provider_stage_ms: float | None
    citation_resolution_ms: float | None


def _grounded_query_log_fields(
    answer: GroundedAnswer,
) -> _GroundedQueryLogFields:
    """Return safe operational fields for one grounded answer."""

    metadata = answer.retrieval_metadata

    fields: _GroundedQueryLogFields = {
        "insufficient_evidence": answer.insufficient_evidence,
        "claim_count": len(answer.claims),
        "citation_count": len(answer.citations),
        "source_document_count": len(answer.source_documents),
        "retriever": None,
        "requested_evidence_top_k": None,
        "returned_evidence_count": None,
        "used_evidence_count": None,
        "reranker_model": None,
        "generation_provider": None,
        "generation_model": None,
        "evidence_sufficient": None,
        "provider_called": None,
        "provider_bypassed": None,
        "provider_succeeded": None,
        "provider_attempts": None,
        "provider_latency_ms": None,
        "provider_request_id": None,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "estimated_cost_usd": None,
        "prompt_injection_safe": None,
        "prompt_injection_findings": None,
        "provider_error_type": None,
        "rag_total_ms": None,
        "retrieval_ms": None,
        "bm25_ms": None,
        "dense_ms": None,
        "hybrid_fusion_ms": None,
        "reranker_scoring_ms": None,
        "retrieval_search_count": None,
        "facet_search_count": None,
        "facet_overhead_ms": None,
        "facet_used": None,
        "evidence_build_ms": None,
        "sufficiency_ms": None,
        "provider_stage_ms": None,
        "citation_resolution_ms": None,
    }

    timings = answer.stage_timings

    if timings is not None:
        fields.update(
            {
                "rag_total_ms": timings.total_ms,
                "retrieval_ms": timings.retrieval_ms,
                "bm25_ms": timings.bm25_ms,
                "dense_ms": timings.dense_ms,
                "hybrid_fusion_ms": timings.hybrid_fusion_ms,
                "reranker_scoring_ms": timings.reranker_scoring_ms,
                "retrieval_search_count": (timings.retrieval_search_count),
                "facet_search_count": timings.facet_search_count,
                "facet_overhead_ms": timings.facet_overhead_ms,
                "facet_used": timings.facet_used,
                "evidence_build_ms": timings.evidence_build_ms,
                "sufficiency_ms": timings.sufficiency_ms,
                "provider_stage_ms": timings.provider_stage_ms,
                "citation_resolution_ms": timings.citation_resolution_ms,
            }
        )

    if metadata is None:
        return fields

    sufficiency = metadata.evidence_sufficiency
    provider = metadata.provider_telemetry

    fields.update(
        {
            "retriever": metadata.retriever,
            "requested_evidence_top_k": metadata.requested_evidence_top_k,
            "returned_evidence_count": metadata.returned_evidence_count,
            "used_evidence_count": metadata.used_evidence_count,
            "reranker_model": metadata.reranker_model,
            "generation_provider": metadata.generation_provider,
            "generation_model": metadata.generation_model,
            "evidence_sufficient": (sufficiency.sufficient if sufficiency is not None else None),
        }
    )

    provider_called = provider is not None or not answer.insufficient_evidence
    provider_bypassed = answer.insufficient_evidence and provider is None

    fields["provider_called"] = provider_called
    fields["provider_bypassed"] = provider_bypassed

    if provider is None:
        return fields

    usage = provider.usage

    fields.update(
        {
            "provider_succeeded": provider.succeeded,
            "provider_attempts": provider.attempts,
            "provider_latency_ms": round(
                provider.latency_seconds * 1000.0,
                3,
            ),
            "provider_request_id": provider.request_id,
            "input_tokens": usage.input_tokens if usage is not None else None,
            "output_tokens": usage.output_tokens if usage is not None else None,
            "total_tokens": usage.total_tokens if usage is not None else None,
            "estimated_cost_usd": provider.estimated_cost_usd,
            "prompt_injection_safe": provider.prompt_injection_safe,
            "prompt_injection_findings": provider.prompt_injection_findings,
            "provider_error_type": provider.error_type,
        }
    )

    return fields


def create_app(
    *,
    query_service: QueryService | None = None,
    runtime_config: RuntimeConfig | None = None,
    service_loader: ServiceLoader = load_query_service,
    event_logger: logging.Logger | None = None,
    service_metrics: ServiceMetrics | None = None,
    tracing_runtime: TracingRuntime | None = None,
    guardrail_settings: ApiGuardrailSettings | None = None,
) -> FastAPI:
    """Create the AeroRAG-X HTTP application."""

    if query_service is not None and runtime_config is not None:
        raise ValueError("Provide query_service or runtime_config, not both.")

    logger = _DEFAULT_EVENT_LOGGER if event_logger is None else event_logger
    metrics = ServiceMetrics() if service_metrics is None else service_metrics
    owns_tracing_runtime = tracing_runtime is None
    trace_runtime = (
        create_configured_tracing_runtime() if tracing_runtime is None else tracing_runtime
    )
    guardrails = ApiGuardrailSettings() if guardrail_settings is None else guardrail_settings
    rate_limiter = SlidingWindowRateLimiter(
        limit=guardrails.rate_limit_requests,
        window_seconds=guardrails.rate_limit_window_seconds,
    )

    @asynccontextmanager
    async def lifespan(
        application: FastAPI,
    ) -> AsyncIterator[None]:
        """Load the heavy runtime once per process."""

        if query_service is None and runtime_config is not None:
            runtime_mode = _runtime_mode_label(runtime_config)
            started_at = perf_counter()

            log_event(
                logger,
                "runtime_load_started",
                runtime_mode=runtime_mode,
                dense_backend=runtime_config.dense_backend,
                candidate_top_k=runtime_config.candidate_top_k,
                evidence_top_k=runtime_config.evidence_top_k,
            )

            try:
                loaded_service = service_loader(runtime_config)

            except Exception as exc:
                duration_ms = round(
                    (perf_counter() - started_at) * 1000.0,
                    3,
                )

                log_event(
                    logger,
                    "runtime_load_failed",
                    level=logging.ERROR,
                    runtime_mode=runtime_mode,
                    dense_backend=runtime_config.dense_backend,
                    candidate_top_k=runtime_config.candidate_top_k,
                    evidence_top_k=runtime_config.evidence_top_k,
                    duration_ms=duration_ms,
                    succeeded=False,
                    error_type=type(exc).__name__,
                )

                raise

            application.state.query_service = loaded_service

            duration_ms = round(
                (perf_counter() - started_at) * 1000.0,
                3,
            )

            log_event(
                logger,
                "runtime_load_completed",
                runtime_mode=runtime_mode,
                dense_backend=runtime_config.dense_backend,
                candidate_top_k=runtime_config.candidate_top_k,
                evidence_top_k=runtime_config.evidence_top_k,
                duration_ms=duration_ms,
                succeeded=True,
            )

        try:
            yield

        finally:
            application.state.query_service = None

            if owns_tracing_runtime:
                trace_runtime.shutdown()

    app = FastAPI(
        title="AeroRAG-X",
        version="0.1.0",
        description=("Evidence-grounded aerospace retrieval-augmented generation API."),
        lifespan=lifespan,
    )

    app.state.query_service = query_service
    app.state.service_metrics = metrics
    app.state.tracing_runtime = trace_runtime

    def current_query_service() -> QueryService | None:
        """Return the currently loaded service."""

        return cast(
            QueryService | None,
            app.state.query_service,
        )

    def current_request_id(
        request: Request,
    ) -> str:
        """Return the current request identifier."""

        return cast(
            str,
            request.state.request_id,
        )

    def metric_route(
        request: Request,
    ) -> str:
        """Return one bounded route label for Prometheus metrics."""

        route = request.scope.get("route")
        route_path = getattr(route, "path", None)

        if isinstance(route_path, str):
            return route_path

        return "__unmatched__"

    def milliseconds_to_seconds(
        value: float | None,
    ) -> float | None:
        """Convert optional millisecond telemetry to seconds."""

        if value is None:
            return None

        return value / 1000.0

    def record_grounded_answer_metrics(
        answer: GroundedAnswer,
    ) -> None:
        """Record aggregate metrics for one successful grounded query."""

        timings = answer.stage_timings

        metrics.record_query_completed(
            insufficient_evidence=answer.insufficient_evidence,
            rag_duration_seconds=(
                milliseconds_to_seconds(timings.total_ms) if timings is not None else None
            ),
            retrieval_duration_seconds=(
                milliseconds_to_seconds(timings.retrieval_ms) if timings is not None else None
            ),
            reranker_duration_seconds=(
                milliseconds_to_seconds(timings.reranker_scoring_ms)
                if timings is not None
                else None
            ),
        )

        metadata = answer.retrieval_metadata

        if metadata is None:
            return

        provider_telemetry = metadata.provider_telemetry
        provider_name = metadata.generation_provider or "unknown"

        if provider_telemetry is not None:
            metrics.record_provider_call(
                provider=provider_name,
                duration_seconds=provider_telemetry.latency_seconds,
                succeeded=provider_telemetry.succeeded,
            )
            return

        if answer.insufficient_evidence:
            metrics.record_provider_bypass()
            return

        metrics.record_provider_call(
            provider=provider_name,
            duration_seconds=(
                milliseconds_to_seconds(timings.provider_stage_ms) if timings is not None else None
            ),
            succeeded=True,
        )

    def error_response(
        *,
        request: Request,
        status_code: int,
        code: str,
        message: str,
    ) -> JSONResponse:
        """Build one stable structured API error."""

        request_id = current_request_id(request)

        payload = ApiErrorResponse(
            error=ApiErrorDetail(
                code=code,
                message=message,
                request_id=request_id,
            )
        )

        return JSONResponse(
            status_code=status_code,
            content=payload.model_dump(),
            headers={
                "X-Request-ID": request_id,
            },
        )

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Attach one request ID and emit one structured request event."""

        request_id = str(uuid4())
        started_at = perf_counter()

        request.state.request_id = request_id

        server_span = trace.get_current_span()

        if server_span.is_recording():
            server_span.set_attribute(
                "aeroragx.request_id",
                request_id,
            )

        with use_tracer(trace_runtime.tracer):
            response: Response
            try:
                if request.url.path == "/v1/query":
                    guardrail_response: Response | None = None
                    raw_content_length = request.headers.get("content-length")

                    if raw_content_length is not None:
                        try:
                            content_length = int(raw_content_length)

                        except ValueError:
                            content_length = guardrails.max_request_bytes + 1

                        if content_length > guardrails.max_request_bytes:
                            guardrail_response = error_response(
                                request=request,
                                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                                code="request_too_large",
                                message="The request body exceeds the configured size limit.",
                            )

                    if guardrail_response is None:
                        client_key = (
                            request.client.host if request.client is not None else "unknown"
                        )
                        decision = rate_limiter.check(key=client_key)

                        if not decision.allowed:
                            response = error_response(
                                request=request,
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                code="rate_limit_exceeded",
                                message="The query rate limit has been exceeded.",
                            )
                            response.headers["Retry-After"] = str(
                                decision.retry_after_seconds,
                            )

                        else:
                            response = await call_next(request)

                        response.headers["X-RateLimit-Limit"] = str(decision.limit)
                        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)

                    else:
                        response = guardrail_response

                else:
                    response = await call_next(request)

            except Exception:
                elapsed_seconds = perf_counter() - started_at
                duration_ms = round(
                    elapsed_seconds * 1000.0,
                    3,
                )
                trace_id, span_id = current_trace_ids()

                metrics.record_http_request(
                    method=request.method,
                    route=metric_route(request),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    duration_seconds=elapsed_seconds,
                )

                log_event(
                    logger,
                    "http_request_failed",
                    request_id=request_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    duration_ms=duration_ms,
                    succeeded=False,
                )

                raise

            elapsed_seconds = perf_counter() - started_at
            duration_ms = round(
                elapsed_seconds * 1000.0,
                3,
            )

            response.headers["X-Request-ID"] = request_id
            trace_id, span_id = current_trace_ids()

            metrics.record_http_request(
                method=request.method,
                route=metric_route(request),
                status_code=response.status_code,
                duration_seconds=elapsed_seconds,
            )

            log_event(
                logger,
                "http_request_completed",
                request_id=request_id,
                trace_id=trace_id,
                span_id=span_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                succeeded=response.status_code < 400,
            )

            return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        """Return a stable validation error."""

        del error

        return error_response(
            request=request,
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            code="invalid_request",
            message=("Request validation failed."),
        )

    @app.exception_handler(RuntimeUnavailableError)
    async def runtime_error_handler(
        request: Request,
        error: RuntimeUnavailableError,
    ) -> JSONResponse:
        """Return runtime-unavailable response."""

        return error_response(
            request=request,
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            code="runtime_unavailable",
            message=str(error),
        )

    @app.exception_handler(StructuredProviderError)
    async def provider_error_handler(
        request: Request,
        error: StructuredProviderError,
    ) -> JSONResponse:
        """Hide provider details behind a stable API error."""

        del error

        metrics.record_provider_call(
            provider="unknown",
            duration_seconds=None,
            succeeded=False,
        )

        return error_response(
            request=request,
            status_code=(status.HTTP_502_BAD_GATEWAY),
            code="provider_failure",
            message=("The generation provider failed to complete the request."),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        """Return a safe internal-error response."""

        del error

        return error_response(
            request=request,
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            code="internal_error",
            message=("An unexpected internal error occurred."),
        )

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
    )
    def health() -> HealthResponse:
        """Return process health."""

        return HealthResponse(
            status="ok",
        )

    @app.get(
        "/ready",
        response_model=ReadinessResponse,
        tags=["system"],
    )
    def ready() -> ReadinessResponse:
        """Return runtime readiness."""

        is_ready = current_query_service() is not None

        return ReadinessResponse(
            status=("ready" if is_ready else "not_ready"),
            ready=is_ready,
        )

    @app.get(
        "/metrics",
        include_in_schema=False,
        tags=["system"],
    )
    def prometheus_metrics() -> Response:
        """Expose Prometheus-compatible service metrics."""

        return Response(
            content=generate_latest(metrics.registry),
            headers={
                "Content-Type": CONTENT_TYPE_LATEST,
            },
        )

    @app.post(
        "/v1/query",
        response_model=GroundedAnswer,
        tags=["generation"],
    )
    def grounded_query(
        request: QueryRequest,
        http_request: Request,
    ) -> GroundedAnswer:
        """Answer one query using grounded evidence."""

        metrics.record_query_started()
        request_id = current_request_id(http_request)

        with trace_runtime.tracer.start_as_current_span(
            "aeroragx.query",
        ) as query_span:
            query_span.set_attribute(
                "aeroragx.request_id",
                request_id,
            )

            try:
                service = current_query_service()

                if service is None:
                    raise RuntimeUnavailableError("AeroRAG-X runtime is not ready.")

                answer = service.query(request.query)

            except Exception:
                metrics.record_query_error()
                query_span.set_status(
                    Status(StatusCode.ERROR),
                )
                raise

            record_grounded_answer_metrics(answer)

            query_span.set_attribute(
                "aeroragx.insufficient_evidence",
                answer.insufficient_evidence,
            )
            query_span.set_attribute(
                "aeroragx.claim_count",
                len(answer.claims),
            )
            query_span.set_attribute(
                "aeroragx.citation_count",
                len(answer.citations),
            )

            metadata = answer.retrieval_metadata

            if metadata is not None and metadata.generation_provider is not None:
                query_span.set_attribute(
                    "aeroragx.generation_provider",
                    metadata.generation_provider,
                )

            trace_id, span_id = current_trace_ids()

            log_event(
                logger,
                "grounded_query_completed",
                request_id=request_id,
                trace_id=trace_id,
                span_id=span_id,
                **_grounded_query_log_fields(answer),
            )

            return answer

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace_runtime.provider,
        excluded_urls="health,ready,metrics",
    )

    return app


_api_settings = load_api_runtime_settings()

app = create_app(
    runtime_config=_api_settings.to_runtime_config(),
    guardrail_settings=_api_settings.guardrails,
)
