"""Container entry point for the retrieval service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from aeroragx.services.backends import RetrievalBackend
from aeroragx.services.contracts import (
    RetrievalServiceRequest,
    RetrievalServiceResponse,
)
from aeroragx.services.health import HealthResponse


def create_app(backend: RetrievalBackend | None = None) -> FastAPI:
    app = FastAPI(title="AeroRAG-X Retrieval Service")

    @app.get("/health/live", response_model=HealthResponse)
    async def live() -> HealthResponse:
        return HealthResponse(status="ok", ready=True)

    @app.get("/health/ready", response_model=HealthResponse)
    async def ready() -> HealthResponse:
        return HealthResponse(
            status="ok" if backend is not None else "degraded",
            ready=backend is not None,
        )

    @app.post("/v1/retrieve", response_model=RetrievalServiceResponse)
    async def retrieve(
        request: RetrievalServiceRequest,
    ) -> RetrievalServiceResponse:
        if backend is None:
            raise HTTPException(status_code=503, detail="retrieval backend unavailable")
        return await backend.retrieve(request)

    return app


app = create_app()
