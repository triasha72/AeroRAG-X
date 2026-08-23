"""Structured transport shared by OpenAI-compatible local serving engines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)

EngineName = Literal["sglang", "tensorrt-llm"]


class CompatibleServingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = "0.1"
    engine: EngineName
    endpoint_url: HttpUrl
    api_key: str | None = None
    max_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0.0, ge=0.0)
    seed: int = 20260810


def load_compatible_serving_config(path: Path) -> CompatibleServingConfig:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Serving configuration must contain a YAML mapping.")
    return CompatibleServingConfig.model_validate(value)


class OpenAICompatibleStructuredTransport:
    """Call an engine's OpenAI-compatible chat endpoint with JSON guidance."""

    def __init__(
        self,
        *,
        model_name: str,
        config: CompatibleServingConfig,
        client: httpx.Client | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be blank.")
        self._model_name = model_name.strip()
        self._config = config
        self._client = client or httpx.Client()

    def complete(
        self, *, request: StructuredModelRequest, timeout_seconds: float
    ) -> StructuredModelResult:
        if request.model_name != self._model_name:
            raise ProviderTransportError("Served model does not match request model.", retryable=False)
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            "seed": self._config.seed,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        try:
            response = self._client.post(
                str(self._config.endpoint_url), json=payload, headers=headers, timeout=timeout_seconds
            )
            response.raise_for_status()
            body = response.json()
            result = json.loads(body["choices"][0]["message"]["content"])
            usage = body.get("usage", {})
        except httpx.TimeoutException as exc:
            raise ProviderTransportError(
                f"{self._config.engine} request timed out.", retryable=True
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderTransportError(
                f"{self._config.engine} returned HTTP {status}.",
                retryable=status in {408, 425, 429} or status >= 500,
            ) from exc
        except (httpx.RequestError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderTransportError(
                f"{self._config.engine} returned an invalid completion.", retryable=False
            ) from exc
        if not isinstance(result, dict):
            raise ProviderTransportError("Structured completion was not an object.", retryable=False)
        return StructuredModelResult(
            payload=result,
            request_id=response.headers.get("x-request-id"),
            usage=ProviderUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            ),
        )
