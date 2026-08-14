"""Async typed HTTP clients for distributed service boundaries."""

from __future__ import annotations

import httpx

from aeroragx.services.contracts import (
    InferenceServiceRequest,
    InferenceServiceResponse,
    RetrievalServiceRequest,
    RetrievalServiceResponse,
)


class RetrievalServiceClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def retrieve(
        self,
        request: RetrievalServiceRequest,
    ) -> RetrievalServiceResponse:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/v1/retrieve",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return RetrievalServiceResponse.model_validate(response.json())


class InferenceServiceClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def generate(
        self,
        request: InferenceServiceRequest,
    ) -> InferenceServiceResponse:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/v1/generate",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return InferenceServiceResponse.model_validate(response.json())
