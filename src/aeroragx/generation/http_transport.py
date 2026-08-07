"""HTTP transport for structured generation model requests."""

from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType
from typing import Self

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from aeroragx.generation.model_adapter import (
    GenericStructuredModelAdapter,
    StructuredModelAdapter,
)
from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    StructuredModelRequest,
    StructuredModelResult,
)


class HttpTransportConfig(BaseModel):
    """Configuration for the provider-neutral structured HTTP transport."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    endpoint_url: HttpUrl
    api_key_env_var: str | None = Field(
        default=None,
        min_length=1,
    )
    authorization_scheme: str = Field(
        default="Bearer",
        min_length=1,
    )
    request_id_header: str = Field(
        default="x-request-id",
        min_length=1,
    )
    user_agent: str = Field(
        default="AeroRAG-X/0.1.0",
        min_length=1,
    )


def load_http_transport_config(
    path: Path,
) -> HttpTransportConfig:
    """Load and validate structured HTTP transport configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("HTTP transport configuration must contain a YAML mapping.")

    return HttpTransportConfig.model_validate(raw_data)


class HttpStructuredModelTransport:
    """POST structured-model requests to a JSON HTTP endpoint."""

    def __init__(
        self,
        *,
        config: HttpTransportConfig,
        adapter: StructuredModelAdapter | None = None,
        client: httpx.Client | None = None,
        environment: dict[str, str] | None = None,
    ) -> None:
        self._config = config
        self._adapter = GenericStructuredModelAdapter() if adapter is None else adapter
        self._environment = os.environ if environment is None else environment

        self._api_key = self._resolve_api_key()

        if client is None:
            self._client = httpx.Client()
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    @property
    def config(self) -> HttpTransportConfig:
        """Return a defensive copy of transport configuration."""

        return self._config.model_copy(deep=True)

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Execute one HTTP request and parse the provider result."""

        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive.")

        headers = self._build_headers()
        payload = self._adapter.build_request_payload(request)

        try:
            response = self._client.post(
                str(self._config.endpoint_url),
                json=payload,
                headers=headers,
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise ProviderTransportError(
                "Structured model request timed out.",
                retryable=True,
            ) from error
        except httpx.RequestError as error:
            raise ProviderTransportError(
                "Structured model request failed before receiving a response.",
                retryable=True,
            ) from error

        if not response.is_success:
            raise ProviderTransportError(
                (f"Structured model endpoint returned HTTP {response.status_code}."),
                retryable=(_is_retryable_status(response.status_code)),
            )

        try:
            data = response.json()
        except ValueError as error:
            raise ProviderTransportError(
                "Structured model endpoint returned invalid JSON.",
                retryable=False,
            ) from error

        if not isinstance(data, dict):
            raise ProviderTransportError(
                "Structured model endpoint returned a non-object JSON response.",
                retryable=False,
            )

        fallback_request_id = _normalized_header(
            response,
            self._config.request_id_header,
        )

        return self._adapter.parse_response(
            _string_key_dict(data),
            fallback_request_id=(fallback_request_id),
        )

    def close(self) -> None:
        """Close the internally owned HTTP client."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        """Return this transport as a context manager."""

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close internally created HTTP resources."""

        del exc_type
        del exc_value
        del traceback

        self.close()

    def _resolve_api_key(
        self,
    ) -> str | None:
        """Resolve the configured API key."""

        variable_name = self._config.api_key_env_var

        if variable_name is None:
            return None

        value = self._environment.get(variable_name)

        if value is None or not value.strip():
            raise ValueError("Configured provider API-key environment variable is missing.")

        return value.strip()

    def _build_headers(
        self,
    ) -> dict[str, str]:
        """Build HTTP request headers."""

        headers = {
            "Accept": "application/json",
            "Content-Type": ("application/json"),
            "User-Agent": (self._config.user_agent),
        }

        if self._api_key is not None:
            headers["Authorization"] = f"{self._config.authorization_scheme} {self._api_key}"

        return headers


def _is_retryable_status(
    status_code: int,
) -> bool:
    """Return whether an HTTP status is safe to retry."""

    return (
        status_code
        in {
            408,
            425,
            429,
        }
        or 500 <= status_code <= 599
    )


def _normalized_header(
    response: httpx.Response,
    name: str,
) -> str | None:
    """Return one normalized response header."""

    value = response.headers.get(name)

    if value is None:
        return None

    return value.strip() or None


def _string_key_dict(
    value: dict[object, object],
) -> dict[str, object]:
    """Return a dictionary while rejecting non-string keys."""

    result: dict[str, object] = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise ProviderTransportError(
                "Structured model endpoint returned a non-string object key.",
                retryable=False,
            )

        result[key] = item

    return result
