"""Tests for the structured HTTP model transport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from aeroragx.generation.http_transport import (
    HttpStructuredModelTransport,
    HttpTransportConfig,
    load_http_transport_config,
)
from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    StructuredModelRequest,
)


def make_config(
    **overrides: object,
) -> HttpTransportConfig:
    """Build one valid HTTP transport config."""

    values: dict[str, object] = {
        "version": "0.1",
        "endpoint_url": ("https://provider.example/v1/generate"),
        "api_key_env_var": "TEST_API_KEY",
        "authorization_scheme": "Bearer",
        "request_id_header": "x-request-id",
        "user_agent": "AeroRAG-X-Test/0.1",
    }
    values.update(overrides)

    return HttpTransportConfig.model_validate(values)


def make_request() -> StructuredModelRequest:
    """Create one structured model request."""

    return StructuredModelRequest(
        model_name="test-model",
        system_prompt="System instructions.",
        user_prompt="User evidence.",
        response_schema={
            "type": "object",
        },
    )


def test_load_http_transport_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "http.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            "endpoint_url: "
            '"https://provider.example/v1/generate"\n'
            'api_key_env_var: "TEST_API_KEY"\n'
            'authorization_scheme: "Bearer"\n'
            'request_id_header: "x-request-id"\n'
            'user_agent: "AeroRAG-X-Test/0.1"\n'
        ),
        encoding="utf-8",
    )

    config = load_http_transport_config(path)

    assert str(config.endpoint_url) == "https://provider.example/v1/generate"
    assert config.api_key_env_var == "TEST_API_KEY"


def test_success_serializes_request_and_parses_result() -> None:
    captured: dict[str, object] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization")
        captured["user_agent"] = request.headers.get("User-Agent")
        captured["body"] = json.loads(request.content)

        return httpx.Response(
            200,
            headers={"x-request-id": "header-123"},
            json={
                "payload": {
                    "answer": "Grounded answer.",
                    "claims": [],
                    "insufficient_evidence": True,
                },
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=client,
        environment={"TEST_API_KEY": "super-secret"},
    )

    result = transport.complete(
        request=make_request(),
        timeout_seconds=10.0,
    )

    assert captured["authorization"] == "Bearer super-secret"
    assert captured["user_agent"] == "AeroRAG-X-Test/0.1"

    body = captured["body"]

    assert isinstance(body, dict)
    assert body["model"] == "test-model"
    assert body["system_prompt"] == "System instructions."
    assert body["response_schema"] == {"type": "object"}

    assert result.payload["answer"] == "Grounded answer."
    assert result.request_id == "header-123"
    assert result.usage is not None
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 20


def test_json_request_id_overrides_header() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        del request

        return httpx.Response(
            200,
            headers={"x-request-id": "header-id"},
            json={
                "payload": {
                    "answer": "Answer",
                    "claims": [],
                    "insufficient_evidence": True,
                },
                "request_id": "json-id",
            },
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    result = transport.complete(
        request=make_request(),
        timeout_seconds=3.0,
    )

    assert result.request_id == "json-id"


def test_missing_api_key_is_rejected_without_leaking_name() -> None:
    with pytest.raises(
        ValueError,
        match=("Configured provider API-key environment variable is missing"),
    ) as exc_info:
        HttpStructuredModelTransport(
            config=make_config(),
            environment={},
        )

    assert "TEST_API_KEY" not in str(exc_info.value)


@pytest.mark.parametrize(
    "status_code",
    [
        408,
        425,
        429,
        500,
        503,
    ],
)
def test_retryable_http_statuses(
    status_code: int,
) -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        del request

        return httpx.Response(
            status_code,
            text="secret upstream body",
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=5.0,
        )

    assert exc_info.value.retryable is True
    assert "secret upstream body" not in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        403,
        404,
        422,
    ],
)
def test_non_retryable_http_statuses(
    status_code: int,
) -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        del request

        return httpx.Response(
            status_code,
            json={"error": "do not expose"},
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=5.0,
        )

    assert exc_info.value.retryable is False
    assert "do not expose" not in str(exc_info.value)


def test_timeout_is_retryable() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
        match="timed out",
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=1.0,
        )

    assert exc_info.value.retryable is True


def test_network_error_is_retryable() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "network unavailable",
            request=request,
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
        match="before receiving",
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=1.0,
        )

    assert exc_info.value.retryable is True


def test_invalid_json_is_non_retryable() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        del request

        return httpx.Response(
            200,
            text="not-json",
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
        match="invalid JSON",
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=5.0,
        )

    assert exc_info.value.retryable is False


def test_missing_payload_is_non_retryable() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        del request

        return httpx.Response(
            200,
            json={
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                }
            },
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
        match="missing object field 'payload'",
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=5.0,
        )

    assert exc_info.value.retryable is False


def test_invalid_usage_is_non_retryable() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        del request

        return httpx.Response(
            200,
            json={
                "payload": {
                    "answer": "Answer",
                    "claims": [],
                    "insufficient_evidence": True,
                },
                "usage": "invalid",
            },
        )

    transport = HttpStructuredModelTransport(
        config=make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"TEST_API_KEY": "secret"},
    )

    with pytest.raises(
        ProviderTransportError,
        match="'usage' must be an object",
    ) as exc_info:
        transport.complete(
            request=make_request(),
            timeout_seconds=5.0,
        )

    assert exc_info.value.retryable is False


def test_authentication_can_be_disabled() -> None:
    captured: dict[str, object] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization")

        return httpx.Response(
            200,
            json={
                "payload": {
                    "answer": "Answer",
                    "claims": [],
                    "insufficient_evidence": True,
                }
            },
        )

    transport = HttpStructuredModelTransport(
        config=make_config(api_key_env_var=None),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={},
    )

    transport.complete(
        request=make_request(),
        timeout_seconds=5.0,
    )

    assert captured["authorization"] is None


def test_timeout_must_be_positive() -> None:
    transport = HttpStructuredModelTransport(
        config=make_config(api_key_env_var=None),
        environment={},
    )

    try:
        with pytest.raises(
            ValueError,
            match=("timeout_seconds must be positive"),
        ):
            transport.complete(
                request=make_request(),
                timeout_seconds=0.0,
            )
    finally:
        transport.close()
