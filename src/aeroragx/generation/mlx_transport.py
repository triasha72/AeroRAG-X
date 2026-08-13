"""Apple Silicon MLX-LM transport for structured generation."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)

type MLXLoadFunction = Callable[..., tuple[Any, Any]]
type MLXStreamGenerateFunction = Callable[..., Iterable[Any]]
type MLXSamplerFactory = Callable[..., Any]

_JSON_FENCE_PATTERN = re.compile(
    r"\A```(?:json)?\s*(?P<payload>.*?)\s*```\Z",
    flags=re.IGNORECASE | re.DOTALL,
)


class MLXRuntimeConfig(BaseModel):
    """Runtime configuration for quantized MLX-LM generation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    context_window_tokens: int = Field(default=32_768, ge=128)
    max_input_tokens: int = Field(default=16_000, ge=1)
    max_new_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0.0, ge=0.0)
    top_p: float = Field(default=0.0, ge=0.0, le=1.0)
    min_p: float = Field(default=0.0, ge=0.0, le=1.0)
    top_k: int = Field(default=0, ge=0)
    enable_thinking: bool = False
    trust_remote_code: bool = False
    revision: str | None = None

    @model_validator(mode="after")
    def validate_context_budget(self) -> MLXRuntimeConfig:
        """Ensure prompt and output budgets fit the context window."""

        requested_tokens = self.max_input_tokens + self.max_new_tokens

        if requested_tokens > self.context_window_tokens:
            raise ValueError(
                "max_input_tokens + max_new_tokens must not exceed context_window_tokens."
            )

        return self


