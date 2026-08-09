"""Tests for cross-encoder reranking."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic import ValidationError

from aeroragx.evaluation.retrieval import (
    EvaluationQuery,
    RelevanceJudgment,
    evaluate_retriever,
)
from aeroragx.observability import (
    create_tracing_runtime,
    use_tracer,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.hybrid import HybridSearchHit
from aeroragx.retrieval.reranker import (
    RerankedSearchHit,
    RerankerConfig,
    RerankerIndex,
    load_reranker_config,
    with_candidate_top_k,
    write_reranked_search_results,
    write_reranker_latency_report,
)


def make_chunk(
    chunk_id: str,
    document_id: int,
    text: str,
    *,
    page_start: int = 1,
    page_end: int = 1,
) -> ChunkRecord:
    """Create one deterministic citation-preserving chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=page_start,
        page_end=page_end,
        page_ids=[
            f"{document_id}:page:{page}"
            for page in range(
                page_start,
                page_end + 1,
            )
        ],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url=(f"https://ntrs.nasa.gov/citations/{document_id}"),
        source_url=(f"https://example.com/{document_id}.pdf"),
        document_sha256="a" * 64,
    )


def make_hybrid_hits() -> list[HybridSearchHit]:
    """Create a deterministic three-candidate Hybrid RRF result set."""

    first = make_chunk(
        "101:chunk:00000",
        101,
        "battery thermal runaway propagation evidence",
        page_start=2,
        page_end=3,
    )
    second = make_chunk(
        "102:chunk:00000",
        102,
        "aircraft battery cooling system evidence",
    )
    third = make_chunk(
        "103:chunk:00000",
        103,
        "electric propulsion thermal management evidence",
    )

    return [
        HybridSearchHit(
            rank=1,
            score=0.032786885246,
            chunk=first,
            retrieved_by=["bm25", "dense"],
            bm25_rank=1,
            bm25_score=15.0,
            dense_rank=1,
            dense_score=0.91,
        ),
        HybridSearchHit(
            rank=2,
            score=0.016129032258,
            chunk=second,
            retrieved_by=["bm25"],
            bm25_rank=2,
            bm25_score=10.0,
        ),
        HybridSearchHit(
            rank=3,
            score=0.015873015873,
            chunk=third,
            retrieved_by=["dense"],
            dense_rank=3,
            dense_score=0.82,
        ),
    ]


class FakeHybridIndex:
    """Return a fixed Hybrid RRF result list."""

    def __init__(
        self,
        hits: Sequence[HybridSearchHit],
    ) -> None:
        self._hits = list(hits)
        self.requested_top_k: list[int] = []

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[HybridSearchHit]:
        """Return at most the requested number of hybrid hits."""

        del query
        self.requested_top_k.append(top_k)
        return self._hits[:top_k]


