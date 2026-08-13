"""Tests for the Apple Silicon MLX structured-model transport."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from aeroragx.generation.mlx_transport import (
    MLXRuntimeConfig,
    MLXStructuredModelTransport,
    load_mlx_runtime_config,
)
from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    StructuredModelRequest,
)


class FakeTokenizer:
    """Minimal MLX tokenizer double."""

    def __init__(self, prompt_tokens: list[int] | None = None) -> None:
        self.prompt_tokens = prompt_tokens or [1, 2, 3]
        self.messages: list[dict[str, str]] | None = None
        self.enable_thinking: bool | None = None

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
        enable_thinking: bool,
    ) -> list[int]:
        del tokenize
        del add_generation_prompt

        self.messages = messages
        self.enable_thinking = enable_thinking

        return self.prompt_tokens


@dataclass(frozen=True)
class FakeGenerationResponse:
    """Minimal MLX-LM streaming response double."""

    text: str
    prompt_tokens: int
    generation_tokens: int


class FakeStreamGenerate:
    """Callable streaming-generation double."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        model: object,
        tokenizer: object,
        prompt: list[int],
        **kwargs: Any,
    ) -> list[FakeGenerationResponse]:
        self.calls.append(
            {
                "model": model,
                "tokenizer": tokenizer,
                "prompt": prompt,
                **kwargs,
            }
        )

        return [
            FakeGenerationResponse(
                text=self.text,
                prompt_tokens=len(prompt),
                generation_tokens=7,
            )
        ]


class FakeSamplerFactory:
    """Callable sampler-factory double."""

    def __init__(self) -> None:
        self.received_kwargs: dict[str, object] | None = None
        self.sampler = object()

    def __call__(self, **kwargs: object) -> object:
        self.received_kwargs = kwargs
        return self.sampler


def make_request() -> StructuredModelRequest:
    """Build one valid provider-neutral request."""

    return StructuredModelRequest(
        model_name="test-model",
        system_prompt="Use only supplied evidence.",
        user_prompt="Question and evidence.",
        response_schema={"type": "object"},
    )


def make_config(**overrides: object) -> MLXRuntimeConfig:
    """Build one valid MLX runtime configuration."""

    values: dict[str, object] = {
        "version": "0.1",
        "context_window_tokens": 1024,
        "max_input_tokens": 512,
        "max_new_tokens": 64,
        "temperature": 0.0,
        "top_p": 0.0,
        "min_p": 0.0,
        "top_k": 0,
        "enable_thinking": False,
        "trust_remote_code": False,
        "revision": None,
    }
    values.update(overrides)
    return MLXRuntimeConfig.model_validate(values)


def make_transport(
    generated_text: str,
    *,
    tokenizer: FakeTokenizer | None = None,
    config: MLXRuntimeConfig | None = None,
) -> tuple[
    MLXStructuredModelTransport,
    FakeTokenizer,
    FakeStreamGenerate,
    FakeSamplerFactory,
]:
    """Build one MLX transport without importing optional dependencies."""

    resolved_tokenizer = tokenizer or FakeTokenizer()
    stream_generate = FakeStreamGenerate(generated_text)
    sampler_factory = FakeSamplerFactory()
    transport = MLXStructuredModelTransport(
        model_name="test-model",
        config=config or make_config(),
        tokenizer=resolved_tokenizer,
        model=object(),
        loader=lambda *_args, **_kwargs: (object(), resolved_tokenizer),
        stream_generate=stream_generate,
        sampler_factory=sampler_factory,
    )
    return transport, resolved_tokenizer, stream_generate, sampler_factory


def test_load_mlx_runtime_config(tmp_path: Path) -> None:
    path = tmp_path / "mlx.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            "context_window_tokens: 1024\n"
            "max_input_tokens: 512\n"
            "max_new_tokens: 64\n"
            "temperature: 0.0\n"
            "top_p: 0.0\n"
            "min_p: 0.0\n"
            "top_k: 0\n"
            "enable_thinking: false\n"
            "trust_remote_code: false\n"
            "revision: null\n"
        ),
        encoding="utf-8",
    )

    config = load_mlx_runtime_config(path)

    assert config.max_new_tokens == 64
    assert config.temperature == 0.0
    assert config.enable_thinking is False


def test_context_budget_is_validated() -> None:
    with pytest.raises(ValidationError, match="context_window_tokens"):
        make_config(
            context_window_tokens=100,
            max_input_tokens=80,
            max_new_tokens=40,
        )


