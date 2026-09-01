"""PostgreSQL + pgvector dense retrieval backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import numpy as np
import psycopg
import yaml
from pgvector.psycopg import register_vector
from psycopg import sql
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.dense import (
    DenseConfig,
    DenseEncoder,
    DenseIndexManifest,
    DenseSearchHit,
    FloatMatrix,
)


class PgVectorConfig(BaseModel):
    """Configuration for PostgreSQL + pgvector retrieval."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    backend: Literal["pgvector"] = "pgvector"

    database_url_env: str = Field(
        min_length=1,
    )

    table_name: str = Field(
        default="aerorag_chunks",
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )

    metric: Literal["cosine"] = "cosine"

    default_top_k: int = Field(
        default=10,
        ge=1,
        le=100,
    )
    index_method: Literal["exact", "hnsw"] = "exact"
    hnsw_m: int = Field(default=16, ge=2, le=100)
    hnsw_ef_construction: int = Field(default=64, ge=4, le=1000)
    hnsw_ef_search: int = Field(default=40, ge=1, le=1000)
    collapse_parent_chunks: bool = True
    parent_candidate_multiplier: int = Field(default=10, ge=1, le=100)


def load_pgvector_config(
    path: Path,
) -> PgVectorConfig:
    """Load and validate pgvector configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Vector-store configuration must contain a YAML mapping.")

    return PgVectorConfig.model_validate(raw_data)


def resolve_database_url(
    config: PgVectorConfig,
) -> str:
    """Resolve the database URL from the configured environment variable."""

    database_url = os.environ.get(
        config.database_url_env,
        "",
    ).strip()

    if not database_url:
        raise ValueError(f"Environment variable {config.database_url_env!r} is not set.")

    return database_url


def initialize_pgvector_schema(
    *,
    database_url: str,
    config: PgVectorConfig,
    embedding_dimension: int,
) -> None:
    """Create the pgvector extension and retrieval tables."""

    if embedding_dimension < 1:
        raise ValueError("embedding_dimension must be positive.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        connection.commit()

        register_vector(connection)

        create_chunks = sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {table} (
                chunk_id TEXT PRIMARY KEY,
                parent_chunk_id TEXT,
                document_id BIGINT NOT NULL,
                chunk_index INTEGER NOT NULL,

                page_start INTEGER NOT NULL,
                page_end INTEGER NOT NULL,
                page_ids JSONB NOT NULL,

                text TEXT NOT NULL,

                word_count INTEGER NOT NULL,
                character_count INTEGER NOT NULL,
                token_estimate INTEGER NOT NULL,

                citation_url TEXT NOT NULL,
                source_url TEXT NOT NULL,
                document_sha256 TEXT NOT NULL,
                title TEXT,
                publication_year INTEGER,
                subject_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
                document_type TEXT,
                programs JSONB NOT NULL DEFAULT '[]'::jsonb,
                report_family TEXT,

                embedding vector({dimension}) NOT NULL,

                embedding_model TEXT NOT NULL,
                index_version TEXT NOT NULL,

                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        ).format(
            table=sql.Identifier(config.table_name),
            dimension=sql.SQL(str(embedding_dimension)),
        )

        create_metadata = """
            CREATE TABLE IF NOT EXISTS aerorag_index_metadata (
                table_name TEXT PRIMARY KEY,
                index_version TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                embedding_dimension INTEGER NOT NULL,
                normalized BOOLEAN NOT NULL,
                chunk_count INTEGER NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """

        with connection.cursor() as cursor:
            cursor.execute(create_chunks)
            cursor.execute(create_metadata)
            cursor.execute(
                sql.SQL(
                    """
                    ALTER TABLE {table}
                    ADD COLUMN IF NOT EXISTS parent_chunk_id TEXT,
                    ADD COLUMN IF NOT EXISTS title TEXT,
                    ADD COLUMN IF NOT EXISTS publication_year INTEGER,
                    ADD COLUMN IF NOT EXISTS subject_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
                    ADD COLUMN IF NOT EXISTS document_type TEXT,
                    ADD COLUMN IF NOT EXISTS programs JSONB NOT NULL DEFAULT '[]'::jsonb,
                    ADD COLUMN IF NOT EXISTS report_family TEXT
                    """
                ).format(table=sql.Identifier(config.table_name))
            )
            cursor.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {index} ON {table} (parent_chunk_id)").format(
                    index=sql.Identifier(f"{config.table_name}_parent_chunk"),
                    table=sql.Identifier(config.table_name),
                )
            )

            if config.index_method == "hnsw":
                index_name = f"{config.table_name}_embedding_hnsw"
                create_hnsw = sql.SQL(
                    """
                    CREATE INDEX IF NOT EXISTS {index}
                    ON {table}
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = {m}, ef_construction = {ef_construction})
                    """
                ).format(
                    index=sql.Identifier(index_name),
                    table=sql.Identifier(config.table_name),
                    m=sql.Literal(config.hnsw_m),
                    ef_construction=sql.Literal(config.hnsw_ef_construction),
                )
                cursor.execute(create_hnsw)

        connection.commit()


def upsert_dense_index(
    *,
    database_url: str,
    config: PgVectorConfig,
    embeddings: FloatMatrix,
    chunks: list[ChunkRecord],
    manifest: DenseIndexManifest,
) -> int:
    """Persist an existing AeroRAG-X dense index in PostgreSQL."""

    if embeddings.ndim != 2:
        raise ValueError("Embeddings must be a two-dimensional matrix.")

    if embeddings.shape[0] != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    if embeddings.shape[1] != manifest.embedding_dimension:
        raise ValueError("Embedding dimension differs from the index manifest.")

    if len(chunks) != manifest.chunk_count:
        raise ValueError("Chunk count differs from the index manifest.")

    initialize_pgvector_schema(
        database_url=database_url,
        config=config,
        embedding_dimension=manifest.embedding_dimension,
    )

    insert_statement = sql.SQL(
        """
        INSERT INTO {table} (
            chunk_id,
            parent_chunk_id,
            document_id,
            chunk_index,
            page_start,
            page_end,
            page_ids,
            text,
            word_count,
            character_count,
            token_estimate,
            citation_url,
            source_url,
            document_sha256,
            title,
            publication_year,
            subject_categories,
            document_type,
            programs,
            report_family,
            embedding,
            embedding_model,
            index_version
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (chunk_id)
        DO UPDATE SET
            document_id = EXCLUDED.document_id,
            parent_chunk_id = EXCLUDED.parent_chunk_id,
            chunk_index = EXCLUDED.chunk_index,
            page_start = EXCLUDED.page_start,
            page_end = EXCLUDED.page_end,
            page_ids = EXCLUDED.page_ids,
            text = EXCLUDED.text,
            word_count = EXCLUDED.word_count,
            character_count = EXCLUDED.character_count,
            token_estimate = EXCLUDED.token_estimate,
            citation_url = EXCLUDED.citation_url,
            source_url = EXCLUDED.source_url,
            document_sha256 = EXCLUDED.document_sha256,
            title = EXCLUDED.title,
            publication_year = EXCLUDED.publication_year,
            subject_categories = EXCLUDED.subject_categories,
            document_type = EXCLUDED.document_type,
            programs = EXCLUDED.programs,
            report_family = EXCLUDED.report_family,
            embedding = EXCLUDED.embedding,
            embedding_model = EXCLUDED.embedding_model,
            index_version = EXCLUDED.index_version,
            updated_at = NOW()
        """
    ).format(table=sql.Identifier(config.table_name))

    rows = []

    for chunk, embedding in zip(
        chunks,
        embeddings,
        strict=True,
    ):
        rows.append(
            (
                chunk.chunk_id,
                chunk.parent_chunk_id,
                chunk.document_id,
                chunk.chunk_index,
                chunk.page_start,
                chunk.page_end,
                Jsonb(chunk.page_ids),
                chunk.text,
                chunk.word_count,
                chunk.character_count,
                chunk.token_estimate,
                chunk.citation_url,
                chunk.source_url,
                chunk.document_sha256,
                chunk.title,
                chunk.publication_year,
                Jsonb(chunk.subject_categories),
                chunk.document_type,
                Jsonb(chunk.programs),
                chunk.report_family,
                np.asarray(
                    embedding,
                    dtype=np.float32,
                ),
                manifest.model_name,
                manifest.version,
            )
        )

    with psycopg.connect(database_url) as connection:
        register_vector(connection)

        with connection.cursor() as cursor:
            cursor.executemany(
                insert_statement,
                rows,
            )

            cursor.execute(
                """
                INSERT INTO aerorag_index_metadata (
                    table_name,
                    index_version,
                    embedding_model,
                    embedding_dimension,
                    normalized,
                    chunk_count
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (table_name)
                DO UPDATE SET
                    index_version = EXCLUDED.index_version,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding_dimension = EXCLUDED.embedding_dimension,
                    normalized = EXCLUDED.normalized,
                    chunk_count = EXCLUDED.chunk_count,
                    updated_at = NOW()
                """,
                (
                    config.table_name,
                    manifest.version,
                    manifest.model_name,
                    manifest.embedding_dimension,
                    manifest.normalized,
                    manifest.chunk_count,
                ),
            )

        connection.commit()

    return len(rows)


def _normalize_query(
    query_matrix: FloatMatrix,
) -> FloatMatrix:
    """Normalize one query vector."""

    if query_matrix.ndim != 2:
        raise ValueError("Query embedding must be a two-dimensional matrix.")

    if query_matrix.shape[0] != 1:
        raise ValueError("Query encoder must return exactly one vector.")

    norm = float(np.linalg.norm(query_matrix[0]))

    if norm == 0.0:
        raise ValueError("Query embedding has zero length.")

    return np.asarray(
        query_matrix / norm,
        dtype=np.float32,
    )


class PgVectorIndex:
    """Dense retrieval using PostgreSQL + pgvector."""

    def __init__(
        self,
        *,
        database_url: str,
        config: PgVectorConfig,
        dense_config: DenseConfig,
        encoder: DenseEncoder,
        manifest: DenseIndexManifest,
    ) -> None:
        self._database_url = database_url
        self._config = config
        self._dense_config = dense_config
        self._encoder = encoder
        self._manifest = manifest

    @property
    def document_count(self) -> int:
        """Return the number of indexed chunks."""

        query = sql.SQL("SELECT COUNT(*) FROM {table}").format(
            table=sql.Identifier(self._config.table_name)
        )

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()

        if result is None:
            return 0

        return int(result[0])

    @property
    def embedding_dimension(self) -> int:
        """Return the embedding dimension."""

        return self._manifest.embedding_dimension

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[DenseSearchHit]:
        """Search PostgreSQL using exact cosine similarity."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        stripped_query = query.strip()

        if not stripped_query:
            return []

        query_matrix = np.asarray(
            self._encoder.encode_query(
                [stripped_query],
                batch_size=1,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=(self._dense_config.normalize_embeddings),
            ),
            dtype=np.float32,
        )

        normalized_query = _normalize_query(query_matrix)[0]

        if normalized_query.shape[0] != self.embedding_dimension:
            raise ValueError("Query and corpus embedding dimensions differ.")

        base_columns = sql.SQL(
            """
            SELECT
                chunk_id,
                parent_chunk_id,
                document_id,
                chunk_index,
                page_start,
                page_end,
                page_ids,
                text,
                word_count,
                character_count,
                token_estimate,
                citation_url,
                source_url,
                document_sha256,
                title,
                publication_year,
                subject_categories,
                document_type,
                programs,
                report_family,
                1.0 - (embedding <=> %s) AS similarity
            FROM {table}
            """
        ).format(table=sql.Identifier(self._config.table_name))

        parameters: tuple[Any, ...]
        if self._config.collapse_parent_chunks:
            statement = sql.SQL(
                """
                WITH candidates AS (
                    {base}
                    ORDER BY embedding <=> %s, chunk_id
                    LIMIT %s
                ), best_children AS (
                    SELECT DISTINCT ON (COALESCE(parent_chunk_id, chunk_id)) *
                    FROM candidates
                    ORDER BY COALESCE(parent_chunk_id, chunk_id), similarity DESC, chunk_id
                )
                SELECT * FROM best_children
                ORDER BY similarity DESC, chunk_id
                LIMIT %s
                """
            ).format(base=base_columns)
            parameters = (
                normalized_query,
                normalized_query,
                top_k * self._config.parent_candidate_multiplier,
                top_k,
            )
        else:
            statement = sql.SQL(
                """
                {base}
            ORDER BY
                embedding <=> %s,
                chunk_id
            LIMIT %s
            """
            ).format(base=base_columns)
            parameters = (normalized_query, normalized_query, top_k)

        with psycopg.connect(self._database_url) as connection:
            register_vector(connection)

            with connection.cursor() as cursor:
                if self._config.index_method == "hnsw":
                    cursor.execute(
                        "SET LOCAL hnsw.ef_search = %s",
                        (self._config.hnsw_ef_search,),
                    )
                cursor.execute(
                    statement,
                    parameters,
                )

                rows = cursor.fetchall()

        hits: list[DenseSearchHit] = []

        for rank, row in enumerate(
            rows,
            start=1,
        ):
            chunk = ChunkRecord(
                chunk_id=row[0],
                parent_chunk_id=row[1],
                document_id=row[2],
                chunk_index=row[3],
                page_start=row[4],
                page_end=row[5],
                page_ids=row[6],
                text=row[7],
                word_count=row[8],
                character_count=row[9],
                token_estimate=row[10],
                citation_url=row[11],
                source_url=row[12],
                document_sha256=row[13],
                title=row[14],
                publication_year=row[15],
                subject_categories=row[16],
                document_type=row[17],
                programs=row[18],
                report_family=row[19],
            )

            similarity = float(
                np.clip(
                    row[20],
                    -1.0,
                    1.0,
                )
            )

            hits.append(
                DenseSearchHit(
                    rank=rank,
                    score=round(
                        similarity,
                        8,
                    ),
                    chunk=chunk,
                )
            )

        return hits
