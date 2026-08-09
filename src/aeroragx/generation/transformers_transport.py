"""Local Hugging Face Transformers transport for structured generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

import torch
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)

type TransformersDeviceName = Literal[
    "auto",
    "cpu",
    "mps",
    "cuda",
]

type TransformersDtypeName = Literal[
    "auto",
    "float32",
    "float16",
    "bfloat16",
]


class TransformersRuntimeConfig(BaseModel):
    """Runtime configuration for local Transformers generation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"

    device: TransformersDeviceName = "auto"
    dtype: TransformersDtypeName = "auto"

    context_window_tokens: int = Field(
        default=32_768,
        ge=128,
    )

    max_input_tokens: int = Field(
        default=16_000,
        ge=1,
    )

    max_new_tokens: int = Field(
        default=512,
        ge=1,
    )

    do_sample: bool = False

    temperature: float = Field(
        default=0.7,
        gt=0.0,
    )

    top_p: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
    )

    top_k: int = Field(
        default=20,
        ge=0,
    )

    enable_thinking: bool = False

    trust_remote_code: bool = False
    local_files_only: bool = False

    revision: str | None = None

    @model_validator(mode="after")
    def validate_context_budget(
        self,
    ) -> TransformersRuntimeConfig:
        """Ensure prompt and output budgets fit the context window."""

        requested_tokens = self.max_input_tokens + self.max_new_tokens

        if requested_tokens > self.context_window_tokens:
            raise ValueError(
                "max_input_tokens + max_new_tokens must not exceed context_window_tokens."
            )

        return self


def load_transformers_runtime_config(
    path: Path,
) -> TransformersRuntimeConfig:
    """Load and validate local Transformers runtime configuration."""

    raw_data = yaml.safe_load(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(raw_data, dict):
        raise ValueError("Transformers runtime configuration must contain a YAML mapping.")

    return TransformersRuntimeConfig.model_validate(raw_data)


def resolve_transformers_device(
    device_name: TransformersDeviceName,
) -> torch.device:
    """Resolve configured local-inference device."""

    if device_name == "cpu":
        return torch.device("cpu")

    if device_name == "mps":
        if not torch.backends.mps.is_available():
            raise ValueError(
                "Transformers runtime requested MPS, "
                "but torch.backends.mps.is_available() "
                "is false."
            )

        return torch.device("mps")

    if device_name == "cuda":
        if not torch.cuda.is_available():
            raise ValueError(
                "Transformers runtime requested CUDA, but torch.cuda.is_available() is false."
            )

        return torch.device("cuda")

    if torch.cuda.is_available():
        return torch.device("cuda")

    if torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


def resolve_transformers_dtype(
    dtype_name: TransformersDtypeName,
) -> str | torch.dtype:
    """Resolve configured model dtype."""

    if dtype_name == "auto":
        return "auto"

    if dtype_name == "float32":
        return torch.float32

    if dtype_name == "float16":
        return torch.float16

    if dtype_name == "bfloat16":
        return torch.bfloat16

    raise AssertionError("Unexpected Transformers dtype.")


def _load_transformers_components(
    *,
    model_name: str,
    config: TransformersRuntimeConfig,
) -> tuple[Any, Any, torch.device]:
    """Load one tokenizer/model pair for local generation."""

    try:
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
        )

    except ImportError as exc:
        raise ValueError(
            "Local Transformers generation requires "
            "the llm dependencies. Install them with "
            '`pip install -e ".[llm]"`.'
        ) from exc

    device = resolve_transformers_device(config.device)

    tokenizer_kwargs: dict[str, object] = {
        "trust_remote_code": (config.trust_remote_code),
        "local_files_only": (config.local_files_only),
    }

    model_kwargs: dict[str, object] = {
        "trust_remote_code": (config.trust_remote_code),
        "local_files_only": (config.local_files_only),
        "dtype": resolve_transformers_dtype(config.dtype),
    }

    if config.revision is not None:
        tokenizer_kwargs["revision"] = config.revision

        model_kwargs["revision"] = config.revision

    tokenizer: Any = AutoTokenizer.from_pretrained(
        model_name,
        **tokenizer_kwargs,
    )

    model: Any = AutoModelForCausalLM.from_pretrained(
        model_name,
        **model_kwargs,
    )

    model.to(device)
    model.eval()

    return tokenizer, model, device


