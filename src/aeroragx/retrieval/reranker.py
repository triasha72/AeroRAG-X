"""Cross-encoder reranking over Hybrid RRF candidates."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol, Self

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.observability.tracing import trace_span
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.hybrid import (
    HybridIndex,
    HybridSearchHit,
    HybridSearchTimings,
    RetrieverName,
)


class RerankerConfig(BaseModel):
    """Configuration for cross-encoder reranking."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    model_name: str = Field(min_length=1)
    candidate_top_k: int = Field(default=20, ge=1, le=100)
    default_top_k: int = Field(default=10, ge=1, le=100)
    batch_size: int = Field(default=16, ge=1, le=512)
    max_length: int | None = Field(default=None, ge=1)
    device: str = Field(default="cpu", min_length=1)
    show_progress_bar: bool = False

    @model_validator(mode="after")
    def validate_result_depths(self) -> Self:
        """Ensure the returned depth does not exceed the candidate depth."""

        if self.default_top_k > self.candidate_top_k:
            raise ValueError("default_top_k must not exceed candidate_top_k.")

        return self


class RerankerScorer(Protocol):
    """Scoring interface used by the reranker and deterministic tests."""

    def score(
        self,
        query: str,
        documents: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[float]:
        """Return one finite score for each query-document pair."""

        ...


class HybridCandidateIndex(Protocol):
    """Search interface required from the Hybrid RRF stage."""

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> Sequence[HybridSearchHit]:
        """Return ranked Hybrid RRF candidates."""

        ...


class CrossEncoderScorer:
    """Sentence Transformers CrossEncoder scoring adapter."""

    def __init__(self, config: RerankerConfig) -> None:
        from sentence_transformers import CrossEncoder

        model_kwargs: dict[str, object] = {
            "device": config.device,
            "trust_remote_code": False,
        }

        if config.max_length is not None:
            model_kwargs["max_length"] = config.max_length

        self._model: Any = CrossEncoder(
            config.model_name,
            **model_kwargs,
        )

    def score(
        self,
        query: str,
        documents: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        """Score query-document pairs using raw model outputs."""

        if not documents:
            return []

        pairs = [(query, document) for document in documents]

        raw_scores = self._model.predict(
            pairs,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
            convert_to_tensor=False,
        )

        values = np.asarray(
            raw_scores,
            dtype=np.float64,
        ).reshape(-1)

        return [float(value) for value in values]


class RerankedSearchHit(BaseModel):
    """One final result with reranker and source-stage provenance."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    score: float
    chunk: ChunkRecord

    hybrid_rank: int = Field(ge=1)
    hybrid_score: float = Field(gt=0.0)
    retrieved_by: list[RetrieverName] = Field(min_length=1)

    bm25_rank: int | None = Field(default=None, ge=1)
    bm25_score: float | None = Field(default=None, ge=0.0)

    dense_rank: int | None = Field(default=None, ge=1)
    dense_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_scores_and_sources(self) -> Self:
        """Reject non-finite scores and inconsistent source metadata."""

        if not math.isfinite(self.score):
            raise ValueError("score must be finite.")

        if not math.isfinite(self.hybrid_score):
            raise ValueError("hybrid_score must be finite.")

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


class RerankerLatencyReport(BaseModel):
    """Measured cross-encoder scoring latency."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    device: str
    candidate_top_k: int = Field(ge=1)
    batch_size: int = Field(ge=1)
    query_count: int = Field(ge=0)
    pair_count: int = Field(ge=0)
    total_seconds: float = Field(ge=0.0)
    milliseconds_per_pair: float = Field(ge=0.0)
    hardware_note: str | None = None


@dataclass(frozen=True, slots=True)
class _ScoredHybridCandidate:
    """Internal cross-encoder score aligned to one hybrid result."""

    hybrid_hit: HybridSearchHit
    cross_encoder_score: float


class RerankerSearchTimings(BaseModel):
    """Internal timing snapshot for one reranked search."""

    model_config = ConfigDict(extra="forbid")

    candidate_retrieval_ms: float = Field(ge=0.0)
    reranker_scoring_ms: float = Field(ge=0.0)
    ranking_ms: float = Field(ge=0.0)
    total_ms: float = Field(ge=0.0)
    pair_count: int = Field(ge=0)
    hybrid: HybridSearchTimings | None = None


class RerankerIndex:
    """Rerank a bounded Hybrid RRF candidate set with a cross-encoder."""

    def __init__(
        self,
        hybrid_index: HybridCandidateIndex,
        scorer: RerankerScorer,
        config: RerankerConfig,
    ) -> None:
        self._hybrid_index = hybrid_index
        self._scorer = scorer
        self._config = config
        self._query_count = 0
        self._pair_count = 0
        self._scoring_seconds = 0.0
        self._last_pair_count = 0
        self._last_scoring_seconds = 0.0
        self._last_search_timings: RerankerSearchTimings | None = None

    @property
    def config(self) -> RerankerConfig:
        """Return the validated reranker configuration."""

        return self._config

    @property
    def last_pair_count(self) -> int:
        """Return the number of pairs in the latest scoring call."""

        return self._last_pair_count

    @property
    def last_scoring_seconds(self) -> float:
        """Return scoring-only latency for the latest query."""

        return self._last_scoring_seconds

    @property
    def last_search_timings(self) -> RerankerSearchTimings | None:
        """Return a defensive copy of the latest reranked-search timings."""

        if self._last_search_timings is None:
            return None

        return self._last_search_timings.model_copy(deep=True)

    def reset_timing(self) -> None:
        """Reset accumulated cross-encoder scoring measurements."""

        self._query_count = 0
        self._pair_count = 0
        self._scoring_seconds = 0.0
        self._last_pair_count = 0
        self._last_scoring_seconds = 0.0
        self._last_search_timings = None

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RerankedSearchHit]:
        """Return cross-encoder-ranked Hybrid RRF candidates with timing."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        if top_k > self._config.candidate_top_k:
            raise ValueError("top_k must not exceed candidate_top_k.")

        with trace_span(
            "aeroragx.reranker",
        ) as reranker_span:
            if reranker_span is not None:
                reranker_span.set_attribute(
                    "aeroragx.model",
                    self._config.model_name,
                )
                reranker_span.set_attribute(
                    "aeroragx.requested_top_k",
                    top_k,
                )
                reranker_span.set_attribute(
                    "aeroragx.candidate_top_k",
                    self._config.candidate_top_k,
                )
                reranker_span.set_attribute(
                    "aeroragx.batch_size",
                    self._config.batch_size,
                )

            self._last_search_timings = None
            total_started_at = perf_counter()

            candidate_started_at = perf_counter()
            hybrid_hits = list(
                self._hybrid_index.search(
                    query=query,
                    top_k=self._config.candidate_top_k,
                )
            )
            candidate_retrieval_ms = round(
                (perf_counter() - candidate_started_at) * 1000.0,
                3,
            )

            hybrid_timings = (
                self._hybrid_index.last_timings
                if isinstance(
                    self._hybrid_index,
                    HybridIndex,
                )
                else None
            )

            chunk_ids = [hit.chunk.chunk_id for hit in hybrid_hits]

            if len(chunk_ids) != len(set(chunk_ids)):
                raise ValueError("Hybrid retrieval returned duplicate chunk IDs.")

            documents = [hit.chunk.text for hit in hybrid_hits]

            scoring_started_at = perf_counter()
            raw_scores = self._scorer.score(
                query,
                documents,
                batch_size=self._config.batch_size,
                show_progress_bar=(self._config.show_progress_bar),
            )
            elapsed_seconds = perf_counter() - scoring_started_at
            reranker_scoring_ms = round(
                elapsed_seconds * 1000.0,
                3,
            )

            scores = [float(score) for score in raw_scores]

            if len(scores) != len(hybrid_hits):
                raise ValueError(
                    "Reranker scorer returned a different number of scores than candidates."
                )

            for score in scores:
                if not math.isfinite(score):
                    raise ValueError("Reranker scorer returned a non-finite score.")

            pair_count = len(hybrid_hits)
            self._query_count += 1
            self._pair_count += pair_count
            self._scoring_seconds += elapsed_seconds
            self._last_pair_count = pair_count
            self._last_scoring_seconds = elapsed_seconds

            ranking_started_at = perf_counter()

            scored_candidates = [
                _ScoredHybridCandidate(
                    hybrid_hit=hybrid_hit,
                    cross_encoder_score=score,
                )
                for hybrid_hit, score in zip(
                    hybrid_hits,
                    scores,
                    strict=True,
                )
            ]

            ranked_candidates = sorted(
                scored_candidates,
                key=lambda candidate: (
                    -candidate.cross_encoder_score,
                    candidate.hybrid_hit.rank,
                    candidate.hybrid_hit.chunk.chunk_id,
                ),
            )

            results = [
                RerankedSearchHit(
                    rank=rank,
                    score=candidate.cross_encoder_score,
                    chunk=candidate.hybrid_hit.chunk,
                    hybrid_rank=candidate.hybrid_hit.rank,
                    hybrid_score=candidate.hybrid_hit.score,
                    retrieved_by=candidate.hybrid_hit.retrieved_by,
                    bm25_rank=candidate.hybrid_hit.bm25_rank,
                    bm25_score=candidate.hybrid_hit.bm25_score,
                    dense_rank=candidate.hybrid_hit.dense_rank,
                    dense_score=candidate.hybrid_hit.dense_score,
                )
                for rank, candidate in enumerate(
                    ranked_candidates[:top_k],
                    start=1,
                )
            ]

            ranking_ms = round(
                (perf_counter() - ranking_started_at) * 1000.0,
                3,
            )
            total_ms = round(
                (perf_counter() - total_started_at) * 1000.0,
                3,
            )

            if reranker_span is not None:
                reranker_span.set_attribute(
                    "aeroragx.pair_count",
                    pair_count,
                )
                reranker_span.set_attribute(
                    "aeroragx.result_count",
                    len(results),
                )

            self._last_search_timings = RerankerSearchTimings(
                candidate_retrieval_ms=candidate_retrieval_ms,
                reranker_scoring_ms=reranker_scoring_ms,
                ranking_ms=ranking_ms,
                total_ms=total_ms,
                pair_count=pair_count,
                hybrid=hybrid_timings,
            )

            return results

    def build_latency_report(
        self,
        *,
        hardware_note: str | None = None,
    ) -> RerankerLatencyReport:
        """Build a report from accumulated scoring-only timings."""

        milliseconds_per_pair = 0.0

        if self._pair_count:
            milliseconds_per_pair = self._scoring_seconds * 1000.0 / self._pair_count

        return RerankerLatencyReport(
            model_name=self._config.model_name,
            device=self._config.device,
            candidate_top_k=(self._config.candidate_top_k),
            batch_size=self._config.batch_size,
            query_count=self._query_count,
            pair_count=self._pair_count,
            total_seconds=round(
                self._scoring_seconds,
                6,
            ),
            milliseconds_per_pair=round(
                milliseconds_per_pair,
                6,
            ),
            hardware_note=hardware_note,
        )


def load_reranker_config(
    path: Path,
) -> RerankerConfig:
    """Load and validate reranker YAML configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Reranker configuration must contain a YAML mapping.")

    return RerankerConfig.model_validate(raw_data)


def with_candidate_top_k(
    config: RerankerConfig,
    candidate_top_k: int | None,
) -> RerankerConfig:
    """Return a validated config with an optional candidate-depth override."""

    if candidate_top_k is None:
        return config

    values = config.model_dump(mode="python")
    values["candidate_top_k"] = candidate_top_k

    return RerankerConfig.model_validate(values)


def load_cross_encoder_scorer(
    config: RerankerConfig,
) -> CrossEncoderScorer:
    """Load the configured Sentence Transformers cross-encoder."""

    return CrossEncoderScorer(config)


def write_reranked_search_results(
    path: Path,
    hits: Sequence[RerankedSearchHit],
) -> None:
    """Write reranked search results as JSON Lines."""

    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(
        json.dumps(
            hit.model_dump(mode="json"),
            sort_keys=True,
        )
        for hit in hits
    )

    if content:
        content += "\n"

    path.write_text(content, encoding="utf-8")


def write_reranker_latency_report(
    path: Path,
    report: RerankerLatencyReport,
) -> None:
    """Write a formatted reranker latency report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
