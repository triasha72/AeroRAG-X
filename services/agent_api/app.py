"""Container entry point for the distributed Agent API."""

from __future__ import annotations

import os

from fastapi import FastAPI

from aeroragx.services.clients import (
    InferenceServiceClient,
    RetrievalServiceClient,
)
from aeroragx.services.contracts import (
    AgentServiceRequest,
    AgentServiceResponse,
)
from aeroragx.services.distributed_agent import DistributedAgentService
from aeroragx.services.health import HealthResponse


def create_app(service: DistributedAgentService | None = None) -> FastAPI:
    app = FastAPI(title="AeroRAG-X Agent API")

    if service is None:
        retrieval_url = os.getenv("AERORAGX_RETRIEVAL_SERVICE_URL")
        inference_url = os.getenv("AERORAGX_INFERENCE_SERVICE_URL")
        if retrieval_url and inference_url:
            service = DistributedAgentService(
                retrieval_client=RetrievalServiceClient(retrieval_url),
                inference_client=InferenceServiceClient(inference_url),
            )

    @app.get("/health/live", response_model=HealthResponse)
    async def live() -> HealthResponse:
        return HealthResponse(status="ok", ready=True)

    @app.get("/health/ready", response_model=HealthResponse)
    async def ready() -> HealthResponse:
        return HealthResponse(
            status="ok" if service is not None else "degraded",
            ready=service is not None,
        )

    @app.post("/v1/query", response_model=AgentServiceResponse)
    async def query(request: AgentServiceRequest) -> AgentServiceResponse:
        if service is None:
            return AgentServiceResponse(
                context=request.context,
                answer=None,
                termination_reason="unrecoverable_tool_failure",
            )
        return await service.query(request)

    return app


app = create_app()
