"""Tests for local Transformers structured-model transport."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import torch
from pydantic import ValidationError

from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    StructuredModelRequest,
)
from aeroragx.generation.transformers_transport import (
    TransformersRuntimeConfig,
    TransformersStructuredModelTransport,
    load_transformers_runtime_config,
    resolve_transformers_device,
)


class FakeTokenizer:
    """Minimal tokenizer double for deterministic tests."""

    def __init__(
        self,
        *,
        decoded_text: str,
    ) -> None:
        self.decoded_text = decoded_text

        self.messages: list[dict[str, str]] | None = None

        self.enable_thinking: bool | None = None

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
        return_dict: bool,
        return_tensors: str,
        enable_thinking: bool,
    ) -> dict[str, torch.Tensor]:
        del tokenize
        del add_generation_prompt
        del return_dict
        del return_tensors

        self.messages = messages
        self.enable_thinking = enable_thinking

        return {
            "input_ids": torch.tensor(
                [[1, 2, 3]],
                dtype=torch.long,
            ),
            "attention_mask": torch.tensor(
                [[1, 1, 1]],
                dtype=torch.long,
            ),
        }

    def decode(
        self,
        token_ids: torch.Tensor,
        *,
        skip_special_tokens: bool,
    ) -> str:
        del token_ids
        del skip_special_tokens

        return self.decoded_text


class FakeModel:
    """Minimal causal-model double."""

    def __init__(self) -> None:
        self.received_kwargs: dict[
            str,
            Any,
        ] = {}

    def generate(
        self,
        **kwargs: Any,
    ) -> torch.Tensor:
        self.received_kwargs = kwargs

        return torch.tensor(
            [[1, 2, 3, 10, 11]],
            dtype=torch.long,
        )


def make_request() -> StructuredModelRequest:
    """Build one valid provider-neutral model request."""

    return StructuredModelRequest(
        model_name="test-model",
        system_prompt=("Use only supplied evidence."),
        user_prompt=("Question and evidence."),
        response_schema={
            "type": "object",
        },
    )


def make_config(
    **overrides: object,
) -> TransformersRuntimeConfig:
    """Build one valid local runtime config."""

    values: dict[str, object] = {
        "version": "0.1",
        "device": "cpu",
        "dtype": "float32",
        "context_window_tokens": 1024,
        "max_input_tokens": 512,
        "max_new_tokens": 64,
        "do_sample": False,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "enable_thinking": False,
        "trust_remote_code": False,
        "local_files_only": True,
        "revision": None,
    }

    values.update(overrides)

    return TransformersRuntimeConfig.model_validate(values)


def test_load_transformers_runtime_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "transformers.yaml"

    path.write_text(
        (
            'version: "0.1"\n'
            'device: "cpu"\n'
            'dtype: "float32"\n'
            "context_window_tokens: 1024\n"
            "max_input_tokens: 512\n"
            "max_new_tokens: 64\n"
            "do_sample: false\n"
            "temperature: 0.7\n"
            "top_p: 0.8\n"
            "top_k: 20\n"
            "enable_thinking: false\n"
            "trust_remote_code: false\n"
            "local_files_only: true\n"
            "revision: null\n"
        ),
        encoding="utf-8",
    )

    config = load_transformers_runtime_config(path)

    assert config.device == "cpu"

    assert config.max_new_tokens == 64

    assert config.enable_thinking is False


def test_context_budget_is_validated() -> None:
    with pytest.raises(
        ValidationError,
        match="context_window_tokens",
    ):
        make_config(
            context_window_tokens=100,
            max_input_tokens=80,
            max_new_tokens=40,
        )


def test_explicit_cpu_device_resolves() -> None:
    device = resolve_transformers_device("cpu")

    assert device.type == "cpu"


def test_complete_returns_structured_payload() -> None:
    tokenizer = FakeTokenizer(
        decoded_text=('{"answer":"Supported.","claims":[],"insufficient_evidence":false}'),
    )

    model = FakeModel()

    transport = TransformersStructuredModelTransport(
        model_name="test-model",
        config=make_config(),
        tokenizer=tokenizer,
        model=model,
        device="cpu",
    )

    result = transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert result.payload["answer"] == "Supported."

    assert result.payload["insufficient_evidence"] is False

    assert result.usage is not None

    assert result.usage.input_tokens == 3

    assert result.usage.output_tokens == 2


def test_complete_uses_chat_messages() -> None:
    tokenizer = FakeTokenizer(
        decoded_text=('{"answer":"Supported.","claims":[],"insufficient_evidence":false}'),
    )

    transport = TransformersStructuredModelTransport(
        model_name="test-model",
        config=make_config(),
        tokenizer=tokenizer,
        model=FakeModel(),
        device="cpu",
    )

    transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert tokenizer.messages == [
        {
            "role": "system",
            "content": ("Use only supplied evidence."),
        },
        {
            "role": "user",
            "content": ("Question and evidence."),
        },
    ]

    assert tokenizer.enable_thinking is False


def test_complete_uses_deterministic_generation() -> None:
    tokenizer = FakeTokenizer(
        decoded_text=('{"answer":"Supported.","claims":[],"insufficient_evidence":false}'),
    )

    model = FakeModel()

    transport = TransformersStructuredModelTransport(
        model_name="test-model",
        config=make_config(
            do_sample=False,
        ),
        tokenizer=tokenizer,
        model=model,
        device="cpu",
    )

    transport.complete(
        request=make_request(),
        timeout_seconds=30.0,
    )

    assert model.received_kwargs["max_new_tokens"] == 64

    assert model.received_kwargs["do_sample"] is False

    assert "temperature" not in model.received_kwargs

    assert "top_p" not in model.received_kwargs


def test_invalid_json_is_rejected() -> None:
    transport = TransformersStructuredModelTransport(
        model_name="test-model",
        config=make_config(),
        tokenizer=FakeTokenizer(
            decoded_text=("this is not json"),
        ),
        model=FakeModel(),
        device="cpu",
    )

    with pytest.raises(
        ProviderTransportError,
        match="not valid JSON",
    ):
        transport.complete(
            request=make_request(),
            timeout_seconds=30.0,
        )


def test_non_object_json_is_rejected() -> None:
    transport = TransformersStructuredModelTransport(
        model_name="test-model",
        config=make_config(),
        tokenizer=FakeTokenizer(
            decoded_text='["not", "object"]',
        ),
        model=FakeModel(),
        device="cpu",
    )

    with pytest.raises(
        ProviderTransportError,
        match="must be a JSON object",
    ):
        transport.complete(
            request=make_request(),
            timeout_seconds=30.0,
        )


def test_request_model_must_match_loaded_model() -> None:
    transport = TransformersStructuredModelTransport(
        model_name="different-model",
        config=make_config(),
        tokenizer=FakeTokenizer(
            decoded_text="{}",
        ),
        model=FakeModel(),
        device="cpu",
    )

    with pytest.raises(
        ProviderTransportError,
        match="does not match",
    ):
        transport.complete(
            request=make_request(),
            timeout_seconds=30.0,
        )


def test_tokenizer_and_model_are_supplied_together() -> None:
    with pytest.raises(
        ValueError,
        match=("both be supplied or both be omitted"),
    ):
        TransformersStructuredModelTransport(
            model_name="test-model",
            config=make_config(),
            tokenizer=FakeTokenizer(
                decoded_text="{}",
            ),
            model=None,
            device="cpu",
        )
