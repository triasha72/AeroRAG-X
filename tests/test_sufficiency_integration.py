"""Tests for sufficiency-gated grounded generation."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from aeroragx.generation.adaptive_retrieval import AdaptiveRetrievalConfig
from aeroragx.generation.grounded import GenerationConfig, GroundedAnswerGenerator
from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderResponse,
    StaticGenerationProvider,
)
from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    SufficiencyConfig,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


@dataclass
class FakeIndex:
    """Return fixed reranked hits."""

    hits: list[RerankedSearchHit]

    def search(self, query: str, top_k: int = 10) -> list[RerankedSearchHit]:
        del query
        return self.hits[:top_k]


@dataclass
class QueryAwareFakeIndex:
    """Return deterministic retrieval results keyed by the retrieval query."""

    hits_by_query: dict[str, list[RerankedSearchHit]]
    received_queries: list[str] = field(default_factory=list)

    def search(self, query: str, top_k: int = 10) -> list[RerankedSearchHit]:
        self.received_queries.append(query)
        return self.hits_by_query[query][:top_k]


def make_hit(text: str) -> RerankedSearchHit:
    """Create one reranked NASA-style chunk."""

    chunk = ChunkRecord(
        chunk_id="1001:chunk:00000",
        document_id=1001,
        chunk_index=0,
        page_start=4,
        page_end=5,
        page_ids=["1001:page:4", "1001:page:5"],
        text=text,
        word_count=max(1, len(text.split())),
        character_count=max(1, len(text)),
        token_estimate=max(1, len(text) // 4),
        citation_url="https://ntrs.nasa.gov/citations/1001",
        source_url=("https://ntrs.nasa.gov/api/citations/1001/downloads/report.pdf"),
        document_sha256="a" * 64,
    )

    return RerankedSearchHit(
        rank=1,
        score=8.5,
        chunk=chunk,
        hybrid_rank=1,
        hybrid_score=0.03,
        retrieved_by=["bm25", "dense"],
        bm25_rank=1,
        bm25_score=10.0,
        dense_rank=1,
        dense_score=0.85,
    )


def generation_config(
    *,
    allow_insufficient_evidence: bool = True,
) -> GenerationConfig:
    """Create generation settings for tests."""

    return GenerationConfig(
        version="0.1",
        provider="fake",
        model_name="deterministic-grounded-v0",
        evidence_top_k=5,
        minimum_evidence_count=1,
        max_context_characters=12_000,
        max_chunk_characters=3_000,
        max_claims=6,
        require_citations=True,
        allow_insufficient_evidence=allow_insufficient_evidence,
        include_retrieval_metadata=True,
    )


def assessor() -> EvidenceSufficiencyAssessor:
    """Create the deterministic evidence gate."""

    return EvidenceSufficiencyAssessor(
        SufficiencyConfig(
            version="0.1",
            minimum_evidence_count=1,
            minimum_supported_terms=2,
            minimum_query_term_coverage=0.60,
            minimum_single_evidence_coverage=0.35,
            exact_query_minimum_coverage=0.75,
            require_all_numeric_terms=True,
            require_named_anchors=True,
        )
    )


def adaptive_config() -> AdaptiveRetrievalConfig:
    """Create the Phase 25 two-pass recovery policy."""

    return AdaptiveRetrievalConfig(
        version="0.1",
        maximum_retrieval_passes=2,
        maximum_query_rewrites=1,
        recovery_trigger="insufficient_evidence",
        rewrite_strategy="append_domain_context",
        rewrite_context_terms=["NASA", "aerospace", "technical", "report"],
    )


def provider() -> StaticGenerationProvider:
    """Create one valid cited provider response."""

    return StaticGenerationProvider(
        ProviderResponse(
            answer="Battery thermal runaway can propagate between cells.",
            claims=[
                ProviderClaim(
                    text="Battery thermal runaway can propagate between cells.",
                    evidence_ids=["E1"],
                )
            ],
            insufficient_evidence=False,
        )
    )


def test_rejected_evidence_skips_provider() -> None:
    test_provider = provider()
    generator = GroundedAnswerGenerator(
        index=FakeIndex([make_hit("NASA studied hydrogen aircraft concepts for service in 2035.")]),
        provider=test_provider,
        config=generation_config(),
        sufficiency_assessor=assessor(),
    )

    answer = generator.generate(
        "What was the exact passenger ticket price of NASA's 2035 hydrogen airliner?"
    )

    assert answer.insufficient_evidence is True
    assert test_provider.call_count == 0
    assert answer.retrieval_metadata is not None
    result = answer.retrieval_metadata.evidence_sufficiency
    assert result is not None
    assert result.sufficient is False


def test_supported_evidence_calls_provider() -> None:
    test_provider = provider()
    generator = GroundedAnswerGenerator(
        index=FakeIndex(
            [
                make_hit(
                    "Battery thermal runaway can propagate between adjacent "
                    "cells in electric aircraft."
                )
            ]
        ),
        provider=test_provider,
        config=generation_config(),
        sufficiency_assessor=assessor(),
    )

    answer = generator.generate("How can battery thermal runaway propagate in electric aircraft?")

    assert answer.insufficient_evidence is False
    assert test_provider.call_count == 1
    assert answer.retrieval_metadata is not None
    result = answer.retrieval_metadata.evidence_sufficiency
    assert result is not None
    assert result.sufficient is True


def test_rejection_raises_when_refusals_are_disabled() -> None:
    generator = GroundedAnswerGenerator(
        index=FakeIndex([make_hit("FAA research covers aircraft battery certification.")]),
        provider=provider(),
        config=generation_config(allow_insufficient_evidence=False),
        sufficiency_assessor=assessor(),
    )

    with pytest.raises(
        ValueError,
        match="Evidence sufficiency assessment failed",
    ):
        generator.generate("Which fictional Zephyr-X battery received FAA certification in 2040?")


def test_adaptive_retrieval_recovers_with_one_rewrite_and_preserves_trace() -> None:
    query = "How can battery thermal runaway propagate in electric aircraft?"
    rewritten_query = f"{query} NASA aerospace technical report"
    index = QueryAwareFakeIndex(
        hits_by_query={
            query: [make_hit("NASA studied hydrogen aircraft concepts for service in 2035.")],
            rewritten_query: [
                make_hit(
                    "Battery thermal runaway can propagate between adjacent "
                    "cells in electric aircraft."
                )
            ],
        }
    )
    test_provider = provider()
    generator = GroundedAnswerGenerator(
        index=index,
        provider=test_provider,
        config=generation_config(),
        sufficiency_assessor=assessor(),
        adaptive_retrieval_config=adaptive_config(),
    )

    answer = generator.generate(query)

    assert answer.query == query
    assert answer.insufficient_evidence is False
    assert test_provider.call_count == 1
    assert index.received_queries == [query, rewritten_query]
    assert answer.retrieval_metadata is not None
    trace = answer.retrieval_metadata.adaptive_retrieval
    assert trace is not None
    assert trace.rewritten_query == rewritten_query
    assert trace.retrieval_terminal_state == "generate"
    assert len(trace.attempts) == 2
    assert trace.attempts[0].assessment.sufficient is False
    assert trace.attempts[1].assessment.sufficient is True
    assert trace.attempts[0].evidence_provenance[0].chunk_id == "1001:chunk:00000"
    assert trace.attempts[1].evidence_provenance[0].chunk_id == "1001:chunk:00000"
    assert answer.stage_timings is not None
    assert answer.stage_timings.retrieval_attempt_count == 2
    assert answer.stage_timings.query_rewrite_count == 1


def test_adaptive_retrieval_refuses_after_a_second_insufficient_pass() -> None:
    query = "What was the exact passenger ticket price of NASA's 2035 hydrogen airliner?"
    rewritten_query = f"{query} NASA aerospace technical report"
    weak_hit = make_hit("NASA studied hydrogen aircraft concepts for service in 2035.")
    index = QueryAwareFakeIndex(
        hits_by_query={
            query: [weak_hit],
            rewritten_query: [weak_hit],
        }
    )
    test_provider = provider()
    generator = GroundedAnswerGenerator(
        index=index,
        provider=test_provider,
        config=generation_config(),
        sufficiency_assessor=assessor(),
        adaptive_retrieval_config=adaptive_config(),
    )

    answer = generator.generate(query)

    assert answer.insufficient_evidence is True
    assert answer.claims == []
    assert answer.citations == []
    assert test_provider.call_count == 0
    assert index.received_queries == [query, rewritten_query]
    assert answer.retrieval_metadata is not None
    trace = answer.retrieval_metadata.adaptive_retrieval
    assert trace is not None
    assert trace.retrieval_terminal_state == "grounded_refusal"
    assert len(trace.attempts) == 2
    assert trace.attempts[-1].assessment.sufficient is False
