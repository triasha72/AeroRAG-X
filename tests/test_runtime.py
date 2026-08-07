"""Tests for reusable AeroRAG-X runtime construction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import aeroragx.runtime as runtime_module
from aeroragx.runtime import (
    RuntimeConfig,
    RuntimeConfigurationError,
    load_grounded_runtime,
)


def test_runtime_defaults_to_local_generation() -> None:
    config = RuntimeConfig()

    assert str(config.generation_config) == "configs/generation_v0_1.yaml"

    assert str(config.sufficiency_config) == ("configs/sufficiency_v0_2_1.yaml")

    assert str(config.facet_retrieval_config) == ("configs/facet_retrieval_v0_1.yaml")


def test_runtime_rejects_evidence_depth_above_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_reranker_settings = SimpleNamespace(
        candidate_top_k=4,
    )

    fake_generation_settings = SimpleNamespace(
        evidence_top_k=5,
    )

    monkeypatch.setattr(
        runtime_module,
        "load_reranker_index",
        lambda config: (
            object(),
            fake_reranker_settings,
        ),
    )

    monkeypatch.setattr(
        runtime_module,
        "load_generation_config",
        lambda path: object(),
    )

    monkeypatch.setattr(
        runtime_module,
        "with_evidence_top_k",
        lambda config, top_k: fake_generation_settings,
    )

    with pytest.raises(
        RuntimeConfigurationError,
        match=("evidence_top_k must not exceed the reranker candidate_top_k"),
    ):
        load_grounded_runtime(
            RuntimeConfig(
                facet_retrieval_config=None,
            )
        )
