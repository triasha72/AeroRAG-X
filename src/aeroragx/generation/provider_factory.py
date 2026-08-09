"""Build configured local and remote generation providers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aeroragx.generation.grounded import GenerationConfig
from aeroragx.generation.http_transport import (
    HttpStructuredModelTransport,
    load_http_transport_config,
)
from aeroragx.generation.model_adapter import OpenAIResponsesAdapter
from aeroragx.generation.prompting import load_provider_hardening_config
from aeroragx.generation.provider import (
    GenerationProvider,
    create_generation_provider,
)
from aeroragx.generation.structured_provider import (
    StructuredGenerationProvider,
)
from aeroragx.generation.transformers_transport import (
    TransformersStructuredModelTransport,
    load_transformers_runtime_config,
)

RemoteAdapterName = Literal["openai-responses"]


class ProviderRuntimeConfig(BaseModel):
    """Provider-specific runtime metadata and cost configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    adapter: RemoteAdapterName
    schema_name: str = Field(min_length=1)

    priced_model_name: str = Field(min_length=1)
    input_cost_per_million_tokens: float = Field(ge=0.0)
    output_cost_per_million_tokens: float = Field(ge=0.0)
    pricing_snapshot_date: str = Field(min_length=1)
    pricing_basis: str = Field(min_length=1)


def load_provider_runtime_config(
    path: Path,
) -> ProviderRuntimeConfig:
    """Load and validate provider-specific runtime configuration."""

    raw_data = yaml.safe_load(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(raw_data, dict):
        raise ValueError("Provider runtime configuration must contain a YAML mapping.")

    return ProviderRuntimeConfig.model_validate(raw_data)


def create_configured_generation_provider(
    *,
    generation_config: GenerationConfig,
    provider_config: Path | None = None,
    http_transport_config: Path | None = None,
    provider_runtime_config: Path | None = None,
    environment: dict[str, str] | None = None,
) -> GenerationProvider:
    """Create a configured generation provider."""

    normalized_provider = generation_config.provider.strip().lower()

    if normalized_provider in {
        "fake",
        "deterministic",
        "extractive",
    }:
        return create_generation_provider(normalized_provider)

    if normalized_provider in {
        "openai",
        "openai-responses",
        "responses",
    }:
        return _create_openai_responses_provider(
            generation_config=generation_config,
            provider_config=_require_path(
                provider_config,
                option_name="provider_config",
            ),
            http_transport_config=_require_path(
                http_transport_config,
                option_name="http_transport_config",
            ),
            provider_runtime_config=_require_path(
                provider_runtime_config,
                option_name="provider_runtime_config",
            ),
            environment=environment,
        )

    if normalized_provider in {
        "transformers",
        "huggingface",
    }:
        return _create_transformers_provider(
            generation_config=generation_config,
            provider_config=_require_path(
                provider_config,
                option_name="provider_config",
            ),
            provider_runtime_config=_require_path(
                provider_runtime_config,
                option_name="provider_runtime_config",
            ),
        )

    raise ValueError(
        "Unsupported configured generation provider "
        f"{generation_config.provider!r}. "
        "Supported providers are: fake, deterministic, "
        "extractive, openai-responses, transformers."
    )


def _create_openai_responses_provider(
    *,
    generation_config: GenerationConfig,
    provider_config: Path,
    http_transport_config: Path,
    provider_runtime_config: Path,
    environment: dict[str, str] | None,
) -> GenerationProvider:
    """Create one hardened OpenAI Responses API generation provider."""

    hardening_config = load_provider_hardening_config(provider_config)

    http_config = load_http_transport_config(http_transport_config)

    runtime_config = load_provider_runtime_config(provider_runtime_config)

    if runtime_config.adapter != "openai-responses":
        raise ValueError("OpenAI generation requires adapter='openai-responses'.")

    if generation_config.model_name != runtime_config.priced_model_name:
        raise ValueError(
            "Generation model does not match "
            "the pricing snapshot model. "
            f"generation="
            f"{generation_config.model_name!r}, "
            f"pricing="
            f"{runtime_config.priced_model_name!r}."
        )

    adapter = OpenAIResponsesAdapter(schema_name=(runtime_config.schema_name))

    transport = HttpStructuredModelTransport(
        config=http_config,
        adapter=adapter,
        environment=environment,
    )

    return StructuredGenerationProvider(
        model_name=(generation_config.model_name),
        transport=transport,
        config=hardening_config,
        input_cost_per_million_tokens=(runtime_config.input_cost_per_million_tokens),
        output_cost_per_million_tokens=(runtime_config.output_cost_per_million_tokens),
    )


def _create_transformers_provider(
    *,
    generation_config: GenerationConfig,
    provider_config: Path,
    provider_runtime_config: Path,
) -> GenerationProvider:
    """Create one local Hugging Face Transformers provider."""

    hardening_config = load_provider_hardening_config(provider_config)

    runtime_config = load_transformers_runtime_config(provider_runtime_config)

    transport = TransformersStructuredModelTransport(
        model_name=(generation_config.model_name),
        config=runtime_config,
    )

    return StructuredGenerationProvider(
        model_name=(generation_config.model_name),
        transport=transport,
        config=hardening_config,
        input_cost_per_million_tokens=0.0,
        output_cost_per_million_tokens=0.0,
    )


def _require_path(
    value: Path | None,
    *,
    option_name: str,
) -> Path:
    """Return one required provider configuration path."""

    if value is None:
        raise ValueError(f"Configured generation provider requires {option_name}.")

    return value
