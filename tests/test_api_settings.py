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

    assert config.dense_backend == "numpy"

    assert str(config.generation_config) == ("configs/generation_v0_1.yaml")

    assert config.provider_config is None
    assert config.http_transport_config is None
    assert config.provider_runtime_config is None


def test_openai_runtime_selects_remote_configs() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_RUNTIME_MODE": ("openai"),
        }
    )

    config = settings.to_runtime_config()

    assert settings.mode == "openai"

    assert str(config.generation_config) == ("configs/generation_openai_v0_1.yaml")

    assert str(config.provider_config) == ("configs/provider_v0_1.yaml")

    assert str(config.http_transport_config) == ("configs/http_transport_openai_v0_1.yaml")

    assert str(config.provider_runtime_config) == ("configs/provider_runtime_openai_v0_1.yaml")


def test_pgvector_backend_can_be_selected() -> None:
    settings = load_api_runtime_settings(
        {
            "AERORAGX_DENSE_BACKEND": ("pgvector"),
        }
    )

    config = settings.to_runtime_config()

    assert settings.dense_backend == "pgvector"

    assert config.dense_backend == "pgvector"


def test_unknown_dense_backend_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=("AERORAGX_DENSE_BACKEND"),
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
        match=("AERORAGX_RUNTIME_MODE"),
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_RUNTIME_MODE": ("invalid"),
            }
        )


def test_evidence_depth_cannot_exceed_candidates() -> None:
    with pytest.raises(
        ValueError,
        match=("AERORAGX_EVIDENCE_TOP_K"),
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_CANDIDATE_TOP_K": ("4"),
                "AERORAGX_EVIDENCE_TOP_K": ("5"),
            }
        )
