from pathlib import Path
from types import SimpleNamespace

import pytest

from aeroragx.evaluation.retrieval import (
    EvaluationQuery,
    RelevanceJudgment,
    build_bm25_candidates,
    evaluate_bm25,
    evaluate_dense,
    load_evaluation_queries,
    load_relevance_judgments,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    write_candidate_records,
    write_evaluation_report,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.bm25 import BM25Index


def make_chunk(
    chunk_id: str,
    document_id: int,
    text: str,
) -> ChunkRecord:
    """Create a deterministic evaluation chunk."""

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


def make_index() -> BM25Index:
    """Create a small deterministic index."""

    return BM25Index(
        [
            make_chunk(
                "101:chunk:00000",
                101,
                ("battery thermal runaway propagation cooling aircraft"),
            ),
            make_chunk(
                "102:chunk:00000",
                102,
                ("fuel cell aircraft thermal management cooling"),
            ),
            make_chunk(
                "103:chunk:00000",
                103,
                "airport traffic operations",
            ),
        ]
    )


class FakeDenseIndex:
    """Deterministic dense index for evaluation tests."""

    def __init__(
        self,
        chunks: list[ChunkRecord],
    ) -> None:
        self._chunks = chunks

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SimpleNamespace]:
        """Return query-specific ranked chunks."""

        if "battery" in query.lower():
            ordered_ids = [
                "101:chunk:00000",
                "103:chunk:00000",
                "102:chunk:00000",
            ]
        elif "fuel cell" in query.lower():
            ordered_ids = [
                "102:chunk:00000",
                "103:chunk:00000",
                "101:chunk:00000",
            ]
        else:
            ordered_ids = [chunk.chunk_id for chunk in self._chunks]

        chunk_by_id = {chunk.chunk_id: chunk for chunk in self._chunks}

        return [SimpleNamespace(chunk=chunk_by_id[chunk_id]) for chunk_id in ordered_ids[:top_k]]


def test_evaluate_dense() -> None:
    chunks = [
        make_chunk(
            "101:chunk:00000",
            101,
            ("battery thermal runaway propagation cooling aircraft"),
        ),
        make_chunk(
            "102:chunk:00000",
            102,
            ("fuel cell aircraft thermal management cooling"),
        ),
        make_chunk(
            "103:chunk:00000",
            103,
            "airport traffic operations",
        ),
    ]

    queries = [
        EvaluationQuery(
            query_id="q001",
            query="battery thermal runaway",
        ),
        EvaluationQuery(
            query_id="q002",
            query="fuel cell thermal management",
        ),
    ]

    judgments = [
        RelevanceJudgment(
            query_id="q001",
            relevant_chunk_ids=["101:chunk:00000"],
        ),
        RelevanceJudgment(
            query_id="q002",
            relevant_chunk_ids=["102:chunk:00000"],
        ),
    ]

    report = evaluate_dense(
        index=FakeDenseIndex(chunks),  # type: ignore[arg-type]
        queries=queries,
        judgments=judgments,
        top_k=10,
    )

    assert report.model_name == "dense"
    assert report.query_count == 2
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_retrieval_metrics() -> None:
    retrieved = [
        "irrelevant",
        "relevant-1",
        "relevant-2",
    ]
    relevant = [
        "relevant-1",
        "relevant-2",
    ]

    assert (
        recall_at_k(
            retrieved,
            relevant,
            2,
        )
        == 0.5
    )

    assert (
        reciprocal_rank_at_k(
            retrieved,
            relevant,
            10,
        )
        == 0.5
    )

    assert (
        ndcg_at_k(
            retrieved,
            relevant,
            10,
        )
        > 0.0
    )


def test_build_candidates_preserves_metadata() -> None:
    records = build_bm25_candidates(
        index=make_index(),
        queries=[
            EvaluationQuery(
                query_id="q001",
                query="battery thermal runaway",
            )
        ],
        top_k=5,
    )

    assert len(records) == 1
    assert records[0].candidates
    assert records[0].candidates[0].chunk_id == "101:chunk:00000"
    assert records[0].candidates[0].citation_url.endswith("/101")


def test_evaluate_bm25() -> None:
    queries = [
        EvaluationQuery(
            query_id="q001",
            query="battery thermal runaway",
        ),
        EvaluationQuery(
            query_id="q002",
            query="fuel cell thermal management",
        ),
    ]

    judgments = [
        RelevanceJudgment(
            query_id="q001",
            relevant_chunk_ids=["101:chunk:00000"],
        ),
        RelevanceJudgment(
            query_id="q002",
            relevant_chunk_ids=["102:chunk:00000"],
        ),
    ]

    report = evaluate_bm25(
        index=make_index(),
        queries=queries,
        judgments=judgments,
        top_k=10,
    )

    assert report.query_count == 2
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_evaluation_rejects_missing_judgment() -> None:
    with pytest.raises(
        ValueError,
        match="Missing relevance judgments",
    ):
        evaluate_bm25(
            index=make_index(),
            queries=[
                EvaluationQuery(
                    query_id="q001",
                    query="battery thermal",
                )
            ],
            judgments=[],
            top_k=10,
        )


def test_load_and_write_evaluation_files(
    tmp_path: Path,
) -> None:
    queries_path = tmp_path / "queries.jsonl"
    qrels_path = tmp_path / "qrels.jsonl"

    queries_path.write_text(
        ('{"query_id":"q001","query":"battery thermal"}\n'),
        encoding="utf-8",
    )

    qrels_path.write_text(
        ('{"query_id":"q001","relevant_chunk_ids":["101:chunk:00000"]}\n'),
        encoding="utf-8",
    )

    queries = load_evaluation_queries(queries_path)
    judgments = load_relevance_judgments(qrels_path)

    candidates = build_bm25_candidates(
        make_index(),
        queries,
    )

    report = evaluate_bm25(
        make_index(),
        queries,
        judgments,
    )

    candidates_output = tmp_path / "candidates.jsonl"
    report_output = tmp_path / "report.json"

    write_candidate_records(
        candidates_output,
        candidates,
    )
    write_evaluation_report(
        report_output,
        report,
    )

    assert candidates_output.exists()
    assert report_output.exists()
