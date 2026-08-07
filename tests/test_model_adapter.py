"""Tests for structured model API adapters."""

from __future__ import annotations

import json

import httpx
import pytest

from aeroragx.generation.http_transport import (
    HttpStructuredModelTransport,
    HttpTransportConfig,
)
from aeroragx.generation.model_adapter import (
    GenericStructuredModelAdapter,
    OpenAIResponsesAdapter,
)
from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    StructuredModelRequest,
)


def make_request() -> StructuredModelRequest:
    """Create one grounded structured-model request."""

    return StructuredModelRequest(
        model_name="gpt-test",
        system_prompt="Use only supplied evidence.",
        user_prompt="<E>NASA evidence</E>",
        response_schema={
            "title": "ProviderResponse",
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Answer",
                    "type": "string",
                },
                "claims": {
                    "default": [],
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "evidence_ids": {
                                "default": [],
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
                "insufficient_evidence": {
                    "default": False,
                    "type": "boolean",
                },
            },
            "required": ["answer"],
        },
    )


def test_generic_adapter_preserves_original_contract() -> None:
    adapter = GenericStructuredModelAdapter()
    request = make_request()

    payload = adapter.build_request_payload(request)

    assert payload == {
        "model": "gpt-test",
        "system_prompt": ("Use only supplied evidence."),
        "user_prompt": ("<E>NASA evidence</E>"),
        "response_schema": (request.response_schema),
    }

    result = adapter.parse_response(
        {
            "payload": {
                "answer": "Answer",
                "claims": [],
                "insufficient_evidence": True,
            },
            "request_id": "generic-123",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
            },
        },
        fallback_request_id=None,
    )

    assert result.request_id == "generic-123"
    assert result.usage is not None
    assert result.usage.total_tokens == 120


def test_openai_adapter_builds_responses_api_payload() -> None:
    adapter = OpenAIResponsesAdapter(schema_name="aeroragx_answer")

    payload = adapter.build_request_payload(make_request())

    assert payload["model"] == "gpt-test"

    input_items = payload["input"]

    assert isinstance(input_items, list)
    assert input_items[0] == {
        "role": "system",
        "content": ("Use only supplied evidence."),
    }
    assert input_items[1] == {
        "role": "user",
        "content": ("<E>NASA evidence</E>"),
    }

    text = payload["text"]

    assert isinstance(text, dict)
    response_format = text["format"]

    assert isinstance(
        response_format,
        dict,
    )
    assert response_format["type"] == "json_schema"
    assert response_format["name"] == "aeroragx_answer"
    assert response_format["strict"] is True

    schema = response_format["schema"]

    assert isinstance(schema, dict)
    assert "title" not in schema
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "answer",
        "claims",
        "insufficient_evidence",
    }

    properties = schema["properties"]

    assert isinstance(properties, dict)
    claims = properties["claims"]

    assert isinstance(claims, dict)
    assert "default" not in claims


def test_openai_adapter_parses_output_text() -> None:
    adapter = OpenAIResponsesAdapter()

    result = adapter.parse_response(
        {
            "id": "resp-123",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "answer": ("Battery cooling removes heat."),
                                    "claims": [
                                        {
                                            "text": ("Cooling removes heat."),
                                            "evidence_ids": ["E1"],
                                        }
                                    ],
                                    "insufficient_evidence": False,
                                }
                            ),
                        }
                    ],
                }
            ],
            "usage": {
                "input_tokens": 250,
                "output_tokens": 60,
                "total_tokens": 310,
            },
        },
        fallback_request_id=("header-request"),
    )

    assert result.request_id == "resp-123"
    assert result.payload["answer"] == "Battery cooling removes heat."
    assert result.usage is not None
    assert result.usage.input_tokens == 250
    assert result.usage.output_tokens == 60


def test_openai_adapter_uses_header_request_id_fallback() -> None:
    adapter = OpenAIResponsesAdapter()

    result = adapter.parse_response(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": ('{"answer":"A","claims":[],"insufficient_evidence":true}'),
                        }
                    ],
                }
            ],
        },
        fallback_request_id="header-7",
    )

    assert result.request_id == "header-7"


def test_openai_refusal_is_non_retryable() -> None:
    adapter = OpenAIResponsesAdapter()

    with pytest.raises(
        ProviderTransportError,
        match="refused",
    ) as exc_info:
        adapter.parse_response(
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "refusal",
                                "refusal": ("Cannot answer."),
                            }
                        ],
                    }
                ],
            },
            fallback_request_id=None,
        )

    assert exc_info.value.retryable is False


def test_openai_incomplete_response_is_non_retryable() -> None:
    adapter = OpenAIResponsesAdapter()

    with pytest.raises(
        ProviderTransportError,
        match="incomplete",
    ) as exc_info:
        adapter.parse_response(
            {
                "status": "incomplete",
                "output": [],
            },
            fallback_request_id=None,
        )

    assert exc_info.value.retryable is False


def test_openai_invalid_output_json_is_rejected() -> None:
    adapter = OpenAIResponsesAdapter()

    with pytest.raises(
        ProviderTransportError,
        match="not valid JSON",
    ):
        adapter.parse_response(
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "{broken",
                            }
                        ],
                    }
                ],
            },
            fallback_request_id=None,
        )


def test_http_transport_uses_openai_adapter() -> None:
    captured: dict[str, object] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["body"] = json.loads(request.content)

        return httpx.Response(
            200,
            headers={"x-request-id": "http-header-id"},
            json={
                "id": "resp-live-shape",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "answer": ("Grounded."),
                                        "claims": [],
                                        "insufficient_evidence": True,
                                    }
                                ),
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    transport = HttpStructuredModelTransport(
        config=HttpTransportConfig(
            version="0.1",
            endpoint_url=("https://api.openai.com/v1/responses"),
            api_key_env_var=("OPENAI_API_KEY"),
            authorization_scheme=("Bearer"),
            request_id_header=("x-request-id"),
            user_agent=("AeroRAG-X-Test"),
        ),
        adapter=(OpenAIResponsesAdapter()),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environment={"OPENAI_API_KEY": "test-secret"},
    )

    result = transport.complete(
        request=make_request(),
        timeout_seconds=20.0,
    )

    body = captured["body"]

    assert isinstance(body, dict)
    assert "input" in body
    assert "text" in body
    assert "system_prompt" not in body
    assert result.request_id == "resp-live-shape"


def test_blank_openai_schema_name_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="schema_name must not be blank",
    ):
        OpenAIResponsesAdapter(schema_name="   ")
