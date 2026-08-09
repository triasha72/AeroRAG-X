"""Tests for the PostgreSQL + pgvector dense retrieval backend."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

import numpy as np
import numpy.typing as npt
import psycopg
import pytest
from psycopg import sql

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.dense import (
    DenseConfig,
    DenseEncoder,
    DenseIndex,
    DenseIndexManifest,
    FloatMatrix,
    encode_chunks,
)
from aeroragx.retrieval.pgvector_store import (
    PgVectorConfig,
    PgVectorIndex,
    load_pgvector_config,
    resolve_database_url,
    upsert_dense_index,
)

FloatVector = npt.NDArray[np.float32]


class FakeEncoder(DenseEncoder):
    """Deterministic encoder for pgvector tests."""

    @staticmethod
    def _vector(text: str) -> FloatVector:
        lowered = text.lower()

        if "battery" in lowered:
            values = [1.0, 0.0, 0.0]
        elif "fuel cell" in lowered:
            values = [0.0, 1.0, 0.0]
        else:
            values = [0.0, 0.0, 1.0]

        return np.asarray(
            values,
            dtype=np.float32,
        )

    def encode_document(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
    ) -> FloatMatrix:
        del batch_size
        del show_progress_bar
        del convert_to_numpy
        del normalize_embeddings

        return np.asarray(
            np.vstack([self._vector(sentence) for sentence in sentences]),
            dtype=np.float32,
        )

    def encode_query(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
    ) -> FloatMatrix:
        return self.encode_document(
            sentences,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=convert_to_numpy,
            normalize_embeddings=normalize_embeddings,
        )


def make_chunk(
    chunk_id: str,
    document_id: int,
    text: str,
) -> ChunkRecord:
    """Create one deterministic test chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        page_ids=[
            f"{document_id}:page:1",
        ],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(
            1,
            len(text) // 4,
        ),
        citation_url=(f"https://ntrs.nasa.gov/citations/{document_id}"),
        source_url=(f"https://example.com/{document_id}.pdf"),
        document_sha256="test-checksum",
    )


def make_dense_config() -> DenseConfig:
    """Create deterministic dense configuration."""

    return DenseConfig(
        version="0.1",
        model_name="test-model",
        batch_size=2,
        normalize_embeddings=True,
        default_top_k=10,
        device="cpu",
    )


def make_manifest(
    chunk_count: int,
    embedding_dimension: int = 3,
) -> DenseIndexManifest:
    """Create a deterministic dense-index manifest."""

    return DenseIndexManifest(
        version="0.1",
        model_name="test-model",
        chunk_count=chunk_count,
        embedding_dimension=embedding_dimension,
        normalized=True,
    )


def test_load_pgvector_config(
    tmp_path: Path,
) -> None:
    """Vector-store YAML should load into validated configuration."""

    config_path = tmp_path / "vector.yaml"

    config_path.write_text(
        (
            'version: "0.1"\n'
            'backend: "pgvector"\n'
            'database_url_env: "TEST_VECTOR_DATABASE_URL"\n'
            'table_name: "test_chunks"\n'
            'metric: "cosine"\n'
            "default_top_k: 7\n"
        ),
        encoding="utf-8",
    )

    config = load_pgvector_config(config_path)

    assert config.backend == "pgvector"
    assert config.table_name == "test_chunks"
    assert config.metric == "cosine"
    assert config.default_top_k == 7


