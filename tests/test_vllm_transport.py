"""Tests for vLLM structured transport and benchmark aggregation."""

from __future__ import annotations

import json

import httpx
import pytest

from aeroragx.generation.structured_provider import StructuredModelRequest
from aeroragx.generation.vllm_benchmark import VLLMRequestMetric, summarize_vllm_metrics
from aeroragx.generation.vllm_transport import VLLMRuntimeConfig, VLLMStructuredModelTransport


def test_vllm_transport_uses_guided_json_schema() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": ('{"answer":"ok","claims":[],"insufficient_evidence":false}')
                        }
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
            headers={"x-request-id": "req-1"},
        )

    transport = VLLMStructuredModelTransport(
        model_name="qwen",
        config=VLLMRuntimeConfig(endpoint_url="http://test/v1/chat/completions"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = transport.complete(
        request=StructuredModelRequest(
            model_name="qwen",
            system_prompt="policy",
            user_prompt="content",
            response_schema={"type": "object"},
        ),
        timeout_seconds=10,
    )
    assert captured["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "aeroragx_grounded_answer", "schema": {"type": "object"}},
    }
    assert result.payload["answer"] == "ok"
    assert result.usage is not None and result.usage.total_tokens == 20


def test_vllm_benchmark_keeps_failures_in_denominator() -> None:
    summary = summarize_vllm_metrics(
        [
            VLLMRequestMetric(latency_seconds=1, ttft_seconds=0.2, output_tokens=5, succeeded=True),
            VLLMRequestMetric(
                latency_seconds=2,
                ttft_seconds=None,
                output_tokens=0,
                succeeded=False,
            ),
        ],
        concurrency=8,
        shared_policy_prefix=True,
        wall_seconds=2,
    )
    assert summary.failure_rate == pytest.approx(0.5)
    assert summary.request_throughput == pytest.approx(0.5)
    assert summary.output_tokens_per_second == pytest.approx(2.5)
    assert summary.mean_tpot_seconds == pytest.approx(0.2)
