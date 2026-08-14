"""Container entry point for the inference service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from aeroragx.services.backends import InferenceBackend
from aeroragx.services.contracts import (
    InferenceServiceRequest,
    InferenceServiceResponse,
)
from aeroragx.services.health import HealthResponse


def create_app(backend: InferenceBackend | None = None) -> FastAPI:
    app = FastAPI(title="AeroRAG-X Inference Service")

    @app.get("/health/live", response_model=HealthResponse)
    async def live() -> HealthResponse:
        return HealthResponse(status="ok", ready=True)

    @app.get("/health/ready", response_model=HealthResponse)
    async def ready() -> HealthResponse:
        return HealthResponse(
            status="ok" if backend is not None else "degraded",
            ready=backend is not None,
        )

    @app.post("/v1/generate", response_model=InferenceServiceResponse)
    async def generate(
        request: InferenceServiceRequest,
    ) -> InferenceServiceResponse:
        if backend is None:
            raise HTTPException(status_code=503, detail="inference backend unavailable")
        return await backend.generate(request)

    return app


app = create_app()
