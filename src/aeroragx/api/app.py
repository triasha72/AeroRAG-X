"""FastAPI application for AeroRAG-X."""

from __future__ import annotations

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
from aeroragx.api.service import QueryService
from aeroragx.generation.grounded import (
    GroundedAnswer,
)


def create_app(
    *,
    query_service: QueryService | None = None,
) -> FastAPI:
    """Create the AeroRAG-X HTTP application."""

    app = FastAPI(
        title="AeroRAG-X",
        version="0.1.0",
        description=("Evidence-grounded aerospace retrieval-augmented generation API."),
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

        is_ready = query_service is not None

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

        if query_service is None:
            raise HTTPException(
                status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
                detail=("AeroRAG-X runtime is not ready."),
            )

        return query_service.query(request.query)

    return app


app = create_app()
