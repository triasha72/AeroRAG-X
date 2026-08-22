"""Tests for AeroRAG-X API environment settings."""

from __future__ import annotations

import pytest

from aeroragx.api.settings import (
    load_api_runtime_settings,
)


def test_default_runtime_is_local() -> None:
    settings = load_api_runtime_settings({})

    config = settings.to_runtime_config()

    assert settings.mode == "local"
    assert settings.dense_backend == "numpy"
    assert settings.adaptive_retrieval_enabled is False
    assert settings.guardrails.max_request_bytes == 16_384
    assert settings.guardrails.rate_limit_requests == 60
    assert settings.guardrails.rate_limit_window_seconds == 60

    assert config.dense_backend == "numpy"
    assert config.adaptive_retrieval_config is None

    assert str(config.generation_config) == "configs/generation_v0_1.yaml"

    assert config.provider_config is None
    assert config.http_transport_config is None
    assert config.provider_runtime_config is None


def test_openai_runtime_selects_remote_configs() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_RUNTIME_MODE": "openai",
        }
    )

    config = settings.to_runtime_config()

    assert settings.mode == "openai"

    assert str(config.generation_config) == ("configs/generation_openai_v0_1.yaml")

    assert str(config.provider_config) == "configs/provider_v0_1.yaml"

    assert str(config.http_transport_config) == ("configs/http_transport_openai_v0_1.yaml")

    assert str(config.provider_runtime_config) == ("configs/provider_runtime_openai_v0_1.yaml")


def test_transformers_runtime_selects_local_llm_configs() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_RUNTIME_MODE": ("transformers"),
        }
    )

    config = settings.to_runtime_config()

    assert settings.mode == "transformers"

    assert str(config.generation_config) == ("configs/generation_transformers_v0_1.yaml")

    assert str(config.provider_config) == "configs/provider_v0_1.yaml"

    assert config.http_transport_config is None

    assert str(config.provider_runtime_config) == ("configs/transformers_runtime_v0_1.yaml")


def test_transformers_runtime_preserves_numpy_default() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_RUNTIME_MODE": ("transformers"),
        }
    )

    config = settings.to_runtime_config()

    assert settings.dense_backend == "numpy"

    assert config.dense_backend == "numpy"


def test_transformers_runtime_can_use_pgvector() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_RUNTIME_MODE": ("transformers"),
            "AERORAGX_DENSE_BACKEND": ("pgvector"),
        }
    )

    config = settings.to_runtime_config()

    assert settings.mode == "transformers"

    assert settings.dense_backend == "pgvector"

    assert config.dense_backend == "pgvector"


def test_pgvector_backend_can_be_selected() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_DENSE_BACKEND": ("pgvector"),
        }
    )

    config = settings.to_runtime_config()

    assert settings.dense_backend == "pgvector"

    assert config.dense_backend == "pgvector"


def test_adaptive_retrieval_can_be_enabled() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_ENABLE_ADAPTIVE_RETRIEVAL": "true",
        }
    )

    config = settings.to_runtime_config()

    assert settings.adaptive_retrieval_enabled is True
    assert str(config.adaptive_retrieval_config) == "configs/adaptive_retrieval_v0_1.yaml"


def test_unknown_dense_backend_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="AERORAGX_DENSE_BACKEND",
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_DENSE_BACKEND": ("invalid"),
            }
        )


def test_runtime_depths_can_be_overridden() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_CANDIDATE_TOP_K": ("30"),
            "AERORAGX_EVIDENCE_TOP_K": ("7"),
        }
    )

    assert settings.candidate_top_k == 30

    assert settings.evidence_top_k == 7


def test_unknown_runtime_mode_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="AERORAGX_RUNTIME_MODE",
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_RUNTIME_MODE": ("invalid"),
            }
        )


def test_evidence_depth_cannot_exceed_candidates() -> None:
    with pytest.raises(
        ValueError,
        match="AERORAGX_EVIDENCE_TOP_K",
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_CANDIDATE_TOP_K": ("4"),
                "AERORAGX_EVIDENCE_TOP_K": ("5"),
            }
        )


def test_invalid_adaptive_retrieval_switch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="AERORAGX_ENABLE_ADAPTIVE_RETRIEVAL",
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_ENABLE_ADAPTIVE_RETRIEVAL": "yes",
            }
        )


def test_request_guardrails_are_loaded_from_environment() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_MAX_REQUEST_BYTES": "4096",
            "AERORAGX_RATE_LIMIT_REQUESTS": "12",
            "AERORAGX_RATE_LIMIT_WINDOW_SECONDS": "30",
        }
    )

    assert settings.guardrails.max_request_bytes == 4096
    assert settings.guardrails.rate_limit_requests == 12
    assert settings.guardrails.rate_limit_window_seconds == 30


@pytest.mark.parametrize(
    "name",
    [
        "AERORAGX_MAX_REQUEST_BYTES",
        "AERORAGX_RATE_LIMIT_REQUESTS",
        "AERORAGX_RATE_LIMIT_WINDOW_SECONDS",
    ],
)
def test_request_guardrails_reject_non_positive_values(
    name: str,
) -> None:
    with pytest.raises(ValueError, match=name):
        load_api_runtime_settings({name: "0"})
