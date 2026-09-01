"""Policies and measurements for retrieval over large chunk collections."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


class RetrievalScaleConfig(BaseModel):
    """Large-corpus controls that keep model context independent of corpus size."""

    model_config = ConfigDict(extra="forbid")

    candidate_top_k: int = Field(default=100, ge=1, le=10_000)
    rerank_top_k: int = Field(default=20, ge=1, le=1_000)
    evidence_top_k: int = Field(default=5, ge=1, le=100)
    max_chunks_per_document: int = Field(default=2, ge=1, le=100)
    collapse_parent_chunks: bool = True
    duplicate_jaccard_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    shingle_words: int = Field(default=5, ge=1, le=20)
    max_context_tokens: int = Field(default=3_000, ge=1)
    max_chunk_tokens: int = Field(default=750, ge=1)

    @model_validator(mode="after")
    def validate_funnel(self) -> "RetrievalScaleConfig":
        if self.rerank_top_k > self.candidate_top_k:
            raise ValueError("rerank_top_k must not exceed candidate_top_k.")
        if self.evidence_top_k > self.rerank_top_k:
            raise ValueError("evidence_top_k must not exceed rerank_top_k.")
        if self.max_chunk_tokens > self.max_context_tokens:
            raise ValueError("max_chunk_tokens must not exceed max_context_tokens.")
        return self


class ChunkFilter(BaseModel):
    """Metadata filters supported by every citation-preserving chunk."""

    model_config = ConfigDict(extra="forbid")

    document_ids: set[int] | None = None
    document_sha256s: set[str] | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    publication_year_min: int | None = Field(default=None, ge=1900, le=2200)
    publication_year_max: int | None = Field(default=None, ge=1900, le=2200)
    subject_categories: set[str] | None = None
    document_types: set[str] | None = None
    programs: set[str] | None = None
    report_families: set[str] | None = None

    @model_validator(mode="after")
    def validate_pages(self) -> "ChunkFilter":
        if (
            self.page_start is not None
            and self.page_end is not None
            and self.page_end < self.page_start
        ):
            raise ValueError("page_end must not be smaller than page_start.")
        if (
            self.publication_year_min is not None
            and self.publication_year_max is not None
            and self.publication_year_max < self.publication_year_min
        ):
            raise ValueError("publication_year_max must not be smaller than publication_year_min.")
        return self


def chunk_matches_filter(chunk: ChunkRecord, filters: ChunkFilter | None) -> bool:
    """Return whether a chunk satisfies all supplied metadata constraints."""

    if filters is None:
        return True
    if filters.document_ids is not None and chunk.document_id not in filters.document_ids:
        return False
    if (
        filters.document_sha256s is not None
        and chunk.document_sha256 not in filters.document_sha256s
    ):
        return False
    if filters.page_start is not None and chunk.page_end < filters.page_start:
        return False
    if filters.page_end is not None and chunk.page_start > filters.page_end:
        return False
    if (
        filters.publication_year_min is not None
        and (chunk.publication_year is None or chunk.publication_year < filters.publication_year_min)
    ):
        return False
    if (
        filters.publication_year_max is not None
        and (chunk.publication_year is None or chunk.publication_year > filters.publication_year_max)
    ):
        return False
    if filters.subject_categories is not None and not (
        {value.casefold() for value in chunk.subject_categories}
        & {value.casefold() for value in filters.subject_categories}
    ):
        return False
    if (
        filters.document_types is not None
        and (chunk.document_type is None or chunk.document_type.casefold() not in {
            value.casefold() for value in filters.document_types
        })
    ):
        return False
    if filters.programs is not None and not (
        {value.casefold() for value in chunk.programs}
        & {value.casefold() for value in filters.programs}
    ):
        return False
    if (
        filters.report_families is not None
        and (chunk.report_family is None or chunk.report_family.casefold() not in {
            value.casefold() for value in filters.report_families
        })
    ):
        return False
    return True


def _word_shingles(text: str, width: int) -> set[str]:
    words = " ".join(text.casefold().split()).split()
    if len(words) < width:
        return {" ".join(words)} if words else set()
    return {" ".join(words[index : index + width]) for index in range(len(words) - width + 1)}


def deduplicate_overlapping_hits(
    hits: Sequence[RerankedSearchHit],
    *,
    threshold: float,
    shingle_words: int = 5,
) -> list[RerankedSearchHit]:
    """Keep the best-ranked hit when passage word shingles substantially overlap."""

    kept: list[RerankedSearchHit] = []
    kept_shingles: list[set[str]] = []
    for hit in hits:
        shingles = _word_shingles(hit.chunk.text, shingle_words)
        duplicate = False
        for existing in kept_shingles:
            union = shingles | existing
            similarity = len(shingles & existing) / len(union) if union else 1.0
            if similarity >= threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(hit)
            kept_shingles.append(shingles)
    return kept


def select_hierarchical_evidence(
    hits: Sequence[RerankedSearchHit],
    config: RetrievalScaleConfig,
    *,
    filters: ChunkFilter | None = None,
) -> list[RerankedSearchHit]:
    """Select diverse child chunks after document-level grouping and deduplication."""

    eligible = [
        hit
        for hit in hits[: config.rerank_top_k]
        if chunk_matches_filter(hit.chunk, filters)
    ]
    parent_collapsed: list[RerankedSearchHit] = []
    seen_parents: set[str] = set()
    for hit in eligible:
        parent_id = hit.chunk.parent_chunk_id or hit.chunk.chunk_id
        if config.collapse_parent_chunks and parent_id in seen_parents:
            continue
        parent_collapsed.append(hit)
        seen_parents.add(parent_id)
    unique = deduplicate_overlapping_hits(
        parent_collapsed,
        threshold=config.duplicate_jaccard_threshold,
        shingle_words=config.shingle_words,
    )
    per_document: defaultdict[int, int] = defaultdict(int)
    selected: list[RerankedSearchHit] = []
    for hit in unique:
        document_id = hit.chunk.document_id
        if per_document[document_id] >= config.max_chunks_per_document:
            continue
        selected.append(hit)
        per_document[document_id] += 1
        if len(selected) >= config.evidence_top_k:
            break
    return selected


def truncate_to_token_budget(
    text: str,
    *,
    token_counter: Callable[[str], int],
    max_tokens: int,
) -> str:
    """Return the longest whitespace-delimited prefix within an actual tokenizer budget."""

    if max_tokens < 1:
        return ""
    if token_counter(text) <= max_tokens:
        return text.strip()
    words = text.split()
    low, high = 0, len(words)
    while low < high:
        midpoint = (low + high + 1) // 2
        if token_counter(" ".join(words[:midpoint])) <= max_tokens:
            low = midpoint
        else:
            high = midpoint - 1
    return " ".join(words[:low]).strip()


class IncrementalIndexPlan(BaseModel):
    """Checksum-derived work needed to synchronize an existing index."""

    model_config = ConfigDict(extra="forbid")

    unchanged_document_ids: list[int]
    upsert_document_ids: list[int]
    delete_document_ids: list[int]


def plan_incremental_index_update(
    existing: Mapping[int, str],
    incoming: Mapping[int, str],
) -> IncrementalIndexPlan:
    """Avoid re-embedding documents whose authoritative PDF checksum is unchanged."""

    unchanged = sorted(key for key, value in incoming.items() if existing.get(key) == value)
    upsert = sorted(key for key, value in incoming.items() if existing.get(key) != value)
    deleted = sorted(set(existing) - set(incoming))
    return IncrementalIndexPlan(
        unchanged_document_ids=unchanged,
        upsert_document_ids=upsert,
        delete_document_ids=deleted,
    )


class ScaleQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    relevant_chunk_ids: set[str] = Field(min_length=1)


class ScaleMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corpus_chunks: int = Field(ge=1)
    query_count: int = Field(ge=1)
    recall_at_k: float = Field(ge=0.0, le=1.0)
    ndcg_at_k: float = Field(ge=0.0, le=1.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)


class ScaleSnapshotManifest(BaseModel):
    """Reproducible logical corpus snapshot without copying source evidence."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"
    target_chunk_count: int = Field(ge=1)
    authoritative_chunk_count: int = Field(ge=1)
    synthetic_distractor_count: int = Field(ge=0)
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    strategy: str = "deterministic_id_salted_replication"
    seed: int = Field(default=1729, ge=0)
    relevance_policy: str = "authoritative_chunks_only"


