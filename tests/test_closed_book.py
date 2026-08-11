"""Tests for closed-book generation and evaluation."""

from __future__ import annotations

from collections.abc import Sequence

from aeroragx.generation.closed_book import (
    ClosedBookGenerator,
    evaluate_closed_book,
)
from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
)
from aeroragx.generation.structured_provider import (
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)


class FakeTransport:
    """Deterministic structured-model transport."""

    def __init__(
        self,
        results: Sequence[StructuredModelResult | Exception],
    ) -> None:
        self.results = list(results)
        self.requests: list[StructuredModelRequest] = []

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Return the next queued result."""

        assert timeout_seconds > 0.0

        self.requests.append(request)

        if not self.results:
            raise RuntimeError("No fake result remains.")

        result = self.results.pop(0)

        if isinstance(
            result,
            Exception,
        ):
            raise result

        return result


def make_result(
    *,
    answer: str,
    claims: list[str],
    insufficient_knowledge: bool,
) -> StructuredModelResult:
    """Create one fake structured result."""

    return StructuredModelResult(
        payload={
            "answer": answer,
            "claims": claims,
            "insufficient_knowledge": (insufficient_knowledge),
        },
        request_id=None,
        usage=ProviderUsage(
            input_tokens=100,
            output_tokens=40,
        ),
    )


def test_supported_and_refused_queries_evaluate() -> None:
    """Evaluate one answerable and one unsupported query."""

    transport = FakeTransport(
        [
            make_result(
                answer=("Battery thermal runaway can propagate between cells."),
                claims=[
                    ("Battery thermal runaway can propagate between cells."),
                    ("Heat transfer can contribute to propagation."),
                ],
                insufficient_knowledge=False,
            ),
            make_result(
                answer=("I do not have sufficient reliable knowledge to answer this question."),
                claims=[],
                insufficient_knowledge=True,
            ),
        ]
    )

    generator = ClosedBookGenerator(
        model_name="test-model",
        transport=transport,
    )

    queries = [
        GenerationEvaluationQuery(
            query_id="supported",
            query=("How can battery thermal runaway propagate?"),
            expected_answerable=True,
            expected_terms=[
                "battery",
                "thermal",
                "runaway",
            ],
        ),
        GenerationEvaluationQuery(
            query_id="unsupported",
            query=("What exact price did NASA set for a fictional aircraft?"),
            expected_answerable=False,
            expected_terms=[],
        ),
    ]

    (
        report,
        telemetry,
    ) = evaluate_closed_book(
        generator=generator,
        queries=queries,
        condition="base",
        adapter_enabled=False,
    )

    assert report.query_count == 2
    assert report.completed_query_count == 2
    assert report.generation_failure_count == 0

    assert report.answerability_accuracy == 1.0

    assert report.answerable_completion_rate == 1.0

    assert report.unsupported_refusal_rate == 1.0

    assert report.expected_term_recall == 1.0

    assert report.structural_validity_rate == 1.0

    assert report.answerable_claim_count == 2

    assert report.claims_per_answerable_query == 2.0

    assert telemetry.query_count == 2
    assert telemetry.total_input_tokens == 200
    assert telemetry.total_output_tokens == 80
    assert telemetry.total_tokens == 280


def test_supported_response_requires_claims() -> None:
    """A supported response without claims should fail validation."""

    transport = FakeTransport(
        [
            make_result(
                answer=("The model attempts to answer."),
                claims=[],
                insufficient_knowledge=False,
            )
        ]
    )

    generator = ClosedBookGenerator(
        model_name="test-model",
        transport=transport,
    )

    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="Question",
            expected_answerable=True,
            expected_terms=[
                "answer",
            ],
        )
    ]

    (
        report,
        _,
    ) = evaluate_closed_book(
        generator=generator,
        queries=queries,
        condition="base",
        adapter_enabled=False,
    )

    assert report.generation_failure_count == 1

    assert report.query_results[0].failure_type == "response_validation"

    assert report.query_results[0].structurally_valid is False


def test_closed_book_prompt_has_no_evidence_contract() -> None:
    """The closed-book prompt should not pretend retrieval occurred."""

    transport = FakeTransport(
        [
            make_result(
                answer=("Battery systems require thermal management."),
                claims=[("Battery systems require thermal management.")],
                insufficient_knowledge=False,
            )
        ]
    )

    generator = ClosedBookGenerator(
        model_name="test-model",
        transport=transport,
    )

    generator.generate("Why do batteries need cooling?")

    request = transport.requests[0]

    assert "No retrieved evidence is available" in request.system_prompt

    assert "Do not invent citations" in request.system_prompt

    assert "insufficient_knowledge" in request.system_prompt


def test_insufficient_response_rejects_claims() -> None:
    """A refusal must not carry technical claims."""

    transport = FakeTransport(
        [
            make_result(
                answer=("I do not have enough reliable knowledge."),
                claims=["Unsupported claim."],
                insufficient_knowledge=True,
            )
        ]
    )

    generator = ClosedBookGenerator(
        model_name="test-model",
        transport=transport,
    )

    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="Unsupported question",
            expected_answerable=False,
            expected_terms=[],
        )
    ]

    (
        report,
        _,
    ) = evaluate_closed_book(
        generator=generator,
        queries=queries,
        condition="base",
        adapter_enabled=False,
    )

    assert report.generation_failure_count == 1

    assert report.query_results[0].failure_type == "response_validation"
