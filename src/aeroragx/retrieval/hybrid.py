"""Reciprocal-rank-fusion retrieval over BM25 and dense rankings."""

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.evaluation.retrieval import RetrievalHit, RetrievalIndex
from aeroragx.processing.chunking import ChunkRecord

RetrieverName = Literal["bm25", "dense"]


class HybridConfig(BaseModel):
    """Configuration for reciprocal-rank-fusion retrieval."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    rrf_k: int = Field(default=60, ge=1, le=10_000)
    bm25_top_k: int = Field(default=50, ge=1, le=100)
    dense_top_k: int = Field(default=50, ge=1, le=100)
    default_top_k: int = Field(default=10, ge=1, le=100)


class HybridSearchHit(BaseModel):
    """One hybrid result with complete source-rank provenance."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    score: float = Field(gt=0.0)
    chunk: ChunkRecord
    retrieved_by: list[RetrieverName] = Field(min_length=1)

    bm25_rank: int | None = Field(default=None, ge=1)
    bm25_score: float | None = Field(default=None, ge=0.0)

    dense_rank: int | None = Field(default=None, ge=1)
    dense_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_source_metadata(self) -> Self:
        """Ensure source labels agree with source rank and score fields."""

        if len(self.retrieved_by) != len(set(self.retrieved_by)):
            raise ValueError("retrieved_by must not contain duplicates.")

        bm25_rank_present = self.bm25_rank is not None
        bm25_score_present = self.bm25_score is not None

        if bm25_rank_present != bm25_score_present:
            raise ValueError(
                "bm25_rank and bm25_score must either both be present or both be absent."
            )

        dense_rank_present = self.dense_rank is not None
        dense_score_present = self.dense_score is not None

        if dense_rank_present != dense_score_present:
            raise ValueError(
                "dense_rank and dense_score must either both be present or both be absent."
            )

        source_names = set(self.retrieved_by)

        if ("bm25" in source_names) != bm25_rank_present:
            raise ValueError(
                "BM25 metadata must be present exactly when 'bm25' appears in retrieved_by."
            )

        if ("dense" in source_names) != dense_rank_present:
            raise ValueError(
                "Dense metadata must be present exactly when 'dense' appears in retrieved_by."
            )

        return self


@dataclass(slots=True)
class _HybridAccumulator:
    """Mutable state while BM25 and dense results are fused."""

    chunk: ChunkRecord
    rrf_score: float = 0.0
    bm25_rank: int | None = None
    bm25_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None


def load_hybrid_config(path: Path) -> HybridConfig:
    """Load and validate hybrid-retrieval YAML configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Hybrid configuration must contain a YAML mapping.")

    return HybridConfig.model_validate(raw_data)


def _same_chunk(first: ChunkRecord, second: ChunkRecord) -> bool:
    """Return whether two chunks contain identical stored provenance."""

    return first.model_dump(mode="json") == second.model_dump(mode="json")


def _validate_source_hit(
    hit: RetrievalHit,
    *,
    source_name: RetrieverName,
) -> None:
    """Validate the minimum assumptions required for RRF."""

    if hit.rank < 1:
        raise ValueError(f"{source_name} returned a rank smaller than 1.")

    if not math.isfinite(hit.score):
        raise ValueError(f"{source_name} returned a non-finite score.")


def _consume_source_hits(
    candidates: dict[str, _HybridAccumulator],
    hits: Sequence[RetrievalHit],
    *,
    source_name: RetrieverName,
    rrf_k: int,
) -> None:
    """Add one retriever's ranked results to the fusion state."""

    seen_chunk_ids: set[str] = set()

    for hit in hits:
        _validate_source_hit(hit, source_name=source_name)

        chunk_id = hit.chunk.chunk_id

        if chunk_id in seen_chunk_ids:
            raise ValueError(f"{source_name} returned duplicate chunk {chunk_id}.")

        seen_chunk_ids.add(chunk_id)
        candidate = candidates.get(chunk_id)

        if candidate is None:
            candidate = _HybridAccumulator(chunk=hit.chunk)
            candidates[chunk_id] = candidate
        elif not _same_chunk(candidate.chunk, hit.chunk):
            raise ValueError(f"Retrievers returned inconsistent metadata for chunk {chunk_id}.")

        candidate.rrf_score += 1.0 / (rrf_k + hit.rank)

        if source_name == "bm25":
            candidate.bm25_rank = hit.rank
            candidate.bm25_score = hit.score
        else:
            candidate.dense_rank = hit.rank
            candidate.dense_score = hit.score


def _best_source_rank(candidate: _HybridAccumulator) -> int:
    """Return the best available source rank."""

    ranks = [rank for rank in (candidate.bm25_rank, candidate.dense_rank) if rank is not None]

    if not ranks:
        raise ValueError("Hybrid candidate has no source rank.")

    return min(ranks)


def _retriever_names(candidate: _HybridAccumulator) -> list[RetrieverName]:
    """Return source labels in deterministic order."""

    names: list[RetrieverName] = []

    if candidate.bm25_rank is not None:
        names.append("bm25")

    if candidate.dense_rank is not None:
        names.append("dense")

    return names


class HybridIndex:
    """Fuse BM25 and dense rankings with reciprocal-rank fusion."""

    def __init__(
        self,
        bm25_index: RetrievalIndex,
        dense_index: RetrievalIndex,
        config: HybridConfig | None = None,
    ) -> None:
        self._bm25_index = bm25_index
        self._dense_index = dense_index
        self._config = config or HybridConfig()

    @property
    def config(self) -> HybridConfig:
        """Return the validated hybrid configuration."""

        return self._config

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[HybridSearchHit]:
        """Return deterministically ranked RRF results."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        bm25_hits = self._bm25_index.search(
            query=query,
            top_k=self._config.bm25_top_k,
        )
        dense_hits = self._dense_index.search(
            query=query,
            top_k=self._config.dense_top_k,
        )

        candidates: dict[str, _HybridAccumulator] = {}

        _consume_source_hits(
            candidates,
            bm25_hits,
            source_name="bm25",
            rrf_k=self._config.rrf_k,
        )
        _consume_source_hits(
            candidates,
            dense_hits,
            source_name="dense",
            rrf_k=self._config.rrf_k,
        )

        ranked_candidates = sorted(
            candidates.values(),
            key=lambda candidate: (
                -candidate.rrf_score,
                _best_source_rank(candidate),
                candidate.chunk.chunk_id,
            ),
        )

        return [
            HybridSearchHit(
                rank=rank,
                score=round(candidate.rrf_score, 12),
                chunk=candidate.chunk,
                retrieved_by=_retriever_names(candidate),
                bm25_rank=candidate.bm25_rank,
                bm25_score=candidate.bm25_score,
                dense_rank=candidate.dense_rank,
                dense_score=candidate.dense_score,
            )
            for rank, candidate in enumerate(
                ranked_candidates[:top_k],
                start=1,
            )
        ]


def write_hybrid_search_results(
    path: Path,
    hits: Sequence[HybridSearchHit],
) -> None:
    """Write hybrid search results as JSON Lines."""

    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(json.dumps(hit.model_dump(mode="json"), sort_keys=True) for hit in hits)

    if content:
        content += "\n"

    path.write_text(content, encoding="utf-8")
