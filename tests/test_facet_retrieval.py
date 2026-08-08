"""Tests for deterministic facet-aware evidence selection."""

from aeroragx.generation.facet_retrieval import (
    FacetAwareEvidenceIndex,
    FacetRetrievalConfig,
    plan_shared_facets,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit

QUERY = "What thermal-management challenges are shared by battery-electric and fuel-cell aircraft?"


def _hit(chunk_id: str, text: str, rank: int) -> RerankedSearchHit:
    chunk = ChunkRecord(
        chunk_id=chunk_id,
        document_id=rank,
        chunk_index=0,
        page_start=1,
        page_end=1,
        page_ids=[f"{rank}:page:1"],
        text=text,
        word_count=max(1, len(text.split())),
        character_count=max(1, len(text)),
        token_estimate=max(1, len(text) // 4),
        citation_url=f"https://example.com/{rank}",
        source_url=f"https://example.com/source/{rank}",
        document_sha256="a" * 64,
    )
    return RerankedSearchHit(
        rank=rank,
        score=float(10 - rank),
        chunk=chunk,
        hybrid_rank=rank,
        hybrid_score=1.0 / (60 + rank),
        retrieved_by=["bm25"],
        bm25_rank=rank,
        bm25_score=float(10 - rank),
    )


class FakeIndex:
    def __init__(self, responses: dict[str, list[RerankedSearchHit]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, top_k: int = 10) -> list[RerankedSearchHit]:
        self.calls.append((query, top_k))
        return self.responses.get(query, [])[:top_k]


def test_plan_extracts_battery_and_fuel_cell_facets() -> None:
    plan = plan_shared_facets(QUERY)
    assert plan is not None
    assert plan.topic == "thermal-management challenges"
    assert [facet.required_terms for facet in plan.facets] == [
        ["battery", "electric"],
        ["fuel", "cell"],
    ]


def test_normal_query_delegates_unchanged() -> None:
    query = "How are aircraft batteries cooled?"
    base = FakeIndex({query: [_hit("battery", "Battery cooling evidence.", 1)]})
    wrapped = FacetAwareEvidenceIndex(base, FacetRetrievalConfig())
    actual = wrapped.search(query=query, top_k=1)
    assert [hit.chunk.chunk_id for hit in actual] == ["battery"]
    assert base.calls == [(query, 1)]
    assert wrapped.last_used_facets is False


def test_shared_query_balances_facets_and_original() -> None:
    plan = plan_shared_facets(QUERY)
    assert plan is not None
    left = plan.facets[0].search_query
    right = plan.facets[1].search_query
    base = FakeIndex(
        {
            QUERY: [_hit("general", "Electrified aircraft thermal management.", 1)],
            left: [
                _hit("battery-1", "Battery electric aircraft thermal management.", 1),
                _hit("battery-2", "Electric aircraft battery heat rejection.", 2),
            ],
            right: [
                _hit("fuel-1", "Fuel cell aircraft heat rejection.", 1),
                _hit("fuel-2", "Aircraft fuel cell thermal management.", 2),
            ],
        }
    )
    wrapped = FacetAwareEvidenceIndex(
        base,
        FacetRetrievalConfig(facet_search_top_k=5),
    )
    actual = wrapped.search(query=QUERY, top_k=5)
    assert [hit.chunk.chunk_id for hit in actual] == [
        "battery-1",
        "fuel-1",
        "battery-2",
        "fuel-2",
        "general",
    ]
    assert [hit.rank for hit in actual] == [1, 2, 3, 4, 5]
    assert wrapped.last_used_facets is True


def test_missing_semantic_facet_falls_back_to_original() -> None:
    plan = plan_shared_facets(QUERY)
    assert plan is not None
    left = plan.facets[0].search_query
    right = plan.facets[1].search_query
    original = [
        _hit("original-1", "Generic thermal evidence.", 1),
        _hit("original-2", "More generic thermal evidence.", 2),
    ]
    base = FakeIndex(
        {
            QUERY: original,
            left: [_hit("battery", "Battery electric thermal evidence.", 1)],
            right: [_hit("generic", "Generic electric aircraft thermal evidence.", 1)],
        }
    )
    wrapped = FacetAwareEvidenceIndex(
        base,
        FacetRetrievalConfig(facet_search_top_k=5),
    )
    actual = wrapped.search(query=QUERY, top_k=2)
    assert [hit.chunk.chunk_id for hit in actual] == ["original-1", "original-2"]
    assert wrapped.last_used_facets is False


def test_shared_query_records_facet_search_timing() -> None:
    plan = plan_shared_facets(QUERY)
    assert plan is not None

    left = plan.facets[0].search_query
    right = plan.facets[1].search_query

    base = FakeIndex(
        {
            QUERY: [
                _hit(
                    "general",
                    "Electrified aircraft thermal management.",
                    1,
                )
            ],
            left: [
                _hit(
                    "battery-1",
                    "Battery electric aircraft thermal management.",
                    1,
                )
            ],
            right: [
                _hit(
                    "fuel-1",
                    "Fuel cell aircraft heat rejection.",
                    1,
                )
            ],
        }
    )

    wrapped = FacetAwareEvidenceIndex(
        base,
        FacetRetrievalConfig(
            facet_search_top_k=5,
            per_facet_quota=1,
        ),
    )

    wrapped.search(
        query=QUERY,
        top_k=3,
    )

    timings = wrapped.last_timings

    assert timings is not None
    assert timings.search_count == 3
    assert timings.facet_search_count == 2
    assert timings.used_facets is True
    assert timings.base_search_ms >= 0.0
    assert timings.facet_overhead_ms >= 0.0
    assert timings.total_ms >= 0.0

    assert timings.bm25_ms is None
    assert timings.dense_ms is None
    assert timings.hybrid_fusion_ms is None
    assert timings.reranker_scoring_ms is None