class FakeRerankerScorer:
    """Return deterministic scores based on exact document text."""

    def __init__(
        self,
        scores_by_text: dict[str, float],
    ) -> None:
        self._scores_by_text = scores_by_text
        self.received_queries: list[str] = []
        self.received_documents: list[list[str]] = []
        self.received_batch_sizes: list[int] = []
        self.received_progress_values: list[bool] = []

    def score(
        self,
        query: str,
        documents: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        """Return one configured score for each document."""

        self.received_queries.append(query)
        self.received_documents.append(list(documents))
        self.received_batch_sizes.append(batch_size)
        self.received_progress_values.append(show_progress_bar)

        return [self._scores_by_text[document] for document in documents]


@dataclass
class FixedSequenceScorer:
    """Return a supplied score sequence without inspecting documents."""

    scores: list[float]

    def score(
        self,
        query: str,
        documents: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        """Return the configured sequence."""

        del query
        del documents
        del batch_size
        del show_progress_bar
        return self.scores


def make_config(**updates: object) -> RerankerConfig:
    """Create a validated test configuration."""

    values: dict[str, object] = {
        "version": "0.1",
        "model_name": ("cross-encoder/ms-marco-MiniLM-L6-v2"),
        "candidate_top_k": 20,
        "default_top_k": 10,
        "batch_size": 16,
        "max_length": None,
        "device": "cpu",
        "show_progress_bar": False,
    }
    values.update(updates)
    return RerankerConfig.model_validate(values)


def make_reranker_index() -> tuple[
    RerankerIndex,
    FakeRerankerScorer,
    FakeHybridIndex,
]:
    """Create a reranker whose scores change hybrid ordering."""

    hits = make_hybrid_hits()
    scorer = FakeRerankerScorer(
        {
            hits[0].chunk.text: 1.0,
            hits[1].chunk.text: 9.0,
            hits[2].chunk.text: -2.0,
        }
    )
    hybrid_index = FakeHybridIndex(hits)

    return (
        RerankerIndex(
            hybrid_index=hybrid_index,
            scorer=scorer,
            config=make_config(),
        ),
        scorer,
        hybrid_index,
    )


def test_load_reranker_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reranker.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            'model_name: "cross-encoder/test"\n'
            "candidate_top_k: 20\n"
            "default_top_k: 10\n"
            "batch_size: 8\n"
            "max_length: 256\n"
            'device: "cpu"\n'
            "show_progress_bar: false\n"
        ),
        encoding="utf-8",
    )

    config = load_reranker_config(path)

    assert config.model_name == "cross-encoder/test"
    assert config.candidate_top_k == 20
    assert config.default_top_k == 10
    assert config.batch_size == 8
    assert config.max_length == 256
    assert config.device == "cpu"
    assert config.show_progress_bar is False


def test_load_reranker_config_rejects_non_mapping(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reranker.yaml"
    path.write_text(
        "- invalid\n- configuration\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must contain a YAML mapping",
    ):
        load_reranker_config(path)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"model_name": " "}, "at least 1 character"),
        ({"candidate_top_k": 0}, "greater than or equal to 1"),
        ({"batch_size": 0}, "greater than or equal to 1"),
        ({"max_length": 0}, "greater than or equal to 1"),
        (
            {
                "candidate_top_k": 5,
                "default_top_k": 10,
            },
            "default_top_k must not exceed",
        ),
    ],
)
def test_reranker_config_rejects_invalid_values(
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(
        ValidationError,
        match=message,
    ):
        make_config(**updates)


def test_candidate_depth_override_is_validated() -> None:
    config = with_candidate_top_k(
        make_config(),
        30,
    )

    assert config.candidate_top_k == 30

    with pytest.raises(
        ValidationError,
        match="default_top_k must not exceed",
    ):
        with_candidate_top_k(
            make_config(),
            5,
        )


def test_reranks_candidates_using_cross_encoder_scores() -> None:
    index, _, _ = make_reranker_index()

    hits = index.search(
        "battery thermal runaway",
        top_k=3,
    )

    assert [hit.chunk.chunk_id for hit in hits] == [
        "102:chunk:00000",
        "101:chunk:00000",
        "103:chunk:00000",
    ]
    assert [hit.rank for hit in hits] == [1, 2, 3]
    assert [hit.score for hit in hits] == [9.0, 1.0, -2.0]


def test_preserves_all_retrieval_provenance() -> None:
    index, _, _ = make_reranker_index()
    first = index.search("battery", top_k=1)[0]

    assert first.chunk.chunk_id == "102:chunk:00000"
    assert first.hybrid_rank == 2
    assert first.hybrid_score == pytest.approx(0.016129032258)
    assert first.retrieved_by == ["bm25"]
    assert first.bm25_rank == 2
    assert first.bm25_score == 10.0
    assert first.dense_rank is None
    assert first.dense_score is None
    assert first.chunk.citation_url.endswith("/102")
    assert first.chunk.page_start == 1
    assert first.chunk.page_end == 1


def test_scorer_receives_hybrid_order_and_config() -> None:
    index, scorer, hybrid_index = make_reranker_index()
    original_hits = make_hybrid_hits()

    index.search(
        "battery query",
        top_k=2,
    )

    assert hybrid_index.requested_top_k == [20]
    assert scorer.received_queries == ["battery query"]
    assert scorer.received_documents == [[hit.chunk.text for hit in original_hits]]
    assert scorer.received_batch_sizes == [16]
    assert scorer.received_progress_values == [False]


def test_respects_top_k() -> None:
    index, _, _ = make_reranker_index()

    hits = index.search("battery", top_k=2)

    assert len(hits) == 2
    assert [hit.rank for hit in hits] == [1, 2]


def test_rejects_invalid_top_k() -> None:
    index, _, _ = make_reranker_index()

    with pytest.raises(
        ValueError,
        match="top_k must be at least 1",
    ):
        index.search("battery", top_k=0)

    with pytest.raises(
        ValueError,
        match="must not exceed candidate_top_k",
    ):
        index.search("battery", top_k=21)


def test_rejects_duplicate_hybrid_candidates() -> None:
    hit = make_hybrid_hits()[0]
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex([hit, hit]),
        scorer=FixedSequenceScorer([1.0, 0.5]),
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="duplicate chunk IDs",
    ):
        index.search("battery", top_k=2)


