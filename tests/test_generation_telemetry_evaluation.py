"""Tests for generation provider telemetry evaluation."""

from __future__ import annotations

import pytest

from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
)
from aeroragx.generation.grounded import (
    AnswerCitation,
    GroundedAnswer,
    GroundedClaim,
    RetrievalMetadata,
    SourceDocument,
)
from aeroragx.generation.structured_provider import (
    ProviderTelemetry,
    ProviderTransportError,
    ProviderUsage,
)
from aeroragx.generation.telemetry_evaluation import (
    evaluate_grounded_generation_with_telemetry,
)


class FakeGenerator:
    """Return configured answers or errors."""

    def __init__(
        self,
        answers: dict[
            str,
            GroundedAnswer | Exception,
        ],
    ) -> None:
        self._answers = answers

        self.received_queries: list[str] = []

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        del reranker_model

        self.received_queries.append(query)

        configured = self._answers[query]

        if isinstance(
            configured,
            Exception,
        ):
            raise configured

        return configured


def supported_answer(
    *,
    query: str,
    latency_seconds: float,
    attempts: int,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_usd: float,
    generation_provider: str = ("openai-responses"),
    generation_model: str = "gpt-test",
) -> GroundedAnswer:
    citation = AnswerCitation(
        citation_id="C1",
        evidence_id="E1",
        chunk_id="1001:chunk:00000",
        document_id=1001,
        page_start=4,
        page_end=5,
        citation_url=("https://ntrs.nasa.gov/citations/1001"),
        source_url=("https://ntrs.nasa.gov/api/citations/1001/downloads/report.pdf"),
        document_sha256="a" * 64,
        reranker_rank=1,
    )

    telemetry = ProviderTelemetry(
        model_name=generation_model,
        prompt_version="prompt-v1",
        attempts=attempts,
        latency_seconds=(latency_seconds),
        succeeded=True,
        request_id="req-test",
        usage=ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        estimated_cost_usd=(estimated_cost_usd),
        prompt_injection_safe=True,
        prompt_injection_findings=0,
        error_type=None,
    )

    return GroundedAnswer(
        query=query,
        answer=("Battery thermal evidence."),
        claims=[
            GroundedClaim(
                claim_id="CL1",
                text=("Battery thermal evidence."),
                citation_ids=["C1"],
            )
        ],
        citations=[citation],
        source_documents=[
            SourceDocument(
                document_id=1001,
                citation_url=(citation.citation_url),
                source_url=(citation.source_url),
                page_ranges=["4-5"],
                chunk_ids=[citation.chunk_id],
            )
        ],
        insufficient_evidence=False,
        retrieval_metadata=RetrievalMetadata(
            retriever=("hybrid+reranker"),
            requested_evidence_top_k=5,
            returned_evidence_count=5,
            used_evidence_count=1,
            reranker_model=("test-reranker"),
            generation_provider=(generation_provider),
            generation_model=(generation_model),
            evidence_sufficiency=None,
            provider_telemetry=telemetry,
        ),
    )


def refusal_answer(
    query: str,
    *,
    generation_provider: str = ("openai-responses"),
    generation_model: str = "gpt-test",
) -> GroundedAnswer:
    return GroundedAnswer(
        query=query,
        answer=("The retrieved evidence is insufficient to answer this question reliably."),
        claims=[],
        citations=[],
        source_documents=[],
        insufficient_evidence=True,
        retrieval_metadata=RetrievalMetadata(
            retriever=("hybrid+reranker"),
            requested_evidence_top_k=5,
            returned_evidence_count=5,
            used_evidence_count=5,
            reranker_model=("test-reranker"),
            generation_provider=(generation_provider),
            generation_model=(generation_model),
            evidence_sufficiency=None,
            provider_telemetry=None,
        ),
    )


