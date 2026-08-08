"""FastAPI application for AeroRAG-X."""

from __future__ import annotations

import logging
from collections.abc import (
    AsyncIterator,
    Callable,
)
from contextlib import asynccontextmanager
from time import perf_counter
from typing import cast
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
from starlette.middleware.base import (
    RequestResponseEndpoint,
)
from starlette.responses import Response

from aeroragx.api.errors import (
    ApiErrorDetail,
    ApiErrorResponse,
    RuntimeUnavailableError,
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
    configure_json_logger,
    log_event,
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
    "Return the supported API runtime mode for observability."

    return "openai" if config.provider_config is not None else "local"


def create_app(
    *,
    query_service: QueryService | None = None,
    runtime_config: RuntimeConfig | None = None,
    service_loader: ServiceLoader = load_query_service,
    event_logger: logging.Logger | None = None,
) -> FastAPI:
    """Create the AeroRAG-X HTTP application."""

    if query_service is not None and runtime_config is not None:
        raise ValueError("Provide query_service or runtime_config, not both.")

    logger = _DEFAULT_EVENT_LOGGER if event_logger is None else event_logger

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
                candidate_top_k=runtime_config.candidate_top_k,
                evidence_top_k=runtime_config.evidence_top_k,
                duration_ms=duration_ms,
                succeeded=True,
            )

        try:
            yield

        finally:
            application.state.query_service = None

    app = FastAPI(
        title="AeroRAG-X",
        version="0.1.0",
        description=("Evidence-grounded aerospace retrieval-augmented generation API."),
        lifespan=lifespan,
    )

    app.state.query_service = query_service

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

        try:
            response = await call_next(request)

        except Exception:
            duration_ms = round(
                (perf_counter() - started_at) * 1000.0,
                3,
            )

            log_event(
                logger,
                "http_request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                duration_ms=duration_ms,
                succeeded=False,
            )

            raise

        duration_ms = round(
            (perf_counter() - started_at) * 1000.0,
            3,
        )

        response.headers["X-Request-ID"] = request_id

        log_event(
            logger,
            "http_request_completed",
            request_id=request_id,
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

    @app.post(
        "/v1/query",
        response_model=GroundedAnswer,
        tags=["generation"],
    )
    def grounded_query(
        request: QueryRequest,
    ) -> GroundedAnswer:
        """Answer one query using grounded evidence."""

        service = current_query_service()

        if service is None:
            raise RuntimeUnavailableError("AeroRAG-X runtime is not ready.")

        return service.query(request.query)

    return app


app = create_app(runtime_config=(load_api_runtime_settings().to_runtime_config()))