@pytest.mark.parametrize(
    "scores",
    [
        [1.0],
        [1.0, 2.0, 3.0, 4.0],
    ],
)
def test_rejects_score_count_mismatch(
    scores: list[float],
) -> None:
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex(make_hybrid_hits()),
        scorer=FixedSequenceScorer(scores),
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="different number of scores",
    ):
        index.search("battery", top_k=3)


@pytest.mark.parametrize(
    "invalid_score",
    [math.nan, math.inf, -math.inf],
)
def test_rejects_non_finite_scores(
    invalid_score: float,
) -> None:
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex(make_hybrid_hits()),
        scorer=FixedSequenceScorer([1.0, invalid_score, 0.0]),
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="non-finite score",
    ):
        index.search("battery", top_k=3)


def test_allows_negative_finite_scores() -> None:
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex(make_hybrid_hits()),
        scorer=FixedSequenceScorer([-1.0, -2.0, -3.0]),
        config=make_config(),
    )

    hits = index.search("battery", top_k=3)

    assert [hit.score for hit in hits] == [
        -1.0,
        -2.0,
        -3.0,
    ]


def test_tied_scores_use_hybrid_rank_then_chunk_id() -> None:
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex(make_hybrid_hits()),
        scorer=FixedSequenceScorer([5.0, 5.0, 5.0]),
        config=make_config(),
    )

    hits = index.search("battery", top_k=3)

    assert [hit.hybrid_rank for hit in hits] == [1, 2, 3]


def test_raw_hybrid_scores_do_not_control_final_order() -> None:
    hits = make_hybrid_hits()
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex(hits),
        scorer=FixedSequenceScorer([-10.0, 100.0, 50.0]),
        config=make_config(),
    )

    reranked = index.search("battery", top_k=3)

    assert [hit.hybrid_rank for hit in reranked] == [2, 3, 1]


def test_generic_evaluator_accepts_reranker_index() -> None:
    hits = make_hybrid_hits()
    index = RerankerIndex(
        hybrid_index=FakeHybridIndex(hits),
        scorer=FixedSequenceScorer([10.0, 1.0, 0.0]),
        config=make_config(),
    )

    report = evaluate_retriever(
        index=index,
        model_name="cross_encoder_reranker",
        queries=[
            EvaluationQuery(
                query_id="q001",
                query="battery thermal runaway",
            )
        ],
        judgments=[
            RelevanceJudgment(
                query_id="q001",
                relevant_chunk_ids=["101:chunk:00000"],
            )
        ],
        top_k=10,
    )

    assert report.model_name == "cross_encoder_reranker"
    assert report.query_count == 1
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_latency_report_tracks_scoring_pairs() -> None:
    index, _, _ = make_reranker_index()
    index.reset_timing()

    index.search("first", top_k=2)
    index.search("second", top_k=2)

    report = index.build_latency_report(hardware_note="test hardware")

    assert report.query_count == 2
    assert report.pair_count == 6
    assert report.total_seconds >= 0.0
    assert report.milliseconds_per_pair >= 0.0
    assert report.hardware_note == "test hardware"


