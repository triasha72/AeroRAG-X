"""Tests for provider telemetry preserved in grounded answers."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aeroragx.generation.grounded import (
    GenerationConfig,
    GroundedAnswerGenerator,
)
from aeroragx.generation.prompting import (
    ProviderHardeningConfig,
)
from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderResponse,
    StaticGenerationProvider,
)
from aeroragx.generation.structured_provider import (
    ProviderUsage,
    StructuredGenerationProvider,
    StructuredModelRequest,
    StructuredModelResult,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.retrieval.reranker import RerankedSearchHit


def make_config(
    *,
    provider: str,
    model_name: str,
) -> GenerationConfig:
    return GenerationConfig(
        version="0.1",
        provider=provider,
        model_name=model_name,
        evidence_top_k=1,
        minimum_evidence_count=1,
        max_context_characters=3_000,
        max_chunk_characters=3_000,
        max_claims=3,
        require_citations=True,
        allow_insufficient_evidence=True,
        include_retrieval_metadata=True,
    )


def make_hit() -> RerankedSearchHit:
    text = "Battery thermal runaway can propagate between adjacent cells."

    chunk = ChunkRecord(
        chunk_id="100:chunk:00000",
        document_id=100,
        chunk_index=0,
        page_start=1,
        page_end=1,
        page_ids=["100:page:1"],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=max(1, len(text) // 4),
        citation_url=("https://ntrs.nasa.gov/citations/100"),
        source_url=("https://ntrs.nasa.gov/api/citations/100/downloads/report.pdf"),
        document_sha256="a" * 64,
    )

    return RerankedSearchHit(
        rank=1,
        score=9.0,
        chunk=chunk,
        hybrid_rank=1,
        hybrid_score=1.0 / 61.0,
        retrieved_by=["bm25", "dense"],
        bm25_rank=1,
        bm25_score=10.0,
        dense_rank=1,
        dense_score=0.9,
    )


class FakeIndex:
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RerankedSearchHit]:
        del query
        del top_k
        return [make_hit()]


class FakeTransport:
    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        del request
        del timeout_seconds

        return StructuredModelResult(
            payload={
                "answer": ("Thermal runaway can propagate between adjacent cells."),
                "claims": [
                    {
                        "text": ("Thermal runaway can propagate between adjacent cells."),
                        "evidence_ids": ["E1"],
                    }
                ],
                "insufficient_evidence": False,
            },
            request_id="req-telemetry-1",
            usage=ProviderUsage(
                input_tokens=100,
                output_tokens=25,
            ),
        )


class FakeClock:
    def __init__(
        self,
        values: Sequence[float],
    ) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def hardening_config() -> ProviderHardeningConfig:
    return ProviderHardeningConfig(
        version="0.1",
        prompt_version="prompt-v1",
        max_query_characters=2_000,
        max_evidence_characters=12_000,
        evidence_start_marker="<E>",
        evidence_end_marker="</E>",
        prompt_injection_policy="block",
        timeout_seconds=30.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        redact_secrets=True,
    )


def test_structured_provider_telemetry_is_preserved() -> None:
    provider = StructuredGenerationProvider(
        model_name="remote-test-model",
        transport=FakeTransport(),
        config=hardening_config(),
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=6.0,
        clock=FakeClock([10.0, 10.4]),
    )

    generator = GroundedAnswerGenerator(
        index=FakeIndex(),
        provider=provider,
        config=make_config(
            provider="openai-responses",
            model_name="remote-test-model",
        ),
    )

    answer = generator.generate("How can thermal runaway propagate?")

    metadata = answer.retrieval_metadata

    assert metadata is not None
    assert metadata.provider_telemetry is not None

    telemetry = metadata.provider_telemetry

    assert telemetry.model_name == "remote-test-model"
    assert telemetry.prompt_version == "prompt-v1"
    assert telemetry.attempts == 1
    assert telemetry.latency_seconds == pytest.approx(0.4)
    assert telemetry.succeeded is True
    assert telemetry.request_id == "req-telemetry-1"
    assert telemetry.usage is not None
    assert telemetry.usage.input_tokens == 100
    assert telemetry.usage.output_tokens == 25
    assert telemetry.usage.total_tokens == 125
    assert telemetry.estimated_cost_usd == pytest.approx(0.00025)
    assert telemetry.prompt_injection_safe is True
    assert telemetry.prompt_injection_findings == 0
    assert telemetry.error_type is None


def test_local_provider_has_no_remote_telemetry() -> None:
    provider = StaticGenerationProvider(
        ProviderResponse(
            answer="Supported local answer.",
            claims=[
                ProviderClaim(
                    text="Supported local claim.",
                    evidence_ids=["E1"],
                )
            ],
            insufficient_evidence=False,
        )
    )

    generator = GroundedAnswerGenerator(
        index=FakeIndex(),
        provider=provider,
        config=make_config(
            provider="fake",
            model_name="deterministic-grounded-v0",
        ),
    )

    answer = generator.generate("What does the evidence show?")

    metadata = answer.retrieval_metadata

    assert metadata is not None
    assert metadata.provider_telemetry is None
