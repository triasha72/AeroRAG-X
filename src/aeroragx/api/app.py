"""FastAPI application for AeroRAG-X."""

from __future__ import annotations

from collections.abc import (
    AsyncIterator,
    Callable,
)
from contextlib import asynccontextmanager
from typing import cast

from fastapi import (
    FastAPI,
    HTTPException,
    status,
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
from aeroragx.generation.grounded import (
    GroundedAnswer,
)
from aeroragx.runtime import RuntimeConfig

ServiceLoader = Callable[
    [RuntimeConfig],
    QueryService,
]


def create_app(
    *,
    query_service: QueryService | None = None,
    runtime_config: RuntimeConfig | None = None,
    service_loader: ServiceLoader = load_query_service,
) -> FastAPI:
    """Create the AeroRAG-X HTTP application."""

    if query_service is not None and runtime_config is not None:
        raise ValueError("Provide query_service or runtime_config, not both.")

    @asynccontextmanager
    async def lifespan(
        application: FastAPI,
    ) -> AsyncIterator[None]:
        """Load the heavy runtime once per process."""

        if query_service is None and runtime_config is not None:
            application.state.query_service = service_loader(runtime_config)

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
            raise HTTPException(
                status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
                detail=("AeroRAG-X runtime is not ready."),
            )

        return service.query(request.query)

    return app


app = create_app(
    runtime_config=RuntimeConfig(
        candidate_top_k=20,
        evidence_top_k=5,
    )
)