def load_mlx_runtime_config(path: Path) -> MLXRuntimeConfig:
    """Load and validate an MLX-LM runtime configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("MLX runtime configuration must contain a YAML mapping.")

    return MLXRuntimeConfig.model_validate(raw_data)


def _load_mlx_dependencies() -> tuple[
    MLXLoadFunction,
    MLXStreamGenerateFunction,
    MLXSamplerFactory,
]:
    """Import optional MLX-LM dependencies only when selected."""

    try:
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler

    except ImportError as exc:
        raise ValueError(
            "MLX generation requires the Apple Silicon dependencies. "
            'Install them with `pip install -e ".[mlx]"` on an arm64 Mac.'
        ) from exc

    return (
        cast(MLXLoadFunction, load),
        cast(MLXStreamGenerateFunction, stream_generate),
        cast(MLXSamplerFactory, make_sampler),
    )


def _normalize_prompt_tokens(value: object) -> list[int]:
    """Normalize one tokenized chat prompt to a flat integer list."""

    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(value, tuple):
        value = list(value)

    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]

    if not isinstance(value, list) or not value:
        raise ProviderTransportError(
            "MLX tokenizer did not return a non-empty token sequence.",
            retryable=False,
        )

    if any(not isinstance(token, int) for token in value):
        raise ProviderTransportError(
            "MLX tokenizer returned non-integer prompt tokens.",
            retryable=False,
        )

    return cast(list[int], value)


def _parse_json_object(generated_text: str) -> dict[str, object]:
    """Parse plain or fenced JSON while rejecting surrounding prose."""

    normalized_text = generated_text.strip()
    fence_match = _JSON_FENCE_PATTERN.fullmatch(normalized_text)

    if fence_match is not None:
        normalized_text = fence_match.group("payload").strip()

    try:
        parsed_payload = json.loads(normalized_text)

    except json.JSONDecodeError as exc:
        raise ProviderTransportError(
            "MLX model output was not valid JSON.",
            retryable=False,
        ) from exc

    if not isinstance(parsed_payload, dict):
        raise ProviderTransportError(
            "MLX structured output must be a JSON object.",
            retryable=False,
        )

    return {str(key): value for key, value in parsed_payload.items()}


class MLXStructuredModelTransport:
    """Execute structured generation with a local MLX-LM model."""

    def __init__(
        self,
        *,
        model_name: str,
        config: MLXRuntimeConfig,
        tokenizer: Any | None = None,
        model: Any | None = None,
        loader: MLXLoadFunction | None = None,
        stream_generate: MLXStreamGenerateFunction | None = None,
        sampler_factory: MLXSamplerFactory | None = None,
    ) -> None:
        normalized_model_name = model_name.strip()

        if not normalized_model_name:
            raise ValueError("model_name must not be blank.")

        supplied_tokenizer = tokenizer is not None
        supplied_model = model is not None

        if supplied_tokenizer != supplied_model:
            raise ValueError("tokenizer and model must either both be supplied or both be omitted.")

        if loader is None or stream_generate is None or sampler_factory is None:
            default_loader, default_stream_generate, default_sampler_factory = (
                _load_mlx_dependencies()
            )
            loader = loader or default_loader
            stream_generate = stream_generate or default_stream_generate
            sampler_factory = sampler_factory or default_sampler_factory

        self._model_name = normalized_model_name
        self._config = config
        self._stream_generate = stream_generate
        self._sampler_factory = sampler_factory

        if tokenizer is None or model is None:
            tokenizer_config: dict[str, object] = {
                "trust_remote_code": config.trust_remote_code,
            }

            try:
                loaded_model, loaded_tokenizer = loader(
                    normalized_model_name,
                    tokenizer_config=tokenizer_config,
                    revision=config.revision,
                )

            except Exception as exc:
                raise ValueError(f"MLX-LM failed to load model {normalized_model_name!r}.") from exc

            self._model = loaded_model
            self._tokenizer = loaded_tokenizer

        else:
            self._model = model
            self._tokenizer = tokenizer

    @property
    def model_name(self) -> str:
        """Return the configured model name or local model path."""

        return self._model_name

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Execute one local structured-model request."""

        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive.")

        if request.model_name != self._model_name:
            raise ProviderTransportError(
                "Structured request model does not match the loaded MLX model.",
                retryable=False,
            )

        try:
            response_schema_text = json.dumps(
                request.response_schema,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise ProviderTransportError(
                "Structured response schema must be JSON serializable.",
                retryable=False,
            ) from exc

        structured_system_prompt = (
            f"{request.system_prompt}\n\n"
            "Output contract: return only one JSON object that validates "
            "against the following JSON Schema:\n"
            f"{response_schema_text}\n\n"
            "The response must begin with '{' and end with '}'. Use "
            "double-quoted JSON keys and values. Do not output an "
            "`answer:` label, Markdown, or any text outside the JSON object."
        )

        messages = [
            {"role": "system", "content": structured_system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]

        try:
            prompt_value = self._tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=self._config.enable_thinking,
            )

        except Exception as exc:
            raise ProviderTransportError(
                "MLX tokenizer failed to build the chat-model input.",
                retryable=False,
            ) from exc

        prompt_tokens = _normalize_prompt_tokens(prompt_value)

        if len(prompt_tokens) > self._config.max_input_tokens:
            raise ProviderTransportError(
                "MLX prompt exceeds max_input_tokens.",
                retryable=False,
            )

        sampler = self._sampler_factory(
            temp=self._config.temperature,
            top_p=self._config.top_p,
            min_p=self._config.min_p,
            top_k=self._config.top_k,
        )

        generated_segments: list[str] = []
        final_response: Any | None = None

        try:
            responses = self._stream_generate(
                self._model,
                self._tokenizer,
                prompt_tokens,
                max_tokens=self._config.max_new_tokens,
                sampler=sampler,
            )

            for response in responses:
                segment = getattr(response, "text", None)

                if not isinstance(segment, str):
                    raise ProviderTransportError(
                        "MLX-LM returned a non-string generated segment.",
                        retryable=False,
                    )

                generated_segments.append(segment)
                final_response = response

        except ProviderTransportError:
            raise
        except Exception as exc:
            raise ProviderTransportError(
                "Local MLX generation failed.",
                retryable=False,
            ) from exc

        if final_response is None:
            raise ProviderTransportError(
                "MLX model returned no generation response.",
                retryable=False,
            )

        generated_text = "".join(generated_segments).strip()

        if not generated_text:
            raise ProviderTransportError(
                "MLX model returned blank decoded output.",
                retryable=False,
            )

        output_token_count = getattr(final_response, "generation_tokens", None)
        reported_input_tokens = getattr(final_response, "prompt_tokens", None)

        if not isinstance(output_token_count, int) or output_token_count < 1:
            raise ProviderTransportError(
                "MLX-LM returned invalid output-token usage.",
                retryable=False,
            )

        input_token_count = (
            reported_input_tokens
            if isinstance(reported_input_tokens, int) and reported_input_tokens >= 0
            else len(prompt_tokens)
        )
        print(
            f"DEBUG: generated_text length={len(generated_text)}; value={generated_text[:1500]!r}"
        )
        return StructuredModelResult(
            payload=_parse_json_object(generated_text),
            request_id=None,
            usage=ProviderUsage(
                input_tokens=input_token_count,
                output_tokens=output_token_count,
            ),
        )
