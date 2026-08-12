"""Tests for reusable AeroRAG-X runtime construction."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import aeroragx.retrieval.pgvector_store as pgvector_module
import aeroragx.runtime as runtime_module
from aeroragx.runtime import (
    RuntimeConfig,
    RuntimeConfigurationError,
    load_grounded_runtime,
    load_hybrid_index,
)


def test_runtime_defaults_to_local_generation() -> None:
    config = RuntimeConfig()

    assert str(config.generation_config) == "configs/generation_v0_1.yaml"

    assert str(config.sufficiency_config) == ("configs/sufficiency_v0_2_1.yaml")

    assert str(config.facet_retrieval_config) == ("configs/facet_retrieval_v0_1.yaml")

    assert config.adaptive_retrieval_config is None


def test_runtime_defaults_to_numpy_dense_backend() -> None:
    config = RuntimeConfig()

    assert config.dense_backend == "numpy"

    assert str(config.vector_store_config) == ("configs/vector_store_v0_1.yaml")


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


def test_runtime_loads_the_opt_in_adaptive_retrieval_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_reranker_settings = SimpleNamespace(
        candidate_top_k=20,
    )
    fake_generation_settings = SimpleNamespace(
        evidence_top_k=5,
    )
    fake_adaptive_settings = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        runtime_module,
        "load_reranker_index",
        lambda config: (object(), fake_reranker_settings),
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
    monkeypatch.setattr(
        runtime_module,
        "create_configured_generation_provider",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        runtime_module,
        "load_sufficiency_config",
        lambda path: object(),
    )
    monkeypatch.setattr(
        runtime_module,
        "load_adaptive_retrieval_config",
        lambda path: fake_adaptive_settings,
    )

    def fake_generator(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        runtime_module,
        "GroundedAnswerGenerator",
        fake_generator,
    )

    runtime = load_grounded_runtime(
        RuntimeConfig(
            facet_retrieval_config=None,
            adaptive_retrieval_config=Path("configs/adaptive_retrieval_v0_1.yaml"),
        )
    )

    assert runtime.generator is not None
    assert captured["adaptive_retrieval_config"] is fake_adaptive_settings


def _stub_retrieval_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    SimpleNamespace,
    SimpleNamespace,
    SimpleNamespace,
]:
    """Install lightweight runtime dependencies."""

    fake_chunks = [
        SimpleNamespace(
            chunk_id="chunk-001",
        )
    ]

    fake_dense_settings = SimpleNamespace(
        model_name="test-model",
    )

    fake_manifest = SimpleNamespace(
        version="0.1",
        model_name="test-model",
        chunk_count=1,
        embedding_dimension=3,
        normalized=True,
    )

    monkeypatch.setattr(
        runtime_module,
        "load_chunk_records",
        lambda path: fake_chunks,
    )

    monkeypatch.setattr(
        runtime_module,
        "load_bm25_config",
        lambda path: object(),
    )

    monkeypatch.setattr(
        runtime_module,
        "load_dense_config",
        lambda path: fake_dense_settings,
    )

    monkeypatch.setattr(
        runtime_module,
        "load_hybrid_config",
        lambda path: object(),
    )

    monkeypatch.setattr(
        runtime_module,
        "BM25Index",
        lambda **kwargs: object(),
    )

    monkeypatch.setattr(
        runtime_module,
        "load_dense_index",
        lambda **kwargs: (
            object(),
            fake_chunks,
            fake_manifest,
        ),
    )

    fake_encoder = SimpleNamespace()

    monkeypatch.setattr(
        runtime_module,
        "load_dense_encoder",
        lambda config: fake_encoder,
    )

    return (
        fake_dense_settings,
        fake_manifest,
        fake_encoder,
    )


def test_runtime_selects_pgvector_dense_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_retrieval_runtime(monkeypatch)

    fake_pgvector_index = SimpleNamespace(
        document_count=1,
    )

    fake_vector_settings = SimpleNamespace()

    monkeypatch.setattr(
        pgvector_module,
        "load_pgvector_config",
        lambda path: fake_vector_settings,
    )

    monkeypatch.setattr(
        pgvector_module,
        "resolve_database_url",
        lambda config: "postgresql://test",
    )

    monkeypatch.setattr(
        pgvector_module,
        "PgVectorIndex",
        lambda **kwargs: fake_pgvector_index,
    )

    captured: dict[
        str,
        object,
    ] = {}

    def fake_hybrid_index(
        *,
        bm25_index: object,
        dense_index: object,
        config: object,
    ) -> object:
        captured["bm25_index"] = bm25_index

        captured["dense_index"] = dense_index

        captured["config"] = config

        return object()

    monkeypatch.setattr(
        runtime_module,
        "HybridIndex",
        fake_hybrid_index,
    )

    load_hybrid_index(
        RuntimeConfig(
            dense_backend="pgvector",
        )
    )

    assert captured["dense_index"] is fake_pgvector_index


def test_runtime_rejects_pgvector_chunk_count_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_retrieval_runtime(monkeypatch)

    fake_pgvector_index = SimpleNamespace(
        document_count=2,
    )

    monkeypatch.setattr(
        pgvector_module,
        "load_pgvector_config",
        lambda path: SimpleNamespace(),
    )

    monkeypatch.setattr(
        pgvector_module,
        "resolve_database_url",
        lambda config: "postgresql://test",
    )

    monkeypatch.setattr(
        pgvector_module,
        "PgVectorIndex",
        lambda **kwargs: fake_pgvector_index,
    )

    with pytest.raises(
        RuntimeConfigurationError,
        match="chunk count",
    ):
        load_hybrid_index(
            RuntimeConfig(
                dense_backend="pgvector",
            )
        )
