"""Tests for retrieval evaluation and judgment utilities."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from aeroragx.evaluation.retrieval import (
    EvaluationQuery,
    RelevanceJudgment,
    build_bm25_candidates,
    evaluate_bm25,
    evaluate_dense,
    evaluate_retriever,
    load_evaluation_queries,
    load_relevance_judgments,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    write_candidate_records,
    write_evaluation_report,
)
from aeroragx.processing.chunking import (
    ChunkRecord,
)
from aeroragx.retrieval.bm25 import (
    BM25Index,
)


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
        document_sha256=("test-checksum"),
    )


def make_chunks() -> list[ChunkRecord]:
    """Create the shared test corpus."""

    return [
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


def make_index() -> BM25Index:
    """Create a small deterministic BM25 index."""

    return BM25Index(make_chunks())


def make_queries() -> list[EvaluationQuery]:
    """Create shared evaluation queries."""

    return [
        EvaluationQuery(
            query_id="q001",
            query=("battery thermal runaway"),
        ),
        EvaluationQuery(
            query_id="q002",
            query=("fuel cell thermal management"),
        ),
    ]


def make_judgments() -> list[RelevanceJudgment]:
    """Create shared relevance judgments."""

    return [
        RelevanceJudgment(
            query_id="q001",
            relevant_chunk_ids=["101:chunk:00000"],
        ),
        RelevanceJudgment(
            query_id="q002",
            relevant_chunk_ids=["102:chunk:00000"],
        ),
    ]


@dataclass(frozen=True)
class FakeRetrievalHit:
    """Protocol-compatible retrieval hit."""

    rank: int
    score: float
    chunk: ChunkRecord


class FakeRetrievalIndex:
    """Deterministic protocol-compatible index."""

    def __init__(
        self,
        chunks: list[ChunkRecord],
    ) -> None:
        self._chunks = chunks

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[FakeRetrievalHit]:
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

        return [
            FakeRetrievalHit(
                rank=rank,
                score=1.0 / rank,
                chunk=chunk_by_id[chunk_id],
            )
            for rank, chunk_id in enumerate(
                ordered_ids[:top_k],
                start=1,
            )
        ]


class DuplicateRetrievalIndex:
    """Index that intentionally repeats a chunk."""

    def __init__(
        self,
        chunk: ChunkRecord,
    ) -> None:
        self._chunk = chunk

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[FakeRetrievalHit]:
        """Return duplicated retrieval hits."""

        del query
        del top_k

        return [
            FakeRetrievalHit(
                rank=1,
                score=1.0,
                chunk=self._chunk,
            ),
            FakeRetrievalHit(
                rank=2,
                score=0.5,
                chunk=self._chunk,
            ),
        ]


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


def test_recall_rejects_invalid_k() -> None:
    with pytest.raises(
        ValueError,
        match="k must be at least 1",
    ):
        recall_at_k(
            ["retrieved"],
            ["relevant"],
            0,
        )


def test_reciprocal_rank_rejects_invalid_k() -> None:
    with pytest.raises(
        ValueError,
        match="k must be at least 1",
    ):
        reciprocal_rank_at_k(
            ["retrieved"],
            ["relevant"],
            0,
        )


def test_ndcg_rejects_invalid_k() -> None:
    with pytest.raises(
        ValueError,
        match="k must be at least 1",
    ):
        ndcg_at_k(
            ["retrieved"],
            ["relevant"],
            0,
        )


def test_build_candidates_preserves_metadata() -> None:
    records = build_bm25_candidates(
        index=make_index(),
        queries=[
            EvaluationQuery(
                query_id="q001",
                query=("battery thermal runaway"),
            )
        ],
        top_k=5,
    )

    assert len(records) == 1
    assert records[0].candidates

    first_candidate = records[0].candidates[0]

    assert first_candidate.chunk_id == "101:chunk:00000"
    assert first_candidate.citation_url.endswith("/101")


def test_evaluate_retriever() -> None:
    report = evaluate_retriever(
        index=FakeRetrievalIndex(make_chunks()),
        model_name="fake-retriever",
        queries=make_queries(),
        judgments=make_judgments(),
        top_k=10,
    )

    assert report.model_name == "fake-retriever"
    assert report.query_count == 2
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_evaluate_dense_wrapper() -> None:
    report = evaluate_dense(
        index=FakeRetrievalIndex(make_chunks()),
        queries=make_queries(),
        judgments=make_judgments(),
        top_k=10,
    )

    assert report.model_name == "dense"
    assert report.query_count == 2
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_evaluate_bm25_wrapper() -> None:
    report = evaluate_bm25(
        index=make_index(),
        queries=make_queries(),
        judgments=make_judgments(),
        top_k=10,
    )

    assert report.model_name == "bm25"
    assert report.query_count == 2
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_wrappers_match_generic_evaluator() -> None:
    index = FakeRetrievalIndex(make_chunks())
    queries = make_queries()
    judgments = make_judgments()

    generic = evaluate_retriever(
        index=index,
        model_name="dense",
        queries=queries,
        judgments=judgments,
        top_k=10,
    )

    wrapped = evaluate_dense(
        index=index,
        queries=queries,
        judgments=judgments,
        top_k=10,
    )

    assert wrapped == generic


def test_evaluation_rejects_empty_model_name() -> None:
    with pytest.raises(
        ValueError,
        match="model_name must not be empty",
    ):
        evaluate_retriever(
            index=FakeRetrievalIndex(make_chunks()),
            model_name=" ",
            queries=make_queries(),
            judgments=make_judgments(),
            top_k=10,
        )


def test_evaluation_rejects_top_k_below_ten() -> None:
    with pytest.raises(
        ValueError,
        match="top_k must be at least 10",
    ):
        evaluate_retriever(
            index=FakeRetrievalIndex(make_chunks()),
            model_name="fake",
            queries=make_queries(),
            judgments=make_judgments(),
            top_k=9,
        )


def test_evaluation_rejects_empty_queries() -> None:
    with pytest.raises(
        ValueError,
        match=("At least one evaluation query"),
    ):
        evaluate_retriever(
            index=FakeRetrievalIndex(make_chunks()),
            model_name="fake",
            queries=[],
            judgments=[],
            top_k=10,
        )


def test_evaluation_rejects_duplicate_queries() -> None:
    duplicate_query = EvaluationQuery(
        query_id="q001",
        query="duplicate",
    )

    with pytest.raises(
        ValueError,
        match=("Evaluation query IDs must be unique"),
    ):
        evaluate_retriever(
            index=FakeRetrievalIndex(make_chunks()),
            model_name="fake",
            queries=[
                make_queries()[0],
                duplicate_query,
            ],
            judgments=[make_judgments()[0]],
            top_k=10,
        )


def test_evaluation_rejects_duplicate_judgments() -> None:
    duplicate_judgment = RelevanceJudgment(
        query_id="q001",
        relevant_chunk_ids=["102:chunk:00000"],
    )

    with pytest.raises(
        ValueError,
        match=("Relevance judgment IDs must be unique"),
    ):
        evaluate_retriever(
            index=FakeRetrievalIndex(make_chunks()),
            model_name="fake",
            queries=[make_queries()[0]],
            judgments=[
                make_judgments()[0],
                duplicate_judgment,
            ],
            top_k=10,
        )


def test_evaluation_rejects_missing_judgment() -> None:
    with pytest.raises(
        ValueError,
        match=("Missing relevance judgments"),
    ):
        evaluate_bm25(
            index=make_index(),
            queries=[
                EvaluationQuery(
                    query_id="q001",
                    query=("battery thermal"),
                )
            ],
            judgments=[],
            top_k=10,
        )


def test_evaluation_rejects_unknown_judgment() -> None:
    with pytest.raises(
        ValueError,
        match=("Judgments contain unknown queries"),
    ):
        evaluate_retriever(
            index=FakeRetrievalIndex(make_chunks()),
            model_name="fake",
            queries=[make_queries()[0]],
            judgments=[
                make_judgments()[0],
                RelevanceJudgment(
                    query_id="q999",
                    relevant_chunk_ids=["103:chunk:00000"],
                ),
            ],
            top_k=10,
        )


def test_evaluation_rejects_duplicate_hits() -> None:
    query = make_queries()[0]
    judgment = make_judgments()[0]

    with pytest.raises(
        ValueError,
        match=("Retriever returned duplicate chunks"),
    ):
        evaluate_retriever(
            index=DuplicateRetrievalIndex(make_chunks()[0]),
            model_name="duplicate",
            queries=[query],
            judgments=[judgment],
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
