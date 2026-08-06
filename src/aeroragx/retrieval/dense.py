"""Exact dense retrieval over citation-preserving aerospace chunks."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

import numpy as np
import numpy.typing as npt
import yaml
from pydantic import BaseModel, ConfigDict, Field
from sentence_transformers import SentenceTransformer

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.bm25 import load_chunk_records

FloatMatrix = npt.NDArray[np.float32]


class DenseEncoder(Protocol):
    """Interface required from a dense text encoder."""

    def encode_document(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
    ) -> FloatMatrix:
        """Encode corpus documents."""

    def encode_query(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
    ) -> FloatMatrix:
        """Encode search queries."""


class DenseConfig(BaseModel):
    """Configuration for exact dense retrieval."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    model_name: str = Field(min_length=1)
    batch_size: int = Field(
        default=32,
        ge=1,
        le=512,
    )
    normalize_embeddings: bool = True
    default_top_k: int = Field(
        default=10,
        ge=1,
        le=100,
    )
    device: str = Field(
        default="cpu",
        min_length=1,
    )


class DenseIndexManifest(BaseModel):
    """Metadata describing a persisted dense index."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str
    model_name: str
    chunk_count: int = Field(ge=1)
    embedding_dimension: int = Field(ge=1)
    normalized: bool


class DenseSearchHit(BaseModel):
    """One ranked dense-retrieval result."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    score: float = Field(
        ge=-1.0,
        le=1.0,
    )
    chunk: ChunkRecord


def load_dense_config(
    path: Path,
) -> DenseConfig:
    """Load and validate dense configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Dense configuration must contain a YAML mapping.")

    return DenseConfig.model_validate(raw_data)


def load_dense_encoder(
    config: DenseConfig,
) -> DenseEncoder:
    """Load the configured Sentence Transformer."""

    encoder = SentenceTransformer(
        config.model_name,
        device=config.device,
    )

    return cast(DenseEncoder, encoder)


def encode_chunks(
    chunks: Sequence[ChunkRecord],
    config: DenseConfig,
    encoder: DenseEncoder,
) -> FloatMatrix:
    """Encode all corpus chunks."""

    if not chunks:
        raise ValueError("At least one chunk is required.")

    embeddings = np.asarray(
        encoder.encode_document(
            [chunk.text for chunk in chunks],
            batch_size=config.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=(config.normalize_embeddings),
        ),
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise ValueError("Dense encoder must return a two-dimensional matrix.")

    if embeddings.shape[0] != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    if embeddings.shape[1] < 1:
        raise ValueError("Embedding dimension must be positive.")

    return embeddings


def write_dense_index(
    embeddings_path: Path,
    metadata_path: Path,
    manifest_path: Path,
    embeddings: FloatMatrix,
    chunks: Sequence[ChunkRecord],
    config: DenseConfig,
) -> DenseIndexManifest:
    """Persist embeddings and aligned chunk metadata."""

    if embeddings.ndim != 2:
        raise ValueError("Embeddings must be a two-dimensional matrix.")

    if embeddings.shape[0] != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    embeddings_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    metadata_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    manifest_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        embeddings_path,
        embeddings,
        allow_pickle=False,
    )

    metadata_content = "\n".join(
        json.dumps(
            chunk.model_dump(mode="json"),
            sort_keys=True,
        )
        for chunk in chunks
    )

    if metadata_content:
        metadata_content += "\n"

    metadata_path.write_text(
        metadata_content,
        encoding="utf-8",
    )

    manifest = DenseIndexManifest(
        version=config.version,
        model_name=config.model_name,
        chunk_count=len(chunks),
        embedding_dimension=embeddings.shape[1],
        normalized=config.normalize_embeddings,
    )

    manifest_path.write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    return manifest


def load_dense_index(
    embeddings_path: Path,
    metadata_path: Path,
    manifest_path: Path,
) -> tuple[
    FloatMatrix,
    list[ChunkRecord],
    DenseIndexManifest,
]:
    """Load and validate a persisted dense index."""

    embeddings = np.asarray(
        np.load(
            embeddings_path,
            allow_pickle=False,
        ),
        dtype=np.float32,
    )

    chunks = load_chunk_records(metadata_path)

    manifest = DenseIndexManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    if embeddings.ndim != 2:
        raise ValueError("Stored embeddings must be a two-dimensional matrix.")

    if embeddings.shape[0] != len(chunks):
        raise ValueError("Stored embedding and metadata counts differ.")

    if len(chunks) != manifest.chunk_count:
        raise ValueError("Metadata count differs from the index manifest.")

    if embeddings.shape[1] != manifest.embedding_dimension:
        raise ValueError("Embedding dimension differs from the manifest.")

    return embeddings, chunks, manifest


def _normalize_rows(
    matrix: FloatMatrix,
) -> FloatMatrix:
    """Normalize matrix rows to unit length."""

    norms = np.linalg.norm(
        matrix,
        axis=1,
        keepdims=True,
    )

    if np.any(norms == 0.0):
        raise ValueError("Dense index contains a zero-length vector.")

    return np.asarray(
        matrix / norms,
        dtype=np.float32,
    )


class DenseIndex:
    """Exact cosine-similarity dense index."""

    def __init__(
        self,
        embeddings: FloatMatrix,
        chunks: Sequence[ChunkRecord],
        config: DenseConfig,
        encoder: DenseEncoder,
    ) -> None:
        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be a two-dimensional matrix.")

        if embeddings.shape[0] != len(chunks):
            raise ValueError("Embedding count does not match chunk count.")

        if not chunks:
            raise ValueError("Dense index requires at least one chunk.")

        self._embeddings = _normalize_rows(
            np.asarray(
                embeddings,
                dtype=np.float32,
            )
        )
        self._chunks = list(chunks)
        self._config = config
        self._encoder = encoder

    @property
    def document_count(self) -> int:
        """Return the number of indexed chunks."""

        return len(self._chunks)

    @property
    def embedding_dimension(self) -> int:
        """Return the embedding dimension."""

        return int(self._embeddings.shape[1])

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[DenseSearchHit]:
        """Search the index using cosine similarity."""

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
                normalize_embeddings=(self._config.normalize_embeddings),
            ),
            dtype=np.float32,
        )

        if query_matrix.ndim != 2 or query_matrix.shape[0] != 1:
            raise ValueError("Query encoder must return exactly one vector.")

        if query_matrix.shape[1] != self.embedding_dimension:
            raise ValueError("Query and corpus embedding dimensions differ.")

        normalized_query = _normalize_rows(query_matrix)[0]

        scores = self._embeddings @ normalized_query

        ranked_indices = sorted(
            range(len(self._chunks)),
            key=lambda index: (
                -float(scores[index]),
                self._chunks[index].chunk_id,
            ),
        )

        hits: list[DenseSearchHit] = []

        for rank, index in enumerate(
            ranked_indices[:top_k],
            start=1,
        ):
            score = float(
                np.clip(
                    scores[index],
                    -1.0,
                    1.0,
                )
            )

            hits.append(
                DenseSearchHit(
                    rank=rank,
                    score=round(score, 8),
                    chunk=self._chunks[index],
                )
            )

        return hits


def write_dense_search_results(
    path: Path,
    hits: Sequence[DenseSearchHit],
) -> None:
    """Write dense search results as JSONL."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = "\n".join(
        json.dumps(
            hit.model_dump(mode="json"),
            sort_keys=True,
        )
        for hit in hits
    )

    if content:
        content += "\n"

    path.write_text(
        content,
        encoding="utf-8",
    )
