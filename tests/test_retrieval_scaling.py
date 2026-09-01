"""Tests for large-corpus retrieval policies and measurements."""

from pathlib import Path

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit
from aeroragx.retrieval.scaling import (
    ChunkFilter,
    RetrievalScaleConfig,
    ScaleQuery,
    benchmark_retriever,
    chunk_matches_filter,
    plan_incremental_index_update,
    select_hierarchical_evidence,
    truncate_to_token_budget,
    write_scale_report,
)


def make_hit(rank: int, document_id: int, text: str) -> RerankedSearchHit:
    chunk = ChunkRecord(
        chunk_id=f"{document_id}:chunk:{rank:05d}",
        document_id=document_id,
        chunk_index=rank,
        page_start=rank,
        page_end=rank,
        page_ids=[f"{document_id}:page:{rank}"],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url=f"https://ntrs.nasa.gov/citations/{document_id}",
        source_url=f"https://example.com/{document_id}.pdf",
        document_sha256=str(document_id) * 32,
    )
    return RerankedSearchHit(
        rank=rank,
        score=10.0 - rank,
        chunk=chunk,
        hybrid_rank=rank,
        hybrid_score=1.0 / (60 + rank),
        retrieved_by=["bm25"],
        bm25_rank=rank,
        bm25_score=10.0 - rank,
        dense_rank=None,
        dense_score=None,
    )


def test_hierarchical_selection_filters_deduplicates_and_diversifies() -> None:
    repeated = "battery thermal runaway propagation barrier material test result"
    hits = [
        make_hit(1, 1, repeated),
        make_hit(2, 1, repeated + " repeated"),
        make_hit(3, 2, "electrical insulation voltage safety result"),
        make_hit(4, 3, "propulsion integration cooling result"),
    ]
    config = RetrievalScaleConfig(
        candidate_top_k=10,
        rerank_top_k=10,
        evidence_top_k=3,
        max_chunks_per_document=1,
        duplicate_jaccard_threshold=0.7,
    )

    selected = select_hierarchical_evidence(hits, config)

    assert [hit.chunk.document_id for hit in selected] == [1, 2, 3]


def test_metadata_filter_uses_authoritative_chunk_fields() -> None:
    hit = make_hit(1, 42, "thermal management")
    assert chunk_matches_filter(hit.chunk, ChunkFilter(document_ids={42}))
    assert not chunk_matches_filter(hit.chunk, ChunkFilter(document_ids={7}))


def test_token_budget_uses_supplied_tokenizer_counter() -> None:
    counter = lambda text: len(text.split())  # noqa: E731
    assert (
        truncate_to_token_budget(
            "one two three four five",
            token_counter=counter,
            max_tokens=3,
        )
        == "one two three"
    )


def test_incremental_plan_uses_document_checksums() -> None:
    plan = plan_incremental_index_update(
        {1: "same", 2: "old", 3: "deleted"},
        {1: "same", 2: "new", 4: "added"},
    )
    assert plan.unchanged_document_ids == [1]
    assert plan.upsert_document_ids == [2, 4]
    assert plan.delete_document_ids == [3]


def test_scaling_benchmark_records_quality_latency_and_checksum(tmp_path: Path) -> None:
    queries = [
        ScaleQuery(query_id="q1", text="battery", relevant_chunk_ids={"c1", "c2"}),
        ScaleQuery(query_id="q2", text="fuel cell", relevant_chunk_ids={"c3"}),
    ]
    results = {"battery": ["c1", "x"], "fuel cell": ["c3"]}
    measurement = benchmark_retriever(
        corpus_chunks=100_000,
        queries=queries,
        search=lambda query, top_k: results[query][:top_k],
        top_k=10,
    )
    assert measurement.recall_at_k == 0.75
    assert measurement.ndcg_at_k > 0.0

    output = tmp_path / "scale.json"
    write_scale_report(output, [measurement])
    assert '"sha256"' in output.read_text(encoding="utf-8")
