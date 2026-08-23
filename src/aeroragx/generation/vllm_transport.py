"""OpenAI-compatible vLLM transport for structured grounded generation."""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)


class VLLMRuntimeConfig(BaseModel):
    """Configuration for a separately managed vLLM OpenAI server."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = "0.1"
    endpoint_url: HttpUrl = "http://127.0.0.1:8000/v1/chat/completions"
    api_key: str | None = None
    max_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0.0, ge=0.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    seed: int = 20260810
    enable_prefix_caching: bool = True


def load_vllm_runtime_config(path: Path) -> VLLMRuntimeConfig:
    """Load and validate vLLM runtime configuration."""

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("vLLM runtime configuration must contain a YAML mapping.")
    return VLLMRuntimeConfig.model_validate(value)


class VLLMStructuredModelTransport:
    """Send structured requests to vLLM without changing the RAG pipeline."""

    def __init__(
        self,
        *,
        model_name: str,
        config: VLLMRuntimeConfig,
        client: httpx.Client | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be blank.")
        self._model_name = model_name.strip()
        self._config = config
        self._client = httpx.Client() if client is None else client
        self._owns_client = client is None

    def complete(
        self, *, request: StructuredModelRequest, timeout_seconds: float
    ) -> StructuredModelResult:
        """Complete one grounded request using vLLM's guided JSON schema."""

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if request.model_name != self._model_name:
            raise ProviderTransportError(
                "Structured request model does not match the vLLM served model.",
                retryable=False,
            )
        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
            "seed": self._config.seed,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "aeroragx_grounded_answer",
                    "schema": request.response_schema,
                },
            },
        }
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        try:
            response = self._client.post(
                str(self._config.endpoint_url),
                json=payload,
                headers=headers,
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTransportError("vLLM request timed out.", retryable=True) from exc
        except httpx.RequestError as exc:
            raise ProviderTransportError("vLLM request failed.", retryable=True) from exc
        if not response.is_success:
            raise ProviderTransportError(
                f"vLLM returned HTTP {response.status_code}.",
                retryable=response.status_code in {408, 425, 429} or response.status_code >= 500,
            )
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
            result = json.loads(text)
            usage = body.get("usage", {})
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderTransportError(
                "vLLM returned an invalid structured completion.", retryable=False
            ) from exc
        if not isinstance(result, dict):
            raise ProviderTransportError("vLLM JSON completion was not an object.", retryable=False)
        return StructuredModelResult(
            payload=result,
            request_id=response.headers.get("x-request-id"),
            usage=ProviderUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            ),
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        self.close()
