"""Tests for configured generation-provider construction."""

from __future__ import annotations

from pathlib import Path

import pytest

import aeroragx.generation.provider_factory as provider_factory_module
from aeroragx.generation.grounded import GenerationConfig
from aeroragx.generation.provider import DeterministicGenerationProvider
from aeroragx.generation.provider_factory import (
    ProviderRuntimeConfig,
    create_configured_generation_provider,
    load_provider_runtime_config,
)
from aeroragx.generation.structured_provider import (
    StructuredGenerationProvider,
    StructuredModelRequest,
    StructuredModelResult,
)


class FakeTransformersTransport:
    """Offline Transformers transport double."""

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Return one deterministic structured result."""

        del request
        del timeout_seconds

        return StructuredModelResult(
            payload={
                "answer": "Supported.",
                "claims": [],
                "insufficient_evidence": False,
            },
            request_id=None,
            usage=None,
        )


def generation_config(
    *,
    provider: str,
    model_name: str,
) -> GenerationConfig:
    """Build a valid generation configuration."""

    return GenerationConfig(
        version="0.1",
        provider=provider,
        model_name=model_name,
        evidence_top_k=5,
        minimum_evidence_count=1,
        max_context_characters=12_000,
        max_chunk_characters=3_000,
        max_claims=6,
        require_citations=True,
        allow_insufficient_evidence=True,
        include_retrieval_metadata=True,
    )


def write_provider_config(
    path: Path,
) -> None:
    """Write one valid hardening configuration."""

    path.write_text(
        (
            'version: "0.1"\n'
            'prompt_version: "grounded-json-v0.1"\n'
            "max_query_characters: 2000\n"
            "max_evidence_characters: 12000\n"
            'evidence_start_marker: "<E>"\n'
            'evidence_end_marker: "</E>"\n'
            'prompt_injection_policy: "block"\n'
            "timeout_seconds: 30.0\n"
            "max_retries: 2\n"
            "retry_backoff_seconds: 0.0\n"
            "redact_secrets: true\n"
        ),
        encoding="utf-8",
    )


def write_http_config(
    path: Path,
) -> None:
    """Write one valid OpenAI HTTP configuration."""

    path.write_text(
        (
            'version: "0.1"\n'
            'endpoint_url: "https://api.openai.com/v1/responses"\n'
            'api_key_env_var: "OPENAI_API_KEY"\n'
            'authorization_scheme: "Bearer"\n'
            'request_id_header: "x-request-id"\n'
            'user_agent: "AeroRAG-X-Test/0.1"\n'
        ),
        encoding="utf-8",
    )


def write_runtime_config(
    path: Path,
    *,
    model_name: str = "gpt-5.6-luna",
) -> None:
    """Write one valid provider-runtime configuration."""

    path.write_text(
        (
            'version: "0.1"\n'
            'adapter: "openai-responses"\n'
            'schema_name: "aeroragx_grounded_answer"\n'
            f'priced_model_name: "{model_name}"\n'
            "input_cost_per_million_tokens: 1.00\n"
            "output_cost_per_million_tokens: 6.00\n"
            'pricing_snapshot_date: "2026-08-07"\n'
            'pricing_basis: "standard_short_context"\n'
        ),
        encoding="utf-8",
    )


def write_transformers_runtime_config(
    path: Path,
) -> None:
    """Write one valid local Transformers runtime configuration."""

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


def test_load_provider_runtime_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.yaml"

    write_runtime_config(path)

    config = load_provider_runtime_config(path)

    assert isinstance(
        config,
        ProviderRuntimeConfig,
    )

    assert config.adapter == "openai-responses"

    assert config.priced_model_name == "gpt-5.6-luna"

    assert config.input_cost_per_million_tokens == pytest.approx(1.00)

    assert config.output_cost_per_million_tokens == pytest.approx(6.00)


@pytest.mark.parametrize(
    "provider_name",
    [
        "fake",
        "deterministic",
        "extractive",
    ],
)
def test_local_provider_requires_no_remote_configs(
    provider_name: str,
) -> None:
    provider = create_configured_generation_provider(
        generation_config=(
            generation_config(
                provider=provider_name,
                model_name=("deterministic-grounded-v0"),
            )
        )
    )

    assert isinstance(
        provider,
        DeterministicGenerationProvider,
    )


@pytest.mark.parametrize(
    "missing_name",
    [
        "provider_config",
        "http_transport_config",
        "provider_runtime_config",
    ],
)
def test_openai_requires_all_remote_configs(
    tmp_path: Path,
    missing_name: str,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    http_path = tmp_path / "http.yaml"

    runtime_path = tmp_path / "runtime.yaml"

    write_provider_config(provider_path)

    write_http_config(http_path)

    write_runtime_config(runtime_path)

    values: dict[
        str,
        Path | None,
    ] = {
        "provider_config": provider_path,
        "http_transport_config": http_path,
        "provider_runtime_config": (runtime_path),
    }

    values[missing_name] = None

    with pytest.raises(
        ValueError,
        match=missing_name,
    ):
        create_configured_generation_provider(
            generation_config=(
                generation_config(
                    provider=("openai-responses"),
                    model_name=("gpt-5.6-luna"),
                )
            ),
            provider_config=(values["provider_config"]),
            http_transport_config=(values["http_transport_config"]),
            provider_runtime_config=(values["provider_runtime_config"]),
            environment={"OPENAI_API_KEY": ("test-secret")},
        )


def test_openai_provider_is_constructed(
    tmp_path: Path,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    http_path = tmp_path / "http.yaml"

    runtime_path = tmp_path / "runtime.yaml"

    write_provider_config(provider_path)

    write_http_config(http_path)

    write_runtime_config(runtime_path)

    provider = create_configured_generation_provider(
        generation_config=(
            generation_config(
                provider=("openai-responses"),
                model_name=("gpt-5.6-luna"),
            )
        ),
        provider_config=provider_path,
        http_transport_config=(http_path),
        provider_runtime_config=(runtime_path),
        environment={"OPENAI_API_KEY": ("test-secret")},
    )

    assert isinstance(
        provider,
        StructuredGenerationProvider,
    )

    assert provider.last_telemetry is None


def test_openai_missing_api_key_is_rejected(
    tmp_path: Path,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    http_path = tmp_path / "http.yaml"

    runtime_path = tmp_path / "runtime.yaml"

    write_provider_config(provider_path)

    write_http_config(http_path)

    write_runtime_config(runtime_path)

    with pytest.raises(
        ValueError,
        match="API-key",
    ):
        create_configured_generation_provider(
            generation_config=(
                generation_config(
                    provider=("openai-responses"),
                    model_name=("gpt-5.6-luna"),
                )
            ),
            provider_config=provider_path,
            http_transport_config=(http_path),
            provider_runtime_config=(runtime_path),
            environment={},
        )


def test_pricing_snapshot_must_match_model(
    tmp_path: Path,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    http_path = tmp_path / "http.yaml"

    runtime_path = tmp_path / "runtime.yaml"

    write_provider_config(provider_path)

    write_http_config(http_path)

    write_runtime_config(
        runtime_path,
        model_name="different-model",
    )

    with pytest.raises(
        ValueError,
        match="pricing snapshot model",
    ):
        create_configured_generation_provider(
            generation_config=(
                generation_config(
                    provider=("openai-responses"),
                    model_name=("gpt-5.6-luna"),
                )
            ),
            provider_config=provider_path,
            http_transport_config=(http_path),
            provider_runtime_config=(runtime_path),
            environment={"OPENAI_API_KEY": ("test-secret")},
        )


def test_transformers_provider_is_constructed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    runtime_path = tmp_path / "transformers.yaml"

    write_provider_config(provider_path)

    write_transformers_runtime_config(runtime_path)

    monkeypatch.setattr(
        provider_factory_module,
        "TransformersStructuredModelTransport",
        lambda **kwargs: FakeTransformersTransport(),
    )

    provider = create_configured_generation_provider(
        generation_config=(
            generation_config(
                provider="transformers",
                model_name="test-model",
            )
        ),
        provider_config=provider_path,
        provider_runtime_config=(runtime_path),
    )

    assert isinstance(
        provider,
        StructuredGenerationProvider,
    )

    assert provider.last_telemetry is None


@pytest.mark.parametrize(
    "missing_name",
    [
        "provider_config",
        "provider_runtime_config",
    ],
)
def test_transformers_requires_configs(
    tmp_path: Path,
    missing_name: str,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    runtime_path = tmp_path / "transformers.yaml"

    write_provider_config(provider_path)

    write_transformers_runtime_config(runtime_path)

    values: dict[
        str,
        Path | None,
    ] = {
        "provider_config": provider_path,
        "provider_runtime_config": (runtime_path),
    }

    values[missing_name] = None

    with pytest.raises(
        ValueError,
        match=missing_name,
    ):
        create_configured_generation_provider(
            generation_config=(
                generation_config(
                    provider="transformers",
                    model_name="test-model",
                )
            ),
            provider_config=(values["provider_config"]),
            provider_runtime_config=(values["provider_runtime_config"]),
        )


@pytest.mark.parametrize(
    "provider_name",
    [
        "transformers",
        "huggingface",
    ],
)
def test_transformers_provider_aliases_are_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    runtime_path = tmp_path / "transformers.yaml"

    write_provider_config(provider_path)

    write_transformers_runtime_config(runtime_path)

    monkeypatch.setattr(
        provider_factory_module,
        "TransformersStructuredModelTransport",
        lambda **kwargs: FakeTransformersTransport(),
    )

    provider = create_configured_generation_provider(
        generation_config=(
            generation_config(
                provider=provider_name,
                model_name="test-model",
            )
        ),
        provider_config=provider_path,
        provider_runtime_config=(runtime_path),
    )

    assert isinstance(
        provider,
        StructuredGenerationProvider,
    )


def test_transformers_does_not_require_http_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_path = tmp_path / "provider.yaml"

    runtime_path = tmp_path / "transformers.yaml"

    write_provider_config(provider_path)

    write_transformers_runtime_config(runtime_path)

    monkeypatch.setattr(
        provider_factory_module,
        "TransformersStructuredModelTransport",
        lambda **kwargs: FakeTransformersTransport(),
    )

    provider = create_configured_generation_provider(
        generation_config=(
            generation_config(
                provider="transformers",
                model_name="test-model",
            )
        ),
        provider_config=provider_path,
        http_transport_config=None,
        provider_runtime_config=(runtime_path),
    )

    assert isinstance(
        provider,
        StructuredGenerationProvider,
    )


def test_unsupported_provider_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported configured",
    ):
        create_configured_generation_provider(
            generation_config=(
                generation_config(
                    provider="mystery-api",
                    model_name="unknown-model",
                )
            )
        )
