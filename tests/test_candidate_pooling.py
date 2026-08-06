"""Tests for pooled retrieval candidate models and utilities."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from aeroragx.evaluation.pooling import (
    AnnotationCandidate,
    AnnotationQueryPool,
    InternalPooledCandidate,
    InternalQueryPool,
    build_pooled_candidate_records,
    build_qrels_from_annotations,
    build_query_candidate_pool,
    load_annotation_records,
    order_chunk_ids_for_annotation,
    stable_candidate_key,
    write_annotation_candidate_records,
    write_internal_candidate_records,
    write_relevance_judgments,
)
from aeroragx.evaluation.retrieval import EvaluationQuery, RelevanceJudgment
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.bm25 import SearchHit
from aeroragx.retrieval.dense import DenseSearchHit


def make_chunk(
    chunk_id: str = "101:chunk:00000",
    document_id: int = 101,
    text: str = "Aircraft battery thermal runaway and cooling evidence.",
) -> ChunkRecord:
    """Create a valid retrieval chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=1,
        page_end=2,
        page_ids=[
            f"{document_id}:page:1",
            f"{document_id}:page:2",
        ],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url=f"https://ntrs.nasa.gov/citations/{document_id}",
        source_url=f"https://example.com/{document_id}.pdf",
        document_sha256="a" * 64,
    )


def make_internal_candidate(
    *,
    candidate_id: str = "q001:c001",
    chunk_id: str = "101:chunk:00000",
) -> InternalPooledCandidate:
    """Create a valid internal candidate."""

    return InternalPooledCandidate(
        candidate_id=candidate_id,
        chunk_id=chunk_id,
        document_id=101,
        page_start=1,
        page_end=2,
        text_preview="Battery thermal runaway and aircraft cooling evidence.",
        citation_url="https://ntrs.nasa.gov/citations/101",
        source_url="https://example.com/101.pdf",
        retrieved_by=["bm25", "dense", "v0.1-qrels"],
        bm25_rank=2,
        bm25_score=12.5,
        dense_rank=1,
        dense_score=0.82,
    )


def make_annotation_candidate(
    *,
    candidate_id: str = "q001:c001",
    chunk_id: str = "101:chunk:00000",
    relevant: bool | None = None,
) -> AnnotationCandidate:
    """Create a valid blinded annotation candidate."""

    return AnnotationCandidate(
        candidate_id=candidate_id,
        chunk_id=chunk_id,
        document_id=101,
        page_start=1,
        page_end=2,
        text_preview="Battery thermal runaway and aircraft cooling evidence.",
        citation_url="https://ntrs.nasa.gov/citations/101",
        source_url="https://example.com/101.pdf",
        relevant=relevant,
    )


class FakeBM25Index:
    """Deterministic BM25 test double."""

    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    def search(self, query: str, top_k: int = 10) -> list[SearchHit]:
        del query
        return self._hits[:top_k]


class FakeDenseIndex:
    """Deterministic dense-retrieval test double."""

    def __init__(self, hits: list[DenseSearchHit]) -> None:
        self._hits = hits

    def search(self, query: str, top_k: int = 10) -> list[DenseSearchHit]:
        del query
        return self._hits[:top_k]


def test_internal_candidate_accepts_both_retrievers() -> None:
    candidate = make_internal_candidate()
    assert candidate.retrieved_by == ["bm25", "dense", "v0.1-qrels"]
    assert candidate.bm25_rank == 2
    assert candidate.dense_rank == 1


def test_qrel_only_candidate_requires_no_scores() -> None:
    candidate = InternalPooledCandidate(
        candidate_id="q001:c001",
        chunk_id="101:chunk:00000",
        document_id=101,
        page_start=1,
        page_end=1,
        text_preview="Previously judged relevant evidence.",
        citation_url="https://ntrs.nasa.gov/citations/101",
        source_url="https://example.com/101.pdf",
        retrieved_by=["v0.1-qrels"],
    )
    assert candidate.bm25_rank is None
    assert candidate.dense_rank is None


