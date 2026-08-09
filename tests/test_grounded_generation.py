"""Tests for citation-verified grounded answer generation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic import ValidationError

from aeroragx.generation.facet_retrieval import (
    FacetRetrievalTimings,
)
from aeroragx.generation.grounded import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    GenerationConfig,
    GroundedAnswerGenerator,
    build_generation_evidence,
    load_generation_config,
    write_grounded_answer,
)
from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderResponse,
    StaticGenerationProvider,
)
from aeroragx.observability import (
    create_tracing_runtime,
    use_tracer,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


def make_chunk(
    chunk_id: str,
    document_id: int,
    text: str,
    *,
    page_start: int = 1,
    page_end: int = 1,
) -> ChunkRecord:
    """Create a deterministic retrieval chunk."""

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        page_start=page_start,
        page_end=page_end,
        page_ids=[f"{document_id}:page:{page}" for page in range(page_start, page_end + 1)],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url=(f"https://ntrs.nasa.gov/citations/{document_id}"),
        source_url=(f"https://ntrs.nasa.gov/api/citations/{document_id}/downloads/report.pdf"),
        document_sha256="a" * 64,
    )


def make_hit(
    rank: int,
    *,
    chunk_id: str | None = None,
    document_id: int | None = None,
    text: str | None = None,
    page_start: int = 1,
    page_end: int = 1,
) -> RerankedSearchHit:
    """Create one reranked hit with complete retrieval provenance."""

    resolved_document_id = document_id if document_id is not None else 100 + rank
    resolved_chunk_id = chunk_id if chunk_id is not None else f"{resolved_document_id}:chunk:00000"
    resolved_text = text if text is not None else f"Evidence text for result {rank}."

    return RerankedSearchHit(
        rank=rank,
        score=10.0 - rank,
        chunk=make_chunk(
            resolved_chunk_id,
            resolved_document_id,
            resolved_text,
            page_start=page_start,
            page_end=page_end,
        ),
        hybrid_rank=rank + 1,
        hybrid_score=1.0 / (60 + rank),
        retrieved_by=["bm25", "dense"],
        bm25_rank=rank,
        bm25_score=20.0 - rank,
        dense_rank=rank + 2,
        dense_score=0.9 - rank * 0.01,
    )


class FakeRerankedIndex:
    """Return fixed reranked evidence and record requested search depth."""

    def __init__(
        self,
        hits: Sequence[RerankedSearchHit],
    ) -> None:
        self._hits = list(hits)
        self.queries: list[str] = []
        self.top_ks: list[int] = []

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RerankedSearchHit]:
        """Return at most the requested number of hits."""

        self.queries.append(query)
        self.top_ks.append(top_k)
        return self._hits[:top_k]


class TimedFakeRerankedIndex(FakeRerankedIndex):
    """Return fixed hits plus production-shaped facet timing telemetry."""

    def __init__(
        self,
        hits: Sequence[RerankedSearchHit],
        timings: FacetRetrievalTimings,
    ) -> None:
        super().__init__(hits)
        self._timings = timings

    @property
    def last_timings(self) -> FacetRetrievalTimings:
        """Return deterministic retrieval timing for generation tests."""

        return self._timings.model_copy(deep=True)


def make_config(**updates: object) -> GenerationConfig:
    """Create a validated generation configuration."""

    values: dict[str, object] = {
        "version": "0.1",
        "provider": "fake",
        "model_name": "deterministic-grounded-v0",
        "evidence_top_k": 5,
        "minimum_evidence_count": 1,
        "max_context_characters": 12_000,
        "max_chunk_characters": 3_000,
        "max_claims": 6,
        "require_citations": True,
        "allow_insufficient_evidence": True,
        "include_retrieval_metadata": True,
    }
    values.update(updates)
    return GenerationConfig.model_validate(values)


def make_supported_response() -> ProviderResponse:
    """Create a deterministic two-claim provider response."""

    return ProviderResponse(
        answer=(
            "Thermal runaway can propagate between adjacent cells, "
            "and cooling design affects mitigation."
        ),
        claims=[
            ProviderClaim(
                text=("Thermal runaway can propagate between adjacent battery cells."),
                evidence_ids=["E1"],
            ),
            ProviderClaim(
                text=("Cooling-system design affects mitigation."),
                evidence_ids=["E1", "E2"],
            ),
        ],
        insufficient_evidence=False,
    )


def test_load_generation_config(tmp_path: Path) -> None:
    path = tmp_path / "generation.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            'provider: "fake"\n'
            'model_name: "deterministic-grounded-v0"\n'
            "evidence_top_k: 5\n"
            "minimum_evidence_count: 1\n"
            "max_context_characters: 12000\n"
            "max_chunk_characters: 3000\n"
            "max_claims: 6\n"
            "require_citations: true\n"
            "allow_insufficient_evidence: true\n"
            "include_retrieval_metadata: true\n"
        ),
        encoding="utf-8",
    )

    config = load_generation_config(path)

    assert config.provider == "fake"
    assert config.evidence_top_k == 5
    assert config.require_citations is True


def test_load_generation_config_rejects_non_mapping(
    tmp_path: Path,
) -> None:
    path = tmp_path / "generation.yaml"
    path.write_text("- invalid\n- config\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="must contain a YAML mapping",
    ):
        load_generation_config(path)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"provider": " "}, "at least 1 character"),
        ({"model_name": " "}, "at least 1 character"),
        ({"evidence_top_k": 0}, "greater than or equal to 1"),
        ({"minimum_evidence_count": 0}, "greater than or equal to 1"),
        ({"max_context_characters": 0}, "greater than or equal to 1"),
        ({"max_chunk_characters": 0}, "greater than or equal to 1"),
        ({"max_claims": 0}, "greater than or equal to 1"),
        (
            {
                "evidence_top_k": 2,
                "minimum_evidence_count": 3,
            },
            "must not exceed evidence_top_k",
        ),
        (
            {
                "max_context_characters": 100,
                "max_chunk_characters": 101,
            },
            "must not exceed max_context_characters",
        ),
    ],
)
def test_generation_config_rejects_invalid_values(
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        make_config(**updates)


def test_generation_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GenerationConfig.model_validate(
            {
                **make_config().model_dump(mode="python"),
                "unknown_setting": True,
            }
        )


def test_build_generation_evidence_preserves_provenance() -> None:
    hit = make_hit(
        1,
        page_start=4,
        page_end=6,
    )

    evidence = build_generation_evidence(
        [hit],
        make_config(),
    )[0]

    assert evidence.evidence_id == "E1"
    assert evidence.chunk_id == hit.chunk.chunk_id
    assert evidence.document_id == hit.chunk.document_id
    assert evidence.page_start == 4
    assert evidence.page_end == 6
    assert evidence.citation_url == hit.chunk.citation_url
    assert evidence.source_url == hit.chunk.source_url
    assert evidence.document_sha256 == hit.chunk.document_sha256
    assert evidence.reranker_rank == hit.rank
    assert evidence.reranker_score == hit.score
    assert evidence.hybrid_rank == hit.hybrid_rank
    assert evidence.hybrid_score == hit.hybrid_score
    assert evidence.bm25_rank == hit.bm25_rank
    assert evidence.dense_rank == hit.dense_rank


def test_build_generation_evidence_respects_depth_and_ids() -> None:
    hits = [make_hit(rank) for rank in range(1, 5)]

    evidence = build_generation_evidence(
        hits,
        make_config(evidence_top_k=3),
    )

    assert [item.evidence_id for item in evidence] == [
        "E1",
        "E2",
        "E3",
    ]
    assert len(evidence) == 3


def test_build_generation_evidence_applies_chunk_limit() -> None:
    hit = make_hit(1, text="abcdefghij")

    evidence = build_generation_evidence(
        [hit],
        make_config(
            max_chunk_characters=4,
            max_context_characters=10,
        ),
    )

    assert evidence[0].text == "abcd"


def test_build_generation_evidence_applies_total_budget() -> None:
    hits = [
        make_hit(1, text="abcdef"),
        make_hit(2, text="ghijkl"),
    ]

    evidence = build_generation_evidence(
        hits,
        make_config(
            max_chunk_characters=6,
            max_context_characters=8,
        ),
    )

    assert [item.text for item in evidence] == [
        "abcdef",
        "gh",
    ]


def test_build_generation_evidence_rejects_duplicate_chunks() -> None:
    first = make_hit(1, chunk_id="same")
    second = make_hit(2, chunk_id="same")

    with pytest.raises(
        ValueError,
        match="duplicate chunk IDs",
    ):
        build_generation_evidence(
            [first, second],
            make_config(),
        )


def test_generate_supported_answer_with_authoritative_citations() -> None:
    hits = [make_hit(1), make_hit(2)]
    index = FakeRerankedIndex(hits)
    provider = StaticGenerationProvider(make_supported_response())
    generator = GroundedAnswerGenerator(
        index=index,
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate(
        "How does thermal runaway propagate?",
        reranker_model=("cross-encoder/ms-marco-MiniLM-L6-v2"),
    )

    assert answer.insufficient_evidence is False
    assert [claim.claim_id for claim in answer.claims] == [
        "CL1",
        "CL2",
    ]
    assert answer.claims[0].citation_ids == ["C1"]
    assert answer.claims[1].citation_ids == ["C1", "C2"]
    assert [citation.citation_id for citation in answer.citations] == [
        "C1",
        "C2",
    ]
    assert answer.citations[0].chunk_id == hits[0].chunk.chunk_id
    assert answer.citations[0].citation_url == hits[0].chunk.citation_url
    assert answer.citations[0].reranker_rank == 1
    assert provider.call_count == 1
    assert provider.received_queries == ["How does thermal runaway propagate?"]
    assert [item.evidence_id for item in provider.received_evidence[0]] == ["E1", "E2"]
    assert provider.received_max_claims == [6]
    assert index.top_ks == [5]

    assert answer.retrieval_metadata is not None
    assert answer.retrieval_metadata.returned_evidence_count == 2
    assert answer.retrieval_metadata.used_evidence_count == 2
    assert answer.retrieval_metadata.reranker_model == ("cross-encoder/ms-marco-MiniLM-L6-v2")


def test_source_documents_are_deduplicated() -> None:
    hits = [
        make_hit(
            1,
            document_id=500,
            chunk_id="500:chunk:00000",
            page_start=1,
            page_end=2,
        ),
        make_hit(
            2,
            document_id=500,
            chunk_id="500:chunk:00001",
            page_start=3,
            page_end=3,
        ),
    ]
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Two pieces of evidence support the answer.",
            claims=[
                ProviderClaim(
                    text="The evidence spans multiple pages.",
                    evidence_ids=["E1", "E2"],
                )
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex(hits),
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate("question")

    assert len(answer.source_documents) == 1
    source = answer.source_documents[0]
    assert source.document_id == 500
    assert source.page_ranges == ["1-2", "3"]
    assert source.chunk_ids == [
        "500:chunk:00000",
        "500:chunk:00001",
    ]


def test_unknown_evidence_id_is_rejected() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Unsupported answer.",
            claims=[
                ProviderClaim(
                    text="Unsupported claim.",
                    evidence_ids=["E99"],
                )
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="unknown evidence ID",
    ):
        generator.generate("question")


def test_uncited_claim_is_rejected() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Answer.",
            claims=[
                ProviderClaim(
                    text="Uncited claim.",
                    evidence_ids=[],
                )
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(require_citations=True),
    )

    with pytest.raises(
        ValueError,
        match="must cite at least one evidence ID",
    ):
        generator.generate("question")


def test_duplicate_evidence_ids_in_claim_are_rejected() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Answer.",
            claims=[
                ProviderClaim(
                    text="Duplicated citation.",
                    evidence_ids=["E1", "E1"],
                )
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="duplicate evidence IDs",
    ):
        generator.generate("question")


def test_too_many_claims_are_rejected() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Answer.",
            claims=[
                ProviderClaim(
                    text="Claim one.",
                    evidence_ids=["E1"],
                ),
                ProviderClaim(
                    text="Claim two.",
                    evidence_ids=["E1"],
                ),
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(max_claims=1),
    )

    with pytest.raises(
        ValueError,
        match="more claims than max_claims",
    ):
        generator.generate("question")


def test_empty_retrieval_returns_refusal_without_provider_call() -> None:
    provider = StaticGenerationProvider(make_supported_response())
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([]),
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate("unsupported question")

    assert answer.insufficient_evidence is True
    assert answer.answer == INSUFFICIENT_EVIDENCE_ANSWER
    assert answer.claims == []
    assert answer.citations == []
    assert provider.call_count == 0


def test_below_minimum_evidence_returns_refusal() -> None:
    provider = StaticGenerationProvider(make_supported_response())
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(
            evidence_top_k=3,
            minimum_evidence_count=2,
        ),
    )

    answer = generator.generate("question")

    assert answer.insufficient_evidence is True
    assert provider.call_count == 0


def test_disabled_automatic_refusal_raises() -> None:
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([]),
        provider=StaticGenerationProvider(make_supported_response()),
        config=make_config(allow_insufficient_evidence=False),
    )

    with pytest.raises(
        ValueError,
        match="insufficient-evidence responses are disabled",
    ):
        generator.generate("question")


def test_provider_declared_insufficient_evidence_is_accepted() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer=("The available evidence does not establish the requested value."),
            claims=[],
            insufficient_evidence=True,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate("question")

    assert answer.insufficient_evidence is True
    assert answer.claims == []
    assert answer.citations == []
    assert provider.call_count == 1


def test_insufficient_provider_response_with_claims_is_rejected() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Insufficient.",
            claims=[
                ProviderClaim(
                    text="Contradictory claim.",
                    evidence_ids=["E1"],
                )
            ],
            insufficient_evidence=True,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="must not contain claims",
    ):
        generator.generate("question")


def test_blank_query_is_rejected() -> None:
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=StaticGenerationProvider(make_supported_response()),
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="query must not be blank",
    ):
        generator.generate("   ")


def test_retrieval_metadata_can_be_disabled() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Supported answer.",
            claims=[
                ProviderClaim(
                    text="Supported claim.",
                    evidence_ids=["E1"],
                )
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(include_retrieval_metadata=False),
    )

    answer = generator.generate("question")

    assert answer.retrieval_metadata is None


def test_write_grounded_answer(tmp_path: Path) -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Supported answer.",
            claims=[
                ProviderClaim(
                    text="Supported claim.",
                    evidence_ids=["E1"],
                )
            ],
            insufficient_evidence=False,
        )
    )
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([make_hit(1)]),
        provider=provider,
        config=make_config(),
    )
    answer = generator.generate("question")
    output = tmp_path / "answer.json"

    write_grounded_answer(output, answer)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["query"] == "question"
    assert payload["claims"][0]["claim_id"] == "CL1"
    assert payload["citations"][0]["citation_id"] == "C1"
    assert payload["citations"][0]["citation_url"].startswith("https://ntrs.nasa.gov/citations/")


def test_generate_attaches_internal_stage_timings() -> None:
    hits = [make_hit(1), make_hit(2)]
    provider = StaticGenerationProvider(make_supported_response())
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex(hits),
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate("How does thermal runaway propagate?")
    timings = answer.stage_timings

    assert timings is not None
    assert timings.retrieval_ms >= 0.0
    assert timings.evidence_build_ms >= 0.0
    assert timings.sufficiency_ms is None
    assert timings.provider_stage_ms is not None
    assert timings.provider_stage_ms >= 0.0
    assert timings.citation_resolution_ms is not None
    assert timings.citation_resolution_ms >= 0.0
    assert timings.total_ms >= timings.retrieval_ms

    payload = answer.model_dump(mode="json")
    assert "stage_timings" not in payload
    assert "_stage_timings" not in payload


def test_insufficient_answer_records_bypassed_stage_timings() -> None:
    provider = StaticGenerationProvider(make_supported_response())
    generator = GroundedAnswerGenerator(
        index=FakeRerankedIndex([]),
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate("Unsupported technical question")
    timings = answer.stage_timings

    assert answer.insufficient_evidence is True
    assert provider.call_count == 0
    assert timings is not None
    assert timings.retrieval_ms >= 0.0
    assert timings.evidence_build_ms >= 0.0
    assert timings.sufficiency_ms is None
    assert timings.provider_stage_ms is None
    assert timings.citation_resolution_ms is None


def test_generate_propagates_detailed_retrieval_timings() -> None:
    hits = [make_hit(1), make_hit(2)]
    index = TimedFakeRerankedIndex(
        hits,
        FacetRetrievalTimings(
            search_count=3,
            facet_search_count=2,
            used_facets=True,
            base_search_ms=41.0,
            bm25_ms=5.0,
            dense_ms=12.0,
            hybrid_fusion_ms=1.5,
            reranker_scoring_ms=20.0,
            facet_overhead_ms=2.5,
            total_ms=43.5,
        ),
    )
    provider = StaticGenerationProvider(
        make_supported_response(),
    )
    generator = GroundedAnswerGenerator(
        index=index,
        provider=provider,
        config=make_config(),
    )

    answer = generator.generate(
        "What thermal-management challenges are shared?",
    )
    timings = answer.stage_timings

    assert timings is not None
    assert timings.bm25_ms == 5.0
    assert timings.dense_ms == 12.0
    assert timings.hybrid_fusion_ms == 1.5
    assert timings.reranker_scoring_ms == 20.0
    assert timings.retrieval_search_count == 3
    assert timings.facet_search_count == 2
    assert timings.facet_overhead_ms == 2.5
    assert timings.facet_used is True

    payload = answer.model_dump(mode="json")

    assert "stage_timings" not in payload
    assert "_stage_timings" not in payload


def test_generation_pipeline_emits_stage_spans_without_raw_query() -> None:
    exporter = InMemorySpanExporter()
    tracing_runtime = create_tracing_runtime(
        exporter=exporter,
        environment="test",
        batch_export=False,
    )

    raw_query = "Sensitive aerospace tracing query"
    index = FakeRerankedIndex(
        [
            make_hit(1),
            make_hit(2),
        ]
    )
    provider = StaticGenerationProvider(
        make_supported_response(),
    )
    generator = GroundedAnswerGenerator(
        index=index,
        provider=provider,
        config=make_config(),
    )

    with use_tracer(tracing_runtime.tracer):
        with tracing_runtime.tracer.start_as_current_span(
            "aeroragx.test.parent",
        ) as parent_span:
            answer = generator.generate(
                raw_query,
            )

    assert answer.insufficient_evidence is False

    tracing_runtime.force_flush()
    spans = exporter.get_finished_spans()

    span_by_name = {span.name: span for span in spans}

    expected_names = {
        "aeroragx.retrieval",
        "aeroragx.evidence_build",
        "aeroragx.provider",
        "aeroragx.citation_resolution",
    }

    assert expected_names.issubset(
        span_by_name,
    )

    parent_context = parent_span.get_span_context()

    for name in expected_names:
        span = span_by_name[name]

        assert span.context is not None
        assert span.parent is not None
        assert span.context.trace_id == parent_context.trace_id
        assert span.parent.span_id == parent_context.span_id

    retrieval_span = span_by_name["aeroragx.retrieval"]

    assert retrieval_span.attributes["aeroragx.top_k"] == 5
    assert retrieval_span.attributes["aeroragx.result_count"] == 2

    evidence_span = span_by_name["aeroragx.evidence_build"]

    assert evidence_span.attributes["aeroragx.evidence_count"] == 2

    provider_span = span_by_name["aeroragx.provider"]

    assert provider_span.attributes["aeroragx.provider"] == "fake"
    assert provider_span.attributes["aeroragx.model"] == "deterministic-grounded-v0"

    citation_span = span_by_name["aeroragx.citation_resolution"]

    assert citation_span.attributes["aeroragx.claim_count"] == 2
    assert citation_span.attributes["aeroragx.citation_count"] == 2

    serialized = repr([dict(span.attributes) for span in spans])

    assert raw_query not in serialized

    tracing_runtime.shutdown()
