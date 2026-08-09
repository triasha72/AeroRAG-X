"""Tests for reciprocal-rank-fusion hybrid retrieval."""

import json
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
    RetrievalHit,
    evaluate_retriever,
)
from aeroragx.observability import (
    create_tracing_runtime,
    use_tracer,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.hybrid import (
    HybridConfig,
    HybridIndex,
    HybridSearchHit,
    load_hybrid_config,
    write_hybrid_search_results,
)


def make_chunk(
    chunk_id: str,
    document_id: int,
    text: str,
    *,
    page_start: int = 1,
    page_end: int = 1,
) -> ChunkRecord:
    """Create one deterministic retrieval chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=page_start,
        page_end=page_end,
        page_ids=[
            f"{document_id}:page:{page_number}" for page_number in range(page_start, page_end + 1)
        ],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url=f"https://ntrs.nasa.gov/citations/{document_id}",
        source_url=f"https://example.com/{document_id}.pdf",
        document_sha256="a" * 64,
    )


@dataclass(frozen=True)
class FakeHit:
    """Protocol-compatible source hit."""

    rank: int
    score: float
    chunk: ChunkRecord


class FakeIndex:
    """Return a fixed ranked result list."""

    def __init__(self, hits: list[FakeHit]) -> None:
        self._hits = hits
        self.requested_top_k: list[int] = []

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[FakeHit]:
        """Return at most the requested number of hits."""

        del query
        self.requested_top_k.append(top_k)
        return self._hits[:top_k]


def make_chunks() -> list[ChunkRecord]:
    """Create a shared three-chunk corpus."""

    return [
        make_chunk(
            "101:chunk:00000",
            101,
            "battery thermal runaway propagation evidence",
            page_start=2,
            page_end=3,
        ),
        make_chunk(
            "102:chunk:00000",
            102,
            "aircraft battery cooling system evidence",
        ),
        make_chunk(
            "103:chunk:00000",
            103,
            "electric propulsion thermal management",
        ),
    ]


def make_hybrid_index() -> HybridIndex:
    """Create a hybrid index with overlapping results."""

    first, second, third = make_chunks()

    return HybridIndex(
        bm25_index=FakeIndex(
            [
                FakeHit(rank=1, score=15.0, chunk=first),
                FakeHit(rank=2, score=10.0, chunk=second),
            ]
        ),
        dense_index=FakeIndex(
            [
                FakeHit(rank=1, score=0.91, chunk=first),
                FakeHit(rank=2, score=0.83, chunk=third),
            ]
        ),
        config=HybridConfig(),
    )


def test_load_hybrid_config(tmp_path: Path) -> None:
    path = tmp_path / "hybrid.yaml"
    path.write_text(
        ('version: "0.1"\nrrf_k: 60\nbm25_top_k: 50\ndense_top_k: 40\ndefault_top_k: 10\n'),
        encoding="utf-8",
    )

    config = load_hybrid_config(path)

    assert config.version == "0.1"
    assert config.rrf_k == 60
    assert config.bm25_top_k == 50
    assert config.dense_top_k == 40
    assert config.default_top_k == 10


def test_load_hybrid_config_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "hybrid.yaml"
    path.write_text("- invalid\n- configuration\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_hybrid_config(path)


def test_hybrid_config_rejects_invalid_rrf_k() -> None:
    with pytest.raises(ValidationError):
        HybridConfig(rrf_k=0)


def test_fuses_chunk_returned_by_both_sources() -> None:
    first = make_hybrid_index().search(
        "battery thermal runaway",
        top_k=10,
    )[0]

    assert first.chunk.chunk_id == "101:chunk:00000"
    assert first.retrieved_by == ["bm25", "dense"]
    assert first.bm25_rank == 1
    assert first.dense_rank == 1
    assert first.bm25_score == 15.0
    assert first.dense_score == 0.91
    assert first.score == pytest.approx(
        (1.0 / 61) + (1.0 / 61),
        abs=1e-12,
    )


def test_preserves_single_source_candidates() -> None:
    hits = make_hybrid_index().search("battery", top_k=10)
    by_chunk = {hit.chunk.chunk_id: hit for hit in hits}

    bm25_only = by_chunk["102:chunk:00000"]
    dense_only = by_chunk["103:chunk:00000"]

    assert bm25_only.retrieved_by == ["bm25"]
    assert bm25_only.bm25_rank == 2
    assert bm25_only.dense_rank is None

    assert dense_only.retrieved_by == ["dense"]
    assert dense_only.dense_rank == 2
    assert dense_only.bm25_rank is None


def test_deduplicates_across_retrievers() -> None:
    chunk_ids = [hit.chunk.chunk_id for hit in make_hybrid_index().search("battery", top_k=10)]

    assert len(chunk_ids) == 3
    assert len(chunk_ids) == len(set(chunk_ids))


def test_rejects_duplicate_bm25_hits() -> None:
    chunk = make_chunks()[0]
    index = HybridIndex(
        bm25_index=FakeIndex(
            [
                FakeHit(rank=1, score=10.0, chunk=chunk),
                FakeHit(rank=2, score=9.0, chunk=chunk),
            ]
        ),
        dense_index=FakeIndex([]),
    )

    with pytest.raises(ValueError, match="bm25 returned duplicate chunk"):
        index.search("battery", top_k=10)


def test_rejects_duplicate_dense_hits() -> None:
    chunk = make_chunks()[0]
    index = HybridIndex(
        bm25_index=FakeIndex([]),
        dense_index=FakeIndex(
            [
                FakeHit(rank=1, score=0.9, chunk=chunk),
                FakeHit(rank=2, score=0.8, chunk=chunk),
            ]
        ),
    )

    with pytest.raises(ValueError, match="dense returned duplicate chunk"):
        index.search("battery", top_k=10)


def test_tied_rrf_scores_are_deterministic() -> None:
    first, second, _ = make_chunks()
    index = HybridIndex(
        bm25_index=FakeIndex([FakeHit(rank=1, score=100.0, chunk=second)]),
        dense_index=FakeIndex([FakeHit(rank=1, score=0.1, chunk=first)]),
    )

    hits = index.search("battery", top_k=10)

    assert [hit.chunk.chunk_id for hit in hits] == [
        "101:chunk:00000",
        "102:chunk:00000",
    ]


def test_respects_requested_top_k() -> None:
    hits = make_hybrid_index().search("battery", top_k=2)

    assert len(hits) == 2
    assert [hit.rank for hit in hits] == [1, 2]


def test_rejects_invalid_top_k() -> None:
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        make_hybrid_index().search("battery", top_k=0)


def test_preserves_chunk_provenance() -> None:
    first = make_hybrid_index().search("battery", top_k=1)[0]

    assert first.chunk.document_id == 101
    assert first.chunk.page_start == 2
    assert first.chunk.page_end == 3
    assert first.chunk.citation_url.endswith("/101")
    assert first.chunk.source_url.endswith("/101.pdf")


def test_rejects_inconsistent_chunk_metadata() -> None:
    original = make_chunks()[0]
    changed = original.model_copy(update={"page_end": 4})

    index = HybridIndex(
        bm25_index=FakeIndex([FakeHit(rank=1, score=10.0, chunk=original)]),
        dense_index=FakeIndex([FakeHit(rank=1, score=0.9, chunk=changed)]),
    )

    with pytest.raises(ValueError, match="inconsistent metadata"):
        index.search("battery", top_k=10)


def test_raw_scores_do_not_affect_fusion() -> None:
    first, second, _ = make_chunks()

    low_score_index = HybridIndex(
        bm25_index=FakeIndex(
            [
                FakeHit(rank=1, score=0.01, chunk=first),
                FakeHit(rank=2, score=0.02, chunk=second),
            ]
        ),
        dense_index=FakeIndex([]),
    )
    high_score_index = HybridIndex(
        bm25_index=FakeIndex(
            [
                FakeHit(rank=1, score=1_000_000.0, chunk=first),
                FakeHit(rank=2, score=999_999.0, chunk=second),
            ]
        ),
        dense_index=FakeIndex([]),
    )

    low = low_score_index.search("battery", top_k=10)
    high = high_score_index.search("battery", top_k=10)

    assert [(hit.chunk.chunk_id, hit.score) for hit in low] == [
        (hit.chunk.chunk_id, hit.score) for hit in high
    ]


def test_source_depths_are_requested_from_indexes() -> None:
    bm25_index = FakeIndex([])
    dense_index = FakeIndex([])

    index = HybridIndex(
        bm25_index=bm25_index,
        dense_index=dense_index,
        config=HybridConfig(bm25_top_k=17, dense_top_k=23),
    )
    index.search("battery", top_k=5)

    assert bm25_index.requested_top_k == [17]
    assert dense_index.requested_top_k == [23]


def test_hybrid_hit_rejects_incomplete_metadata() -> None:
    with pytest.raises(
        ValidationError,
        match="bm25_rank and bm25_score",
    ):
        HybridSearchHit(
            rank=1,
            score=0.1,
            chunk=make_chunks()[0],
            retrieved_by=["bm25"],
            bm25_rank=1,
        )


def test_generic_evaluator_accepts_hybrid_index() -> None:
    report = evaluate_retriever(
        index=make_hybrid_index(),
        model_name="hybrid_rrf",
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

    assert report.model_name == "hybrid_rrf"
    assert report.query_count == 1
    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mrr_at_10 == 1.0
    assert report.ndcg_at_10 == 1.0


def test_write_hybrid_search_results(tmp_path: Path) -> None:
    output = tmp_path / "hybrid.jsonl"
    hits = make_hybrid_index().search("battery", top_k=2)

    write_hybrid_search_results(output, hits)

    rows = [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()
    ]

    assert len(rows) == 2
    assert rows[0]["rank"] == 1
    assert rows[0]["retrieved_by"] == ["bm25", "dense"]
    assert rows[0]["chunk"]["citation_url"].endswith("/101")


def test_fake_hits_satisfy_retrieval_protocol() -> None:
    hit: RetrievalHit = FakeHit(
        rank=1,
        score=1.0,
        chunk=make_chunks()[0],
    )

    assert hit.rank == 1


def test_hybrid_records_component_timings() -> None:
    index = make_hybrid_index()

    hits = index.search(
        "battery thermal runaway",
        top_k=2,
    )

    timings = index.last_timings

    assert len(hits) == 2
    assert timings is not None
    assert timings.bm25_ms >= 0.0
    assert timings.dense_ms >= 0.0
    assert timings.fusion_ms >= 0.0
    assert timings.total_ms >= 0.0


def test_hybrid_search_emits_nested_retrieval_spans_without_raw_query() -> None:
    exporter = InMemorySpanExporter()
    tracing_runtime = create_tracing_runtime(
        exporter=exporter,
        environment="test",
        batch_export=False,
    )
    index = make_hybrid_index()
    raw_query = "Sensitive hybrid tracing query"

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
    span_by_name = {span.name: span for span in spans}

    expected_names = {
        "aeroragx.hybrid_retrieval",
        "aeroragx.bm25",
        "aeroragx.dense",
        "aeroragx.hybrid_fusion",
    }

    assert expected_names.issubset(span_by_name)

    hybrid_span = span_by_name["aeroragx.hybrid_retrieval"]
    parent_context = parent_span.get_span_context()

    assert hybrid_span.context is not None
    assert hybrid_span.parent is not None
    assert hybrid_span.context.trace_id == parent_context.trace_id
    assert hybrid_span.parent.span_id == parent_context.span_id

    hybrid_context = hybrid_span.context

    for child_name in (
        "aeroragx.bm25",
        "aeroragx.dense",
        "aeroragx.hybrid_fusion",
    ):
        child = span_by_name[child_name]

        assert child.context is not None
        assert child.parent is not None
        assert child.context.trace_id == hybrid_context.trace_id
        assert child.parent.span_id == hybrid_context.span_id

    assert hybrid_span.attributes["aeroragx.requested_top_k"] == 2
    assert span_by_name["aeroragx.bm25"].attributes["aeroragx.result_count"] == 2
    assert span_by_name["aeroragx.dense"].attributes["aeroragx.result_count"] == 2
    assert span_by_name["aeroragx.hybrid_fusion"].attributes["aeroragx.result_count"] == 2

    serialized = repr([dict(span.attributes) for span in spans])

    assert raw_query not in serialized

    tracing_runtime.shutdown()