def test_internal_candidate_rejects_duplicate_retrievers() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        InternalPooledCandidate(
            candidate_id="q001:c001",
            chunk_id="101:chunk:00000",
            document_id=101,
            page_start=1,
            page_end=1,
            text_preview="Relevant evidence.",
            citation_url="https://ntrs.nasa.gov/citations/101",
            source_url="https://example.com/101.pdf",
            retrieved_by=["bm25", "bm25"],
            bm25_rank=1,
            bm25_score=10.0,
        )


def test_internal_candidate_requires_matching_bm25_metadata() -> None:
    with pytest.raises(ValidationError, match="bm25_rank and bm25_score"):
        InternalPooledCandidate(
            candidate_id="q001:c001",
            chunk_id="101:chunk:00000",
            document_id=101,
            page_start=1,
            page_end=1,
            text_preview="Relevant evidence.",
            citation_url="https://ntrs.nasa.gov/citations/101",
            source_url="https://example.com/101.pdf",
            retrieved_by=["bm25"],
            bm25_rank=1,
        )


def test_candidate_rejects_invalid_page_range() -> None:
    with pytest.raises(ValidationError, match="page_end"):
        AnnotationCandidate(
            candidate_id="q001:c001",
            chunk_id="101:chunk:00000",
            document_id=101,
            page_start=3,
            page_end=2,
            text_preview="Relevant evidence.",
            citation_url="https://ntrs.nasa.gov/citations/101",
            source_url="https://example.com/101.pdf",
        )


def test_annotation_candidate_is_blinded() -> None:
    dumped = make_annotation_candidate().model_dump()
    assert "retrieved_by" not in dumped
    assert "bm25_rank" not in dumped
    assert "dense_rank" not in dumped


def test_stable_candidate_key_is_deterministic() -> None:
    first = stable_candidate_key(42, "q001", "101:chunk:00000")
    second = stable_candidate_key(42, "q001", "101:chunk:00000")
    assert first == second
    assert len(first) == 64


def test_annotation_order_is_deterministic() -> None:
    chunk_ids = [f"{number}:chunk:00000" for number in range(100, 106)]
    ordered = order_chunk_ids_for_annotation(chunk_ids, seed=42, query_id="q001")
    assert ordered == [
        "103:chunk:00000",
        "104:chunk:00000",
        "105:chunk:00000",
        "102:chunk:00000",
        "101:chunk:00000",
        "100:chunk:00000",
    ]


def test_annotation_order_rejects_duplicate_chunks() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        order_chunk_ids_for_annotation(
            ["101:chunk:00000", "101:chunk:00000"],
            seed=42,
            query_id="q001",
        )


def test_query_pool_deduplicates_retrievers() -> None:
    battery = make_chunk()
    cooling = make_chunk(
        "102:chunk:00000",
        102,
        "Aircraft battery cooling system evidence.",
    )
    query = EvaluationQuery(query_id="q001", query="battery thermal runaway")
    judgment = RelevanceJudgment(
        query_id="q001",
        relevant_chunk_ids=[cooling.chunk_id],
    )

    internal, annotation = build_query_candidate_pool(
        query=query,
        bm25_hits=[SearchHit(rank=1, score=10.0, chunk=battery)],
        dense_hits=[
            DenseSearchHit(rank=2, score=0.81, chunk=battery),
            DenseSearchHit(rank=1, score=0.84, chunk=cooling),
        ],
        previous_judgment=judgment,
        chunk_by_id={
            battery.chunk_id: battery,
            cooling.chunk_id: cooling,
        },
    )

    assert len(internal.candidates) == 2
    assert len(annotation.candidates) == 2
    by_chunk = {candidate.chunk_id: candidate for candidate in internal.candidates}
    assert by_chunk[battery.chunk_id].retrieved_by == ["bm25", "dense"]
    assert by_chunk[cooling.chunk_id].retrieved_by == ["dense", "v0.1-qrels"]


def test_query_pool_carries_forward_qrel() -> None:
    chunk = make_chunk()
    internal, _ = build_query_candidate_pool(
        query=EvaluationQuery(query_id="q001", query="aerospace evidence"),
        bm25_hits=[],
        dense_hits=[],
        previous_judgment=RelevanceJudgment(
            query_id="q001",
            relevant_chunk_ids=[chunk.chunk_id],
        ),
        chunk_by_id={chunk.chunk_id: chunk},
    )
    assert internal.candidates[0].retrieved_by == ["v0.1-qrels"]