def test_remote_provider_telemetry_is_aggregated() -> None:
    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="answerable",
            expected_answerable=True,
            expected_terms=["battery"],
        ),
        GenerationEvaluationQuery(
            query_id="q2",
            query="unsupported",
            expected_answerable=False,
        ),
    ]

    report = evaluate_grounded_generation_with_telemetry(
        generator=FakeGenerator(
            {
                "answerable": (
                    supported_answer(
                        query="answerable",
                        latency_seconds=3.0,
                        attempts=2,
                        input_tokens=100,
                        output_tokens=20,
                        estimated_cost_usd=(0.00022),
                    )
                ),
                "unsupported": (refusal_answer("unsupported")),
            }
        ),
        queries=queries,
        generation_provider=("openai-responses"),
        generation_model=("gpt-test"),
        reranker_model=("test-reranker"),
    )

    summary = report.provider_summary

    assert summary.provider_kind == "remote"

    assert summary.telemetry_expected is True

    assert summary.remote_provider is True

    assert summary.provider_call_count == 1

    assert summary.provider_bypass_count == 1

    assert summary.provider_call_unknown_count == 0

    assert summary.provider_call_policy_evaluated_count == 2

    assert summary.provider_call_policy_correct_count == 2

    assert summary.provider_bypass_rate == 0.5

    assert summary.provider_call_policy_accuracy == 1.0

    assert summary.provider_total_attempts == 2

    assert summary.provider_retried_call_count == 1

    assert summary.provider_retry_rate == 1.0

    assert summary.provider_total_input_tokens == 100

    assert summary.provider_total_output_tokens == 20

    assert summary.provider_total_tokens == 120

    assert summary.provider_total_estimated_cost_usd == pytest.approx(0.00022)

    assert summary.mean_latency_seconds == 3.0

    assert summary.p50_latency_seconds == 3.0

    assert summary.p95_latency_seconds == 3.0

    first = report.query_telemetry[0]
    second = report.query_telemetry[1]

    assert first.provider_called is True

    assert first.provider_call_policy_correct is True

    assert first.attempts == 2

    assert first.total_tokens == 120

    assert first.prompt_injection_safe is True

    assert first.generation_failed is False

    assert second.provider_called is False

    assert second.provider_call_policy_correct is True

    assert second.attempts is None


def test_percentiles_across_two_remote_calls() -> None:
    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="first",
            expected_answerable=True,
        ),
        GenerationEvaluationQuery(
            query_id="q2",
            query="second",
            expected_answerable=True,
        ),
    ]

    report = evaluate_grounded_generation_with_telemetry(
        generator=FakeGenerator(
            {
                "first": (
                    supported_answer(
                        query="first",
                        latency_seconds=1.0,
                        attempts=1,
                        input_tokens=10,
                        output_tokens=2,
                        estimated_cost_usd=(0.00002),
                    )
                ),
                "second": (
                    supported_answer(
                        query="second",
                        latency_seconds=3.0,
                        attempts=1,
                        input_tokens=30,
                        output_tokens=6,
                        estimated_cost_usd=(0.00006),
                    )
                ),
            }
        ),
        queries=queries,
        generation_provider=("openai-responses"),
        generation_model=("gpt-test"),
    )

    summary = report.provider_summary

    assert summary.provider_kind == "remote"

    assert summary.telemetry_expected is True

    assert summary.remote_provider is True

    assert summary.mean_latency_seconds == 2.0

    assert summary.p50_latency_seconds == 2.0

    assert summary.p95_latency_seconds == pytest.approx(2.9)

    assert summary.mean_input_tokens == 20.0

    assert summary.mean_output_tokens == 4.0


def test_deterministic_provider_has_no_provider_policy_metrics() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="local",
        expected_answerable=False,
    )

    report = evaluate_grounded_generation_with_telemetry(
        generator=FakeGenerator(
            {
                "local": GroundedAnswer(
                    query="local",
                    answer=(
                        "The retrieved evidence is insufficient to answer this question reliably."
                    ),
                    claims=[],
                    citations=[],
                    source_documents=[],
                    insufficient_evidence=True,
                    retrieval_metadata=None,
                )
            }
        ),
        queries=[query],
        generation_provider="fake",
        generation_model=("deterministic-grounded-v0"),
    )

    summary = report.provider_summary

    assert summary.provider_kind == "deterministic"

    assert summary.telemetry_expected is False

    assert summary.remote_provider is False

    assert summary.provider_call_count == 0

    assert summary.provider_bypass_count == 0

    assert summary.provider_call_unknown_count == 0

    assert summary.provider_bypass_rate is None

    assert summary.provider_call_policy_accuracy is None

    assert summary.provider_retry_rate is None

    assert summary.mean_latency_seconds is None


