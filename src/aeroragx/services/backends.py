"""Backend protocols used by containerized retrieval and inference services."""

from __future__ import annotations

from typing import Protocol

from aeroragx.services.contracts import (
    InferenceServiceRequest,
    InferenceServiceResponse,
    RetrievalServiceRequest,
    RetrievalServiceResponse,
)


class RetrievalBackend(Protocol):
    async def retrieve(
        self,
        request: RetrievalServiceRequest,
    ) -> RetrievalServiceResponse: ...


class InferenceBackend(Protocol):
    async def generate(
        self,
        request: InferenceServiceRequest,
    ) -> InferenceServiceResponse: ...