def test_query_pool_rejects_missing_qrel_chunk() -> None:
    with pytest.raises(ValueError, match="missing from the corpus"):
        build_query_candidate_pool(
            query=EvaluationQuery(query_id="q001", query="battery safety"),
            bm25_hits=[],
            dense_hits=[],
            previous_judgment=RelevanceJudgment(
                query_id="q001",
                relevant_chunk_ids=["missing:chunk:00000"],
            ),
            chunk_by_id={},
        )


def test_build_pooled_records_uses_both_indexes() -> None:
    chunk = make_chunk()
    query = EvaluationQuery(query_id="q001", query="battery safety")
    judgment = RelevanceJudgment(
        query_id="q001",
        relevant_chunk_ids=[chunk.chunk_id],
    )

    internal, annotation = build_pooled_candidate_records(
        queries=[query],
        previous_judgments=[judgment],
        chunks=[chunk],
        bm25_index=FakeBM25Index([SearchHit(rank=1, score=5.0, chunk=chunk)]),
        dense_index=FakeDenseIndex([DenseSearchHit(rank=1, score=0.8, chunk=chunk)]),
    )

    assert len(internal) == 1
    assert len(annotation) == 1
    assert internal[0].candidates[0].retrieved_by == [
        "bm25",
        "dense",
        "v0.1-qrels",
    ]


def test_annotation_writer_is_blinded(tmp_path: Path) -> None:
    record = AnnotationQueryPool(
        query_id="q001",
        query="battery evidence",
        candidates=[make_annotation_candidate()],
    )
    path = tmp_path / "annotations.jsonl"
    write_annotation_candidate_records(path, [record])
    raw = path.read_text(encoding="utf-8")
    assert "retrieved_by" not in raw
    assert "bm25_rank" not in raw
    assert "dense_rank" not in raw
    assert raw.endswith("\n")


def test_internal_writer_preserves_provenance(tmp_path: Path) -> None:
    record = InternalQueryPool(
        query_id="q001",
        query="battery evidence",
        candidates=[make_internal_candidate()],
    )
    path = tmp_path / "internal.jsonl"
    write_internal_candidate_records(path, [record])
    raw = path.read_text(encoding="utf-8")
    assert '"retrieved_by"' in raw
    assert '"bm25_rank"' in raw
    assert raw.endswith("\n")


def test_annotation_records_round_trip(tmp_path: Path) -> None:
    record = AnnotationQueryPool(
        query_id="q001",
        query="battery evidence",
        candidates=[make_annotation_candidate()],
    )
    path = tmp_path / "annotations.jsonl"
    write_annotation_candidate_records(path, [record])
    assert load_annotation_records(path) == [record]


def test_incomplete_annotations_rejected() -> None:
    record = AnnotationQueryPool(
        query_id="q001",
        query="battery evidence",
        candidates=[make_annotation_candidate()],
    )
    with pytest.raises(ValueError, match="Incomplete relevance labels"):
        build_qrels_from_annotations([record])


def test_query_without_relevant_candidate_rejected() -> None:
    record = AnnotationQueryPool(
        query_id="q001",
        query="battery evidence",
        candidates=[make_annotation_candidate(relevant=False)],
    )
    with pytest.raises(ValueError, match="at least one relevant candidate"):
        build_qrels_from_annotations([record])


def test_completed_annotations_create_qrels(tmp_path: Path) -> None:
    record = AnnotationQueryPool(
        query_id="q001",
        query="battery evidence",
        candidates=[
            make_annotation_candidate(relevant=True),
            make_annotation_candidate(
                candidate_id="q001:c002",
                chunk_id="102:chunk:00000",
                relevant=False,
            ),
        ],
    )
    judgments = build_qrels_from_annotations([record])
    assert judgments == [
        RelevanceJudgment(
            query_id="q001",
            relevant_chunk_ids=["101:chunk:00000"],
        )
    ]

    path = tmp_path / "qrels.jsonl"
    write_relevance_judgments(path, judgments)
    assert path.read_text(encoding="utf-8").endswith("\n")