def test_resolve_database_url_rejects_missing_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing database credentials should fail explicitly."""

    environment_name = "AERORAGX_TEST_MISSING_DATABASE_URL"

    monkeypatch.delenv(
        environment_name,
        raising=False,
    )

    config = PgVectorConfig(
        database_url_env=environment_name,
    )

    with pytest.raises(
        ValueError,
        match="is not set",
    ):
        resolve_database_url(config)


def test_pgvector_index_rejects_invalid_top_k() -> None:
    """top_k must remain positive."""

    index = PgVectorIndex(
        database_url="postgresql://unused",
        config=PgVectorConfig(
            database_url_env="UNUSED",
        ),
        dense_config=make_dense_config(),
        encoder=FakeEncoder(),
        manifest=make_manifest(1),
    )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        index.search(
            "battery",
            top_k=0,
        )


def test_pgvector_empty_query_returns_no_hits() -> None:
    """Blank queries should not reach the database."""

    index = PgVectorIndex(
        database_url="postgresql://unused",
        config=PgVectorConfig(
            database_url_env="UNUSED",
        ),
        dense_config=make_dense_config(),
        encoder=FakeEncoder(),
        manifest=make_manifest(1),
    )

    assert index.search("   ") == []


def test_upsert_rejects_embedding_dimension_mismatch() -> None:
    """Persisted vectors must agree with manifest dimensionality."""

    chunks = [
        make_chunk(
            "101:chunk:00000",
            101,
            "battery cooling",
        )
    ]

    embeddings = np.asarray(
        [[1.0, 0.0, 0.0]],
        dtype=np.float32,
    )

    manifest = make_manifest(
        chunk_count=1,
        embedding_dimension=4,
    )

    with pytest.raises(
        ValueError,
        match="Embedding dimension",
    ):
        upsert_dense_index(
            database_url="postgresql://unused",
            config=PgVectorConfig(
                database_url_env="UNUSED",
            ),
            embeddings=embeddings,
            chunks=chunks,
            manifest=manifest,
        )


def test_pgvector_matches_numpy_dense_backend() -> None:
    """pgvector should preserve exact dense-retrieval behavior."""

    database_url = os.environ.get("AERORAGX_VECTOR_DATABASE_URL")

    if not database_url:
        pytest.skip("AERORAGX_VECTOR_DATABASE_URL is not configured.")

    table_name = f"aerorag_test_{uuid4().hex[:12]}"

    vector_config = PgVectorConfig(
        database_url_env=("AERORAGX_VECTOR_DATABASE_URL"),
        table_name=table_name,
    )

    chunks = [
        make_chunk(
            "101:chunk:00000",
            101,
            "battery thermal runaway cooling",
        ),
        make_chunk(
            "102:chunk:00000",
            102,
            "fuel cell aircraft propulsion",
        ),
        make_chunk(
            "103:chunk:00000",
            103,
            "airport operations",
        ),
    ]

    dense_config = make_dense_config()
    encoder = FakeEncoder()

    embeddings = encode_chunks(
        chunks=chunks,
        config=dense_config,
        encoder=encoder,
    )

    manifest = make_manifest(
        chunk_count=len(chunks),
        embedding_dimension=3,
    )

    try:
        inserted = upsert_dense_index(
            database_url=database_url,
            config=vector_config,
            embeddings=embeddings,
            chunks=chunks,
            manifest=manifest,
        )

        assert inserted == 3

        numpy_index = DenseIndex(
            embeddings=embeddings,
            chunks=chunks,
            config=dense_config,
            encoder=encoder,
        )

        pgvector_index = PgVectorIndex(
            database_url=database_url,
            config=vector_config,
            dense_config=dense_config,
            encoder=encoder,
            manifest=manifest,
        )

        assert pgvector_index.document_count == len(chunks)

        for query in (
            "battery safety",
            "fuel cell propulsion",
            "airport operations",
        ):
            numpy_hits = numpy_index.search(
                query,
                top_k=3,
            )

            pgvector_hits = pgvector_index.search(
                query,
                top_k=3,
            )

            assert [hit.chunk.chunk_id for hit in pgvector_hits] == [
                hit.chunk.chunk_id for hit in numpy_hits
            ]

            for numpy_hit, pgvector_hit in zip(
                numpy_hits,
                pgvector_hits,
                strict=True,
            ):
                assert pgvector_hit.score == pytest.approx(
                    numpy_hit.score,
                    abs=1e-6,
                )

    finally:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name))
                )

                cursor.execute(
                    """
                    SELECT to_regclass(
                        'public.aerorag_index_metadata'
                    )
                    """
                )

                metadata_table = cursor.fetchone()

                if metadata_table is not None and metadata_table[0] is not None:
                    cursor.execute(
                        """
                        DELETE
                        FROM aerorag_index_metadata
                        WHERE table_name = %s
                        """,
                        (table_name,),
                    )

            connection.commit()