class TransformersStructuredModelTransport:
    """Execute structured generation with a local Transformers model."""

    def __init__(
        self,
        *,
        model_name: str,
        config: TransformersRuntimeConfig,
        tokenizer: Any | None = None,
        model: Any | None = None,
        device: torch.device | str | None = None,
    ) -> None:
        normalized_model_name = model_name.strip()

        if not normalized_model_name:
            raise ValueError("model_name must not be blank.")

        supplied_tokenizer = tokenizer is not None

        supplied_model = model is not None

        if supplied_tokenizer != supplied_model:
            raise ValueError("tokenizer and model must either both be supplied or both be omitted.")

        self._model_name = normalized_model_name

        self._config = config

        if tokenizer is None or model is None:
            (
                loaded_tokenizer,
                loaded_model,
                loaded_device,
            ) = _load_transformers_components(
                model_name=normalized_model_name,
                config=config,
            )

            self._tokenizer = loaded_tokenizer

            self._model = loaded_model

            self._device = loaded_device

        else:
            self._tokenizer = tokenizer
            self._model = model

            self._device = (
                resolve_transformers_device(config.device)
                if device is None
                else torch.device(device)
            )

    @property
    def model_name(self) -> str:
        """Return the configured model name."""

        return self._model_name

    @property
    def device(self) -> str:
        """Return the resolved inference device."""

        return str(self._device)

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
                "Structured request model does not match the loaded Transformers model.",
                retryable=False,
            )

        messages = [
            {
                "role": "system",
                "content": request.system_prompt,
            },
            {
                "role": "user",
                "content": request.user_prompt,
            },
        ]

        try:
            encoded_value = self._tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
                enable_thinking=(self._config.enable_thinking),
            )

        except Exception as exc:
            raise ProviderTransportError(
                "Transformers tokenizer failed to build the chat-model input.",
                retryable=False,
            ) from exc

        if not isinstance(
            encoded_value,
            dict,
        ):
            try:
                encoded_value = dict(encoded_value)

            except (TypeError, ValueError) as exc:
                raise ProviderTransportError(
                    "Transformers tokenizer returned an unsupported input structure.",
                    retryable=False,
                ) from exc

        encoded = cast(
            dict[str, Any],
            encoded_value,
        )

        input_ids_value = encoded.get("input_ids")

        if not isinstance(
            input_ids_value,
            torch.Tensor,
        ):
            raise ProviderTransportError(
                "Transformers tokenizer did not return tensor input_ids.",
                retryable=False,
            )

        if input_ids_value.ndim != 2:
            raise ProviderTransportError(
                "Transformers input_ids must be a rank-2 tensor.",
                retryable=False,
            )

        input_token_count = int(input_ids_value.shape[-1])

        if input_token_count > self._config.max_input_tokens:
            raise ProviderTransportError(
                "Transformers prompt exceeds max_input_tokens.",
                retryable=False,
            )

        model_inputs: dict[str, Any] = {}

        for key, value in encoded.items():
            if isinstance(value, torch.Tensor):
                model_inputs[key] = value.to(self._device)

            else:
                model_inputs[key] = value

        generation_kwargs: dict[
            str,
            object,
        ] = {
            "max_new_tokens": (self._config.max_new_tokens),
            "do_sample": (self._config.do_sample),
        }

        if self._config.do_sample:
            generation_kwargs.update(
                {
                    "temperature": (self._config.temperature),
                    "top_p": (self._config.top_p),
                    "top_k": (self._config.top_k),
                }
            )

        try:
            with torch.inference_mode():
                generated_value = self._model.generate(
                    **model_inputs,
                    **generation_kwargs,
                )

        except Exception as exc:
            raise ProviderTransportError(
                "Local Transformers generation failed.",
                retryable=False,
            ) from exc

        generated = cast(
            torch.Tensor,
            generated_value,
        )

        if generated.ndim != 2:
            raise ProviderTransportError(
                "Transformers model returned an unexpected generation tensor.",
                retryable=False,
            )

        generated_tokens = generated[
            0,
            input_token_count:,
        ]

        output_token_count = int(generated_tokens.numel())

        if output_token_count < 1:
            raise ProviderTransportError(
                "Transformers model returned no new tokens.",
                retryable=False,
            )

        try:
            decoded_value = self._tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True,
            )

        except Exception as exc:
            raise ProviderTransportError(
                "Transformers tokenizer failed to decode generated tokens.",
                retryable=False,
            ) from exc

        if not isinstance(
            decoded_value,
            str,
        ):
            raise ProviderTransportError(
                "Transformers tokenizer returned non-string decoded output.",
                retryable=False,
            )

        generated_text = decoded_value.strip()

        if not generated_text:
            raise ProviderTransportError(
                "Transformers model returned blank decoded output.",
                retryable=False,
            )

        try:
            parsed_payload = json.loads(generated_text)

        except json.JSONDecodeError as exc:
            raise ProviderTransportError(
                "Transformers model output was not valid JSON.",
                retryable=False,
            ) from exc

        if not isinstance(
            parsed_payload,
            dict,
        ):
            raise ProviderTransportError(
                "Transformers structured output must be a JSON object.",
                retryable=False,
            )

        payload = {str(key): value for key, value in parsed_payload.items()}

        return StructuredModelResult(
            payload=payload,
            request_id=None,
            usage=ProviderUsage(
                input_tokens=(input_token_count),
                output_tokens=(output_token_count),
            ),
        )