def test_complete_returns_plain_json_payload_and_usage() -> None:
    transport, _tokenizer, stream_generate, sampler_factory = make_transport(
        '{"answer":"Supported.","claims":[],"insufficient_evidence":false}'
    )

    result = transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert result.payload["answer"] == "Supported."
    assert result.payload["insufficient_evidence"] is False
    assert result.usage is not None
    assert result.usage.input_tokens == 3
    assert result.usage.output_tokens == 7
    assert stream_generate.calls[0]["max_tokens"] == 64
    assert stream_generate.calls[0]["sampler"] is sampler_factory.sampler


def test_complete_does_not_write_generated_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport(
        '{"answer":"Supported."}'
    )

    transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert capsys.readouterr().out == ""


def test_complete_accepts_fenced_json() -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport(
        '```json\n{"answer":"Supported."}\n```'
    )

    result = transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert result.payload == {"answer": "Supported."}


def test_complete_uses_chat_messages_and_disables_thinking() -> None:
    transport, tokenizer, _stream_generate, _sampler_factory = make_transport("{}")

    transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert tokenizer.messages == [
        {
            "role": "system",
            "content": (
                "Use only supplied evidence.\n\n"
                "Output contract: return only one JSON object that validates "
                "against the following JSON Schema:\n"
                '{"type":"object"}\n\n'
                "The response must begin with '{' and end with '}'. Use "
                "double-quoted JSON keys and values. Do not output an "
                "`answer:` label, Markdown, or any text outside the JSON object."
            ),
        },
        {"role": "user", "content": "Question and evidence."},
    ]
    assert tokenizer.enable_thinking is False


def test_complete_uses_deterministic_sampler_configuration() -> None:
    transport, _tokenizer, _stream_generate, sampler_factory = make_transport("{}")

    transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert sampler_factory.received_kwargs == {
        "temp": 0.0,
        "top_p": 0.0,
        "min_p": 0.0,
        "top_k": 0,
    }


def test_invalid_json_is_rejected() -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport("not JSON")

    with pytest.raises(ProviderTransportError, match="not valid JSON"):
        transport.complete(
            request=make_request(),
            timeout_seconds=30.0,
        )


def test_non_object_json_is_rejected() -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport('["not", "object"]')

    with pytest.raises(ProviderTransportError, match="must be a JSON object"):
        transport.complete(
            request=make_request(),
            timeout_seconds=30.0,
        )


def test_prompt_limit_is_enforced() -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport(
        "{}",
        tokenizer=FakeTokenizer(prompt_tokens=[1, 2, 3, 4]),
        config=make_config(max_input_tokens=3),
    )

    with pytest.raises(ProviderTransportError, match="max_input_tokens"):
        transport.complete(
            request=make_request(),
            timeout_seconds=30.0,
        )


def test_request_model_must_match_loaded_model() -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport("{}")
    request = make_request().model_copy(update={"model_name": "another-model"})

    with pytest.raises(ProviderTransportError, match="does not match"):
        transport.complete(
            request=request,
            timeout_seconds=30.0,
        )


def test_timeout_must_be_positive() -> None:
    transport, _tokenizer, _stream_generate, _sampler_factory = make_transport("{}")

    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        transport.complete(
            request=make_request(),
            timeout_seconds=0.0,
        )


def test_loader_runs_once_during_construction() -> None:
    loader_calls: list[str] = []
    tokenizer = FakeTokenizer()

    def loader(model_name: str, **_kwargs: object) -> tuple[object, FakeTokenizer]:
        loader_calls.append(model_name)
        return object(), tokenizer

    stream_generate = FakeStreamGenerate("{}")
    transport = MLXStructuredModelTransport(
        model_name="test-model",
        config=make_config(),
        loader=loader,
        stream_generate=stream_generate,
        sampler_factory=FakeSamplerFactory(),
    )

    transport.complete(request=make_request(), timeout_seconds=30.0)
    transport.complete(request=make_request(), timeout_seconds=30.0)

    assert loader_calls == ["test-model"]


def test_tokenizer_and_model_are_supplied_together() -> None:
    with pytest.raises(ValueError, match="both be supplied or both be omitted"):
        MLXStructuredModelTransport(
            model_name="test-model",
            config=make_config(),
            tokenizer=FakeTokenizer(),
            model=None,
            loader=lambda *_args, **_kwargs: (object(), FakeTokenizer()),
            stream_generate=FakeStreamGenerate("{}"),
            sampler_factory=FakeSamplerFactory(),
        )