def build_scale_snapshot_manifest(
    *,
    source_path: Path,
    authoritative_chunk_count: int,
    target_chunk_count: int,
    seed: int = 1729,
) -> ScaleSnapshotManifest:
    """Describe a deterministic scale snapshot while preserving evidence identity."""

    if authoritative_chunk_count < 1:
        raise ValueError("authoritative_chunk_count must be positive.")
    if target_chunk_count < authoritative_chunk_count:
        raise ValueError("target_chunk_count must include every authoritative chunk.")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return ScaleSnapshotManifest(
        target_chunk_count=target_chunk_count,
        authoritative_chunk_count=authoritative_chunk_count,
        synthetic_distractor_count=target_chunk_count - authoritative_chunk_count,
        source_path=str(source_path),
        source_sha256=digest,
        seed=seed,
    )


def iter_scale_snapshot_chunks(
    chunks: Sequence[ChunkRecord],
    manifest: ScaleSnapshotManifest,
) -> Sequence[ChunkRecord]:
    """Materialize deterministic distractors with non-authoritative synthetic IDs."""

    if len(chunks) != manifest.authoritative_chunk_count:
        raise ValueError("Chunk count does not match the scale snapshot manifest.")
    expanded = list(chunks)
    for index in range(manifest.synthetic_distractor_count):
        source = chunks[(index + manifest.seed) % len(chunks)]
        replica_number = index + 1
        expanded.append(
            source.model_copy(
                update={
                    "chunk_id": f"synthetic:{replica_number:09d}:{source.chunk_id}",
                    "document_id": -(replica_number),
                    "citation_url": "synthetic://scale-distractor",
                    "source_url": "synthetic://scale-distractor",
                    "document_sha256": hashlib.sha256(
                        f"{manifest.seed}:{replica_number}:{source.chunk_id}".encode()
                    ).hexdigest(),
                }
            )
        )
    return expanded


