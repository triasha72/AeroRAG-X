"""Models and utilities for pooled retrieval annotation."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.evaluation.retrieval import EvaluationQuery, RelevanceJudgment
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.bm25 import SearchHit
from aeroragx.retrieval.dense import DenseSearchHit

RetrieverName = Literal[
    "bm25",
    "dense",
    "v0.1-qrels",
]


class BM25SearchIndex(Protocol):
    """Search interface required from the BM25 index."""

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> Sequence[SearchHit]:
        """Return ranked BM25 hits."""


class DenseSearchIndex(Protocol):
    """Search interface required from the dense index."""

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> Sequence[DenseSearchHit]:
        """Return ranked dense hits."""


def stable_candidate_key(
    seed: int,
    query_id: str,
    chunk_id: str,
) -> str:
    """Return a deterministic blinded-order key."""

    normalized_query_id = query_id.strip()
    normalized_chunk_id = chunk_id.strip()

    if not normalized_query_id:
        raise ValueError("query_id must not be empty.")

    if not normalized_chunk_id:
        raise ValueError("chunk_id must not be empty.")

    value = f"{seed}:{normalized_query_id}:{normalized_chunk_id}"

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def order_chunk_ids_for_annotation(
    chunk_ids: Sequence[str],
    *,
    seed: int,
    query_id: str,
) -> list[str]:
    """Return chunk IDs in reproducible blinded order."""

    normalized_chunk_ids = [chunk_id.strip() for chunk_id in chunk_ids]

    if any(not chunk_id for chunk_id in normalized_chunk_ids):
        raise ValueError("chunk_ids must not contain empty values.")

    if len(normalized_chunk_ids) != len(set(normalized_chunk_ids)):
        raise ValueError("chunk_ids must be unique before ordering.")

    return sorted(
        normalized_chunk_ids,
        key=lambda chunk_id: (
            stable_candidate_key(
                seed=seed,
                query_id=query_id,
                chunk_id=chunk_id,
            ),
            chunk_id,
        ),
    )


class _CandidateCore(BaseModel):
    """Fields shared by internal and blinded candidates."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    candidate_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_id: int
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    text_preview: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    source_url: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_page_range(self) -> Self:
        """Ensure the ending page is not before the first page."""

        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start.")

        return self


class InternalPooledCandidate(_CandidateCore):
    """Candidate retaining retriever provenance and ranks."""

    retrieved_by: list[RetrieverName] = Field(min_length=1)
    bm25_rank: int | None = Field(default=None, ge=1)
    bm25_score: float | None = Field(default=None, ge=0.0)
    dense_rank: int | None = Field(default=None, ge=1)
    dense_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_retriever_metadata(self) -> Self:
        """Ensure retriever labels match rank and score metadata."""

        if len(self.retrieved_by) != len(set(self.retrieved_by)):
            raise ValueError("retrieved_by must not contain duplicates.")

        bm25_rank_present = self.bm25_rank is not None
        bm25_score_present = self.bm25_score is not None

        if bm25_rank_present != bm25_score_present:
            raise ValueError(
                "bm25_rank and bm25_score must either both be provided or both be absent."
            )

        dense_rank_present = self.dense_rank is not None
        dense_score_present = self.dense_score is not None

        if dense_rank_present != dense_score_present:
            raise ValueError(
                "dense_rank and dense_score must either both be provided or both be absent."
            )

        retrieved_by = set(self.retrieved_by)

        if ("bm25" in retrieved_by) != bm25_rank_present:
            raise ValueError(
                "BM25 metadata must be present exactly when 'bm25' appears in retrieved_by."
            )

        if ("dense" in retrieved_by) != dense_rank_present:
            raise ValueError(
                "Dense metadata must be present exactly when 'dense' appears in retrieved_by."
            )

        return self


class AnnotationCandidate(_CandidateCore):
    """Candidate shown during blinded relevance annotation."""

    relevant: bool | None = None