def test_transformers_provider_telemetry_is_aggregated() -> None:
    model_name = "Qwen/Qwen3-0.6B"

    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="answerable",
            expected_answerable=True,
            expected_terms=["battery"],
        ),
        GenerationEvaluationQuery(
            query_id="q2",
            query="unsupported",
            expected_answerable=False,
        ),
    ]

    report = evaluate_grounded_generation_with_telemetry(
        generator=FakeGenerator(
            {
                "answerable": (
                    supported_answer(
                        query="answerable",
                        latency_seconds=2.5,
                        attempts=1,
                        input_tokens=120,
                        output_tokens=30,
                        estimated_cost_usd=0.0,
                        generation_provider=("transformers"),
                        generation_model=(model_name),
                    )
                ),
                "unsupported": (
                    refusal_answer(
                        "unsupported",
                        generation_provider=("transformers"),
                        generation_model=(model_name),
                    )
                ),
            }
        ),
        queries=queries,
        generation_provider=("transformers"),
        generation_model=model_name,
        reranker_model=("test-reranker"),
    )

    summary = report.provider_summary

    assert summary.provider_kind == "local_model"

    assert summary.telemetry_expected is True

    assert summary.remote_provider is False

    assert summary.provider_call_count == 1

    assert summary.provider_bypass_count == 1

    assert summary.provider_call_unknown_count == 0

    assert summary.provider_call_policy_evaluated_count == 2

    assert summary.provider_call_policy_correct_count == 2

    assert summary.provider_bypass_rate == 0.5

    assert summary.provider_call_policy_accuracy == 1.0

    assert summary.provider_total_attempts == 1

    assert summary.provider_retried_call_count == 0

    assert summary.provider_retry_rate == 0.0

    assert summary.provider_total_input_tokens == 120

    assert summary.provider_total_output_tokens == 30

    assert summary.provider_total_tokens == 150

    assert summary.provider_total_estimated_cost_usd == 0.0

    assert summary.mean_latency_seconds == 2.5

    assert summary.p50_latency_seconds == 2.5

    assert summary.p95_latency_seconds == 2.5

    assert summary.mean_input_tokens == 120.0

    assert summary.mean_output_tokens == 30.0

    assert summary.mean_estimated_cost_usd == 0.0

    supported = report.query_telemetry[0]

    unsupported = report.query_telemetry[1]

    assert supported.provider_called is True

    assert supported.provider_call_policy_correct is True

    assert supported.attempts == 1

    assert supported.total_tokens == 150

    assert supported.estimated_cost_usd == 0.0

    assert supported.prompt_injection_safe is True

    assert unsupported.provider_called is False

    assert unsupported.provider_call_policy_correct is True

    assert unsupported.attempts is None

    assert unsupported.total_tokens is None

    assert unsupported.estimated_cost_usd is None


def test_transformers_failure_is_recorded_and_evaluation_continues() -> None:
    model_name = "Qwen/Qwen3-0.6B"

    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="broken",
            expected_answerable=True,
            expected_terms=["battery"],
        ),
        GenerationEvaluationQuery(
            query_id="q2",
            query="unsupported",
            expected_answerable=False,
        ),
        GenerationEvaluationQuery(
            query_id="q3",
            query="working",
            expected_answerable=True,
            expected_terms=["battery"],
        ),
    ]

    generator = FakeGenerator(
        {
            "broken": ProviderTransportError(
                "invalid local-model JSON",
                retryable=False,
                diagnostics={
                    "failure_stage": "json_decode",
                    "output_tokens": 384,
                    "output_reached_token_limit": True,
                },
            ),
            "unsupported": refusal_answer(
                "unsupported",
                generation_provider=("transformers"),
                generation_model=(model_name),
            ),
            "working": supported_answer(
                query="working",
                latency_seconds=2.0,
                attempts=1,
                input_tokens=100,
                output_tokens=25,
                estimated_cost_usd=0.0,
                generation_provider=("transformers"),
                generation_model=(model_name),
            ),
        }
    )

    report = evaluate_grounded_generation_with_telemetry(
        generator=generator,
        queries=queries,
        generation_provider=("transformers"),
        generation_model=model_name,
        reranker_model=("test-reranker"),
    )

    generation = report.generation_report

    assert generation.query_count == 3

    assert generation.completed_query_count == 2

    assert generation.generation_failure_count == 1

    assert generation.generation_failure_rate == pytest.approx(1 / 3)

    assert generator.received_queries == [
        "broken",
        "unsupported",
        "working",
    ]

    failed = report.query_telemetry[0]

    assert failed.generation_failed is True

    assert failed.failure_type == "provider_transport"

    assert failed.provider_called is None

    assert failed.provider_call_policy_correct is None

    assert failed.failure_diagnostics == {
        "failure_stage": "json_decode",
        "output_tokens": 384,
        "output_reached_token_limit": True,
    }

    summary = report.provider_summary

    assert summary.provider_kind == "local_model"

    assert summary.provider_call_count == 1

    assert summary.provider_bypass_count == 1

    assert summary.provider_call_unknown_count == 1

    assert summary.provider_call_policy_evaluated_count == 2

    assert summary.provider_call_policy_correct_count == 2

    assert summary.provider_call_policy_accuracy == 1.0

    assert summary.provider_bypass_rate == 0.5

    assert summary.provider_total_input_tokens == 100

    assert summary.provider_total_output_tokens == 25

    assert summary.provider_total_tokens == 125

    assert summary.provider_total_estimated_cost_usd == 0.0


def test_telemetry_evaluation_can_remain_strict() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="broken",
        expected_answerable=True,
    )

    with pytest.raises(
        ProviderTransportError,
        match="strict failure",
    ):
        evaluate_grounded_generation_with_telemetry(
            generator=FakeGenerator(
                {
                    "broken": (
                        ProviderTransportError(
                            "strict failure",
                            retryable=False,
                        )
                    )
                }
            ),
            queries=[query],
            generation_provider=("transformers"),
            generation_model=("Qwen/Qwen3-0.6B"),
            continue_on_error=False,
        )