def benchmark_retriever(
    *,
    corpus_chunks: int,
    queries: Sequence[ScaleQuery],
    search: Callable[[str, int], Sequence[str]],
    top_k: int = 10,
) -> ScaleMeasurement:
    """Measure quality and latency using frozen relevance labels at one corpus size."""

    recalls: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []
    for query in queries:
        started = time.perf_counter()
        returned = list(search(query.text, top_k))[:top_k]
        latencies.append((time.perf_counter() - started) * 1_000.0)
        relevant = query.relevant_chunk_ids
        recalls.append(len(set(returned) & relevant) / len(relevant))
        gain = sum(
            1.0 / math.log2(rank + 1)
            for rank, item in enumerate(returned, 1)
            if item in relevant
        )
        ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(relevant), top_k) + 1))
        ndcgs.append(gain / ideal if ideal else 0.0)
    ordered = sorted(latencies)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ScaleMeasurement(
        corpus_chunks=corpus_chunks,
        query_count=len(queries),
        recall_at_k=statistics.fmean(recalls),
        ndcg_at_k=statistics.fmean(ndcgs),
        p50_latency_ms=statistics.median(ordered),
        p95_latency_ms=ordered[p95_index],
    )


def write_scale_report(path: Path, measurements: Sequence[ScaleMeasurement]) -> None:
    """Write deterministic JSON containing benchmark results and a checksum."""

    rows = [item.model_dump(mode="json") for item in measurements]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    payload = {"measurements": rows, "sha256": hashlib.sha256(canonical.encode()).hexdigest()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
