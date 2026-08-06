from collections.abc import Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.dense import (
    DenseConfig,
    DenseEncoder,
    DenseIndex,
    encode_chunks,
    load_dense_config,
    load_dense_index,
    write_dense_index,
    write_dense_search_results,
)

FloatMatrix = npt.NDArray[np.float32]
FloatVector = npt.NDArray[np.float32]


class FakeEncoder(DenseEncoder):
    """Deterministic encoder for unit tests."""

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
    """Create a test chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        page_ids=[f"{document_id}:page:1"],
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


def make_config() -> DenseConfig:
    """Create a test configuration."""

    return DenseConfig(
        model_name="test-model",
        batch_size=2,
        normalize_embeddings=True,
        default_top_k=10,
        device="cpu",
    )


def test_load_dense_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "dense.yaml"

    path.write_text(
        (
            'version: "0.1"\n'
            'model_name: "test-model"\n'
            "batch_size: 8\n"
            "normalize_embeddings: true\n"
            "default_top_k: 10\n"
            'device: "cpu"\n'
        ),
        encoding="utf-8",
    )

    config = load_dense_config(path)

    assert config.model_name == "test-model"
    assert config.batch_size == 8


def test_dense_search_ranks_relevant_chunk() -> None:
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

    config = make_config()
    encoder = FakeEncoder()

    embeddings = encode_chunks(
        chunks=chunks,
        config=config,
        encoder=encoder,
    )

    index = DenseIndex(
        embeddings=embeddings,
        chunks=chunks,
        config=config,
        encoder=encoder,
    )

    hits = index.search(
        query="battery safety",
        top_k=3,
    )

    assert len(hits) == 3
    assert hits[0].chunk.chunk_id == "101:chunk:00000"
    assert hits[0].score == 1.0


def test_empty_query_returns_no_hits() -> None:
    chunk = make_chunk(
        "101:chunk:00000",
        101,
        "battery cooling",
    )

    index = DenseIndex(
        embeddings=np.asarray(
            [[1.0, 0.0, 0.0]],
            dtype=np.float32,
        ),
        chunks=[chunk],
        config=make_config(),
        encoder=FakeEncoder(),
    )

    assert index.search("   ") == []


def test_dense_index_round_trip(
    tmp_path: Path,
) -> None:
    chunks = [
        make_chunk(
            "101:chunk:00000",
            101,
            "battery cooling",
        ),
        make_chunk(
            "102:chunk:00000",
            102,
            "fuel cell system",
        ),
    ]

    config = make_config()

    embeddings = encode_chunks(
        chunks=chunks,
        config=config,
        encoder=FakeEncoder(),
    )

    embeddings_path = tmp_path / "embeddings.npy"
    metadata_path = tmp_path / "metadata.jsonl"
    manifest_path = tmp_path / "manifest.json"

    write_dense_index(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
        manifest_path=manifest_path,
        embeddings=embeddings,
        chunks=chunks,
        config=config,
    )

    (
        loaded_embeddings,
        loaded_chunks,
        manifest,
    ) = load_dense_index(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
        manifest_path=manifest_path,
    )

    assert loaded_embeddings.shape == (2, 3)
    assert len(loaded_chunks) == 2
    assert manifest.chunk_count == 2
    assert manifest.embedding_dimension == 3


def test_dense_index_rejects_count_mismatch() -> None:
    chunks = [
        make_chunk(
            "101:chunk:00000",
            101,
            "battery cooling",
        )
    ]

    embeddings = np.zeros(
        (2, 3),
        dtype=np.float32,
    )

    with pytest.raises(
        ValueError,
        match="Embedding count",
    ):
        DenseIndex(
            embeddings=embeddings,
            chunks=chunks,
            config=make_config(),
            encoder=FakeEncoder(),
        )


def test_write_dense_results(
    tmp_path: Path,
) -> None:
    chunk = make_chunk(
        "101:chunk:00000",
        101,
        "battery cooling",
    )

    index = DenseIndex(
        embeddings=np.asarray(
            [[1.0, 0.0, 0.0]],
            dtype=np.float32,
        ),
        chunks=[chunk],
        config=make_config(),
        encoder=FakeEncoder(),
    )

    hits = index.search(
        query="battery",
        top_k=1,
    )

    output = tmp_path / "results.jsonl"

    write_dense_search_results(
        path=output,
        hits=hits,
    )

    assert output.exists()
    assert "101:chunk:00000" in output.read_text(encoding="utf-8")
