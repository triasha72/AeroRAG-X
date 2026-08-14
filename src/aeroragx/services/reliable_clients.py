"""Reliable wrappers over typed retrieval and inference service clients."""

from __future__ import annotations

import httpx

from aeroragx.services.clients import (
    InferenceServiceClient,
    RetrievalServiceClient,
)
from aeroragx.services.contracts import (
    InferenceServiceRequest,
    InferenceServiceResponse,
    RetrievalServiceRequest,
    RetrievalServiceResponse,
)
from aeroragx.services.retry_policy import AsyncRetryPolicy, run_with_retry


def retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


class ReliableRetrievalClient:
    def __init__(
        self,
        client: RetrievalServiceClient,
        *,
        policy: AsyncRetryPolicy,
    ) -> None:
        self._client = client
        self._policy = policy

    async def retrieve(
        self,
        request: RetrievalServiceRequest,
    ) -> RetrievalServiceResponse:
        return await run_with_retry(
            lambda: self._client.retrieve(request),
            policy=self._policy,
            retryable=retryable_http_error,
        )


class ReliableInferenceClient:
    def __init__(
        self,
        client: InferenceServiceClient,
        *,
        policy: AsyncRetryPolicy,
    ) -> None:
        self._client = client
        self._policy = policy

    async def generate(
        self,
        request: InferenceServiceRequest,
    ) -> InferenceServiceResponse:
        return await run_with_retry(
            lambda: self._client.generate(request),
            policy=self._policy,
            retryable=retryable_http_error,
        )