class InternalQueryPool(BaseModel):
    """Internal pooled candidates for one query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    candidates: list[InternalPooledCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_candidates(self) -> Self:
        """Reject duplicate candidate and chunk identifiers."""

        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate_id values must be unique within each query.")

        chunk_ids = [candidate.chunk_id for candidate in self.candidates]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_id values must be unique within each query.")

        return self


class AnnotationQueryPool(BaseModel):
    """Blinded annotation candidates for one query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    candidates: list[AnnotationCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_candidates(self) -> Self:
        """Reject duplicate candidate and chunk identifiers."""

        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate_id values must be unique within each query.")

        chunk_ids = [candidate.chunk_id for candidate in self.candidates]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_id values must be unique within each query.")

        return self


@dataclass(slots=True)
class _CandidateAccumulator:
    """Mutable candidate state while result lists are combined."""

    chunk: ChunkRecord
    bm25_rank: int | None = None
    bm25_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None
    carried_forward: bool = False


def _build_chunk_map(chunks: Sequence[ChunkRecord]) -> dict[str, ChunkRecord]:
    """Build a unique chunk lookup table."""

    if not chunks:
        raise ValueError("At least one corpus chunk is required.")

    chunk_by_id: dict[str, ChunkRecord] = {}

    for chunk in chunks:
        if chunk.chunk_id in chunk_by_id:
            raise ValueError(f"Duplicate corpus chunk ID: {chunk.chunk_id}")
        chunk_by_id[chunk.chunk_id] = chunk

    return chunk_by_id


def _normalized_preview(
    text: str,
    *,
    max_characters: int,
) -> str:
    """Create a compact single-line evidence preview."""

    if max_characters < 1:
        raise ValueError("max_characters must be at least 1.")

    normalized = " ".join(text.split())

    if not normalized:
        raise ValueError("Candidate chunk text must not be empty.")

    return normalized[:max_characters].rstrip()


def _accumulator_for_chunk(
    candidates: dict[str, _CandidateAccumulator],
    chunk_by_id: Mapping[str, ChunkRecord],
    chunk_id: str,
) -> _CandidateAccumulator:
    """Return or create the accumulator for one chunk."""

    chunk = chunk_by_id.get(chunk_id)

    if chunk is None:
        raise ValueError(f"Candidate chunk is missing from the corpus: {chunk_id}")

    candidate = candidates.get(chunk_id)

    if candidate is None:
        candidate = _CandidateAccumulator(chunk=chunk)
        candidates[chunk_id] = candidate

    return candidate


def _retriever_names(candidate: _CandidateAccumulator) -> list[RetrieverName]:
    """Return retriever labels in a fixed order."""

    retrievers: list[RetrieverName] = []

    if candidate.bm25_rank is not None:
        retrievers.append("bm25")

    if candidate.dense_rank is not None:
        retrievers.append("dense")

    if candidate.carried_forward:
        retrievers.append("v0.1-qrels")

    return retrievers


def build_query_candidate_pool(
    query: EvaluationQuery,
    bm25_hits: Sequence[SearchHit],
    dense_hits: Sequence[DenseSearchHit],
    previous_judgment: RelevanceJudgment | None,
    chunk_by_id: Mapping[str, ChunkRecord],
    *,
    shuffle_seed: int = 42,
    preview_characters: int = 700,
) -> tuple[InternalQueryPool, AnnotationQueryPool]:
    """Build internal and blinded pools for one query."""

    if previous_judgment is not None and previous_judgment.query_id != query.query_id:
        raise ValueError("Previous judgment query ID does not match the evaluation query.")

    candidates: dict[str, _CandidateAccumulator] = {}
    seen_bm25: set[str] = set()

    for bm25_hit in bm25_hits:
        chunk_id = bm25_hit.chunk.chunk_id

        if chunk_id in seen_bm25:
            raise ValueError(f"BM25 returned a duplicated chunk: {chunk_id}")

        seen_bm25.add(chunk_id)
        candidate = _accumulator_for_chunk(candidates, chunk_by_id, chunk_id)
        candidate.bm25_rank = bm25_hit.rank
        candidate.bm25_score = bm25_hit.score

    seen_dense: set[str] = set()

    for dense_hit in dense_hits:
        chunk_id = dense_hit.chunk.chunk_id

        if chunk_id in seen_dense:
            raise ValueError(f"Dense retrieval returned a duplicated chunk: {chunk_id}")

        seen_dense.add(chunk_id)
        candidate = _accumulator_for_chunk(candidates, chunk_by_id, chunk_id)
        candidate.dense_rank = dense_hit.rank
        candidate.dense_score = dense_hit.score

    if previous_judgment is not None:
        for chunk_id in previous_judgment.relevant_chunk_ids:
            candidate = _accumulator_for_chunk(candidates, chunk_by_id, chunk_id)
            candidate.carried_forward = True

    if not candidates:
        raise ValueError(f"No pooled candidates were found for query {query.query_id}.")

    ordered_chunk_ids = order_chunk_ids_for_annotation(
        list(candidates),
        seed=shuffle_seed,
        query_id=query.query_id,
    )

    internal_candidates: list[InternalPooledCandidate] = []
    annotation_candidates: list[AnnotationCandidate] = []

    for position, chunk_id in enumerate(ordered_chunk_ids, start=1):
        candidate = candidates[chunk_id]
        chunk = candidate.chunk
        candidate_id = f"{query.query_id}:c{position:03d}"
        text_preview = _normalized_preview(
            chunk.text,
            max_characters=preview_characters,
        )

        internal_candidates.append(
            InternalPooledCandidate(
                candidate_id=candidate_id,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text_preview=text_preview,
                citation_url=chunk.citation_url,
                source_url=chunk.source_url,
                retrieved_by=_retriever_names(candidate),
                bm25_rank=candidate.bm25_rank,
                bm25_score=candidate.bm25_score,
                dense_rank=candidate.dense_rank,
                dense_score=candidate.dense_score,
            )
        )

        annotation_candidates.append(
            AnnotationCandidate(
                candidate_id=candidate_id,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text_preview=text_preview,
                citation_url=chunk.citation_url,
                source_url=chunk.source_url,
                relevant=None,
            )
        )

    return (
        InternalQueryPool(
            query_id=query.query_id,
            query=query.query,
            candidates=internal_candidates,
        ),
        AnnotationQueryPool(
            query_id=query.query_id,
            query=query.query,
            candidates=annotation_candidates,
        ),
    )


def build_pooled_candidate_records(
    queries: Sequence[EvaluationQuery],
    previous_judgments: Sequence[RelevanceJudgment],
    chunks: Sequence[ChunkRecord],
    bm25_index: BM25SearchIndex,
    dense_index: DenseSearchIndex,
    *,
    top_k_per_retriever: int = 20,
    shuffle_seed: int = 42,
    preview_characters: int = 700,
) -> tuple[list[InternalQueryPool], list[AnnotationQueryPool]]:
    """Build pooled records for all evaluation queries."""

    if top_k_per_retriever < 1:
        raise ValueError("top_k_per_retriever must be at least 1.")

    if not queries:
        raise ValueError("At least one evaluation query is required.")

    query_ids = [query.query_id for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Evaluation query IDs must be unique.")

    judgment_by_query: dict[str, RelevanceJudgment] = {}

    for judgment in previous_judgments:
        if judgment.query_id in judgment_by_query:
            raise ValueError("Previous relevance judgment IDs must be unique.")
        judgment_by_query[judgment.query_id] = judgment

    query_id_set = set(query_ids)
    judgment_id_set = set(judgment_by_query)
    missing_judgments = query_id_set - judgment_id_set
    unknown_judgments = judgment_id_set - query_id_set

    if missing_judgments:
        raise ValueError("Missing previous judgments for: " + ", ".join(sorted(missing_judgments)))

    if unknown_judgments:
        raise ValueError(
            "Previous judgments contain unknown queries: " + ", ".join(sorted(unknown_judgments))
        )

    chunk_by_id = _build_chunk_map(chunks)
    internal_records: list[InternalQueryPool] = []
    annotation_records: list[AnnotationQueryPool] = []

    for query in queries:
        bm25_hits = bm25_index.search(
            query=query.query,
            top_k=top_k_per_retriever,
        )
        dense_hits = dense_index.search(
            query=query.query,
            top_k=top_k_per_retriever,
        )

        internal, annotation = build_query_candidate_pool(
            query=query,
            bm25_hits=bm25_hits,
            dense_hits=dense_hits,
            previous_judgment=judgment_by_query[query.query_id],
            chunk_by_id=chunk_by_id,
            shuffle_seed=shuffle_seed,
            preview_characters=preview_characters,
        )

        internal_records.append(internal)
        annotation_records.append(annotation)

    return internal_records, annotation_records


def _write_model_records(
    path: Path,
    records: Sequence[BaseModel],
) -> None:
    """Write Pydantic records as deterministic JSONL."""

    if not records:
        raise ValueError("At least one record is required.")

    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(
        json.dumps(record.model_dump(mode="json"), sort_keys=True) for record in records
    )

    path.write_text(content + "\n", encoding="utf-8")


def write_internal_candidate_records(
    path: Path,
    records: Sequence[InternalQueryPool],
) -> None:
    """Write internal pooled candidates."""

    _write_model_records(path, records)


def write_annotation_candidate_records(
    path: Path,
    records: Sequence[AnnotationQueryPool],
) -> None:
    """Write blinded annotation candidates."""

    _write_model_records(path, records)


def load_annotation_records(path: Path) -> list[AnnotationQueryPool]:
    """Load blinded annotation records from JSONL."""

    records: list[AnnotationQueryPool] = []
    seen_query_ids: set[str] = set()

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()

        if not stripped:
            continue

        try:
            record = AnnotationQueryPool.model_validate_json(stripped)
        except ValueError as exc:
            raise ValueError(f"Invalid annotation row {line_number}: {exc}") from exc

        if record.query_id in seen_query_ids:
            raise ValueError(f"Duplicate annotation query ID: {record.query_id}")

        seen_query_ids.add(record.query_id)
        records.append(record)

    if not records:
        raise ValueError("Annotation file contains no records.")

    return records


def build_qrels_from_annotations(
    records: Sequence[AnnotationQueryPool],
) -> list[RelevanceJudgment]:
    """Convert completed annotations to qrels."""

    if not records:
        raise ValueError("At least one annotation record is required.")

    judgments: list[RelevanceJudgment] = []
    seen_query_ids: set[str] = set()

    for record in records:
        if record.query_id in seen_query_ids:
            raise ValueError(f"Duplicate annotation query ID: {record.query_id}")

        seen_query_ids.add(record.query_id)

        incomplete = [
            candidate.candidate_id for candidate in record.candidates if candidate.relevant is None
        ]

        if incomplete:
            raise ValueError(
                f"Incomplete relevance labels for {record.query_id}: " + ", ".join(incomplete)
            )

        relevant_chunk_ids = sorted(
            candidate.chunk_id for candidate in record.candidates if candidate.relevant is True
        )

        if not relevant_chunk_ids:
            raise ValueError(
                f"Every query must have at least one relevant candidate: {record.query_id}"
            )

        judgments.append(
            RelevanceJudgment(
                query_id=record.query_id,
                relevant_chunk_ids=relevant_chunk_ids,
            )
        )

    return judgments


def write_relevance_judgments(
    path: Path,
    judgments: Sequence[RelevanceJudgment],
) -> None:
    """Write relevance judgments as JSONL."""

    _write_model_records(path, judgments)
