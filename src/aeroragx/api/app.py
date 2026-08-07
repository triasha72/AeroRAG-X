"""FastAPI application for AeroRAG-X."""

from __future__ import annotations

from fastapi import FastAPI

from aeroragx.api.schemas import (
    HealthResponse,
    ReadinessResponse,
)


def create_app() -> FastAPI:
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
        """Return API readiness.

        Retrieval/generation runtime readiness
        will be added in the next checkpoint.
        """

        return ReadinessResponse(
            status="ready",
            ready=True,
        )

    return app


app = create_app()
