"""Tests for SGLang and TensorRT-LLM structured transport."""

from __future__ import annotations

import httpx
import pytest

from aeroragx.generation.openai_compatible_serving import (
    CompatibleServingConfig,
    OpenAICompatibleStructuredTransport,
)
from aeroragx.generation.structured_provider import StructuredModelRequest


@pytest.mark.parametrize("engine", ["sglang", "tensorrt-llm"])
def test_compatible_engine_returns_structured_result(engine: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"answer":"Supported.","claims":[],"insufficient_evidence":false}'
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 6},
            },
        )

    config = CompatibleServingConfig(
        engine=engine,
        endpoint_url="http://engine/v1/chat/completions",
    )
    transport = OpenAICompatibleStructuredTransport(
        model_name="qwen",
        config=config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = transport.complete(
        request=StructuredModelRequest(
            model_name="qwen",
            system_prompt="policy",
            user_prompt="content",
            response_schema={"type": "object"},
        ),
        timeout_seconds=5,
    )
    assert result.payload["answer"] == "Supported."
    assert result.usage is not None and result.usage.total_tokens == 16