def test_write_reranked_outputs(
    tmp_path: Path,
) -> None:
    index, _, _ = make_reranker_index()
    hits = index.search("battery", top_k=2)

    results_path = tmp_path / "reranked.jsonl"
    latency_path = tmp_path / "latency.json"

    write_reranked_search_results(
        results_path,
        hits,
    )
    write_reranker_latency_report(
        latency_path,
        index.build_latency_report(),
    )

    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    latency = json.loads(latency_path.read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert rows[0]["rank"] == 1
    assert "hybrid_rank" in rows[0]
    assert "retrieved_by" in rows[0]
    assert latency["pair_count"] == 3


def test_reranked_hit_rejects_non_finite_score() -> None:
    hybrid_hit = make_hybrid_hits()[0]

    with pytest.raises(
        ValidationError,
        match="score must be finite",
    ):
        RerankedSearchHit(
            rank=1,
            score=math.inf,
            chunk=hybrid_hit.chunk,
            hybrid_rank=hybrid_hit.rank,
            hybrid_score=hybrid_hit.score,
            retrieved_by=hybrid_hit.retrieved_by,
            bm25_rank=hybrid_hit.bm25_rank,
            bm25_score=hybrid_hit.bm25_score,
            dense_rank=hybrid_hit.dense_rank,
            dense_score=hybrid_hit.dense_score,
        )


def test_reranker_records_detailed_search_timings() -> None:
    index, _, _ = make_reranker_index()

    hits = index.search(
        "battery thermal runaway",
        top_k=2,
    )

    timings = index.last_search_timings

    assert len(hits) == 2
    assert timings is not None
    assert timings.candidate_retrieval_ms >= 0.0
    assert timings.reranker_scoring_ms >= 0.0
    assert timings.ranking_ms >= 0.0
    assert timings.total_ms >= 0.0
    assert timings.pair_count == 3
    assert timings.hybrid is None


def test_reranker_search_emits_span_without_raw_query() -> None:
    exporter = InMemorySpanExporter()
    tracing_runtime = create_tracing_runtime(
        exporter=exporter,
        environment="test",
        batch_export=False,
    )
    index, _, _ = make_reranker_index()
    raw_query = "Sensitive reranker tracing query"

    with use_tracer(tracing_runtime.tracer):
        with tracing_runtime.tracer.start_as_current_span(
            "aeroragx.test.parent",
        ) as parent_span:
            hits = index.search(
                raw_query,
                top_k=2,
            )

    assert len(hits) == 2

    tracing_runtime.force_flush()
    spans = exporter.get_finished_spans()

    reranker_span = next(span for span in spans if span.name == "aeroragx.reranker")

    assert reranker_span.context is not None
    assert reranker_span.parent is not None

    parent_context = parent_span.get_span_context()

    assert reranker_span.context.trace_id == parent_context.trace_id
    assert reranker_span.parent.span_id == parent_context.span_id

    assert reranker_span.attributes["aeroragx.model"] == "cross-encoder/ms-marco-MiniLM-L6-v2"
    assert reranker_span.attributes["aeroragx.requested_top_k"] == 2
    assert reranker_span.attributes["aeroragx.candidate_top_k"] == 20
    assert reranker_span.attributes["aeroragx.batch_size"] == 16
    assert reranker_span.attributes["aeroragx.pair_count"] == 3
    assert reranker_span.attributes["aeroragx.result_count"] == 2

    serialized = repr(dict(reranker_span.attributes))

    assert raw_query not in serialized

    tracing_runtime.shutdown()
