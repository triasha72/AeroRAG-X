"""Tests for grounded-generation structural evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
    evaluate_grounded_generation,
    load_generation_evaluation_queries,
    write_generation_evaluation_report,
)
from aeroragx.generation.grounded import (
    AnswerCitation,
    GroundedAnswer,
    GroundedClaim,
    SourceDocument,
)
from aeroragx.generation.structured_provider import (
    ProviderResponseValidationError,
    ProviderTransportError,
)


class FakeGenerator:
    """Return preconfigured answers or errors."""

    def __init__(
        self,
        answers: dict[
            str,
            GroundedAnswer | Exception,
        ],
    ) -> None:
        self._answers = answers

        self.received_queries: list[str] = []

        self.received_models: list[str | None] = []

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        """Return the configured answer or raise."""

        self.received_queries.append(query)

        self.received_models.append(reranker_model)

        configured = self._answers[query]

        if isinstance(
            configured,
            Exception,
        ):
            raise configured

        return configured


def supported_answer(
    query: str,
    *,
    answer_text: str,
) -> GroundedAnswer:
    """Create a structurally valid answer."""

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

    return GroundedAnswer(
        query=query,
        answer=answer_text,
        claims=[
            GroundedClaim(
                claim_id="CL1",
                text=answer_text,
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
        retrieval_metadata=None,
    )


def refusal_answer(
    query: str,
) -> GroundedAnswer:
    """Create a valid evidence refusal."""

    return GroundedAnswer(
        query=query,
        answer=("The retrieved evidence is insufficient to answer this question reliably."),
        claims=[],
        citations=[],
        source_documents=[],
        insufficient_evidence=True,
        retrieval_metadata=None,
    )


def test_load_generation_evaluation_queries(
    tmp_path: Path,
) -> None:
    path = tmp_path / "queries.jsonl"

    path.write_text(
        (
            '{"query_id":"q1",'
            '"query":"battery thermal",'
            '"expected_answerable":true,'
            '"expected_terms":'
            '["battery","thermal"]}\n'
            '{"query_id":"q2",'
            '"query":"unsupported",'
            '"expected_answerable":false,'
            '"expected_terms":[]}\n'
        ),
        encoding="utf-8",
    )

    queries = load_generation_evaluation_queries(path)

    assert len(queries) == 2

    assert queries[0].query_id == "q1"

    assert queries[0].expected_terms == [
        "battery",
        "thermal",
    ]

    assert queries[1].expected_answerable is False


def test_loader_rejects_duplicate_query_ids(
    tmp_path: Path,
) -> None:
    path = tmp_path / "queries.jsonl"

    path.write_text(
        (
            '{"query_id":"q1",'
            '"query":"first",'
            '"expected_answerable":true}\n'
            '{"query_id":"q1",'
            '"query":"second",'
            '"expected_answerable":true}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=("Duplicate generation query ID"),
    ):
        load_generation_evaluation_queries(path)


def test_loader_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "queries.jsonl"

    path.write_text(
        "{invalid json}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSON",
    ):
        load_generation_evaluation_queries(path)


def test_loader_rejects_empty_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "queries.jsonl"

    path.write_text(
        "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        load_generation_evaluation_queries(path)


def test_unanswerable_query_rejects_expected_terms() -> None:
    with pytest.raises(
        ValueError,
        match=("Unanswerable queries must not define expected_terms"),
    ):
        GenerationEvaluationQuery(
            query_id="q1",
            query="unsupported",
            expected_answerable=False,
            expected_terms=["term"],
        )


def test_evaluate_grounded_generation_metrics() -> None:
    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="answerable correct",
            expected_answerable=True,
            expected_terms=[
                "battery",
                "thermal",
            ],
        ),
        GenerationEvaluationQuery(
            query_id="q2",
            query="answerable refused",
            expected_answerable=True,
            expected_terms=["hydrogen"],
        ),
        GenerationEvaluationQuery(
            query_id="q3",
            query="unsupported refused",
            expected_answerable=False,
        ),
        GenerationEvaluationQuery(
            query_id="q4",
            query="unsupported answered",
            expected_answerable=False,
        ),
    ]

    generator = FakeGenerator(
        {
            "answerable correct": (
                supported_answer(
                    "answerable correct",
                    answer_text=("Battery thermal evidence."),
                )
            ),
            "answerable refused": (refusal_answer("answerable refused")),
            "unsupported refused": (refusal_answer("unsupported refused")),
            "unsupported answered": (
                supported_answer(
                    "unsupported answered",
                    answer_text=("An unsupported extracted answer."),
                )
            ),
        }
    )

    report = evaluate_grounded_generation(
        generator=generator,
        queries=queries,
        generation_provider="fake",
        generation_model=("deterministic-grounded-v0"),
        reranker_model="test-reranker",
    )

    assert report.query_count == 4

    assert report.completed_query_count == 4

    assert report.generation_failure_count == 0

    assert report.generation_failure_rate == 0.0

    assert report.answerable_query_count == 2

    assert report.unanswerable_query_count == 2

    assert report.predicted_answerable_count == 2

    assert report.refusal_count == 2

    assert report.correct_answerability_count == 2

    assert report.answerability_accuracy == 0.5

    assert report.answerable_completion_rate == 0.5

    assert report.unsupported_refusal_rate == 0.5

    assert report.total_claim_count == 2

    assert report.cited_claim_count == 2

    assert report.claim_citation_coverage_rate == 1.0

    assert report.citation_reference_validity_rate == 1.0

    assert report.source_document_coverage_rate == 1.0

    assert report.structural_validity_rate == 1.0

    assert report.expected_term_count == 3

    assert report.matched_expected_term_count == 2

    assert report.expected_term_recall == pytest.approx(2 / 3)

    assert generator.received_models == [
        "test-reranker",
        "test-reranker",
        "test-reranker",
        "test-reranker",
    ]


def test_query_results_preserve_answer_text() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="battery question",
        expected_answerable=True,
        expected_terms=["battery"],
    )

    answer = supported_answer(
        "battery question",
        answer_text="Battery evidence.",
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator(
            {
                "battery question": answer,
            }
        ),
        queries=[query],
        generation_provider="fake",
        generation_model="test",
    )

    result = report.query_results[0]

    assert result.query_id == "q1"

    assert result.answer == "Battery evidence."

    assert result.matched_terms == ["battery"]

    assert result.expected_term_recall == 1.0

    assert result.structurally_valid is True

    assert result.generation_failed is False

    assert result.failure_type is None


def test_evaluator_rejects_empty_query_sequence() -> None:
    with pytest.raises(
        ValueError,
        match="at least one query",
    ):
        evaluate_grounded_generation(
            generator=FakeGenerator({}),
            queries=[],
            generation_provider="fake",
            generation_model="test",
        )


def test_evaluator_rejects_duplicate_query_ids() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="same query",
        expected_answerable=False,
    )

    with pytest.raises(
        ValueError,
        match="duplicate IDs",
    ):
        evaluate_grounded_generation(
            generator=FakeGenerator({"same query": (refusal_answer("same query"))}),
            queries=[query, query],
            generation_provider="fake",
            generation_model="test",
        )


def test_default_evaluator_still_raises_generation_errors() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="broken",
        expected_answerable=True,
        expected_terms=["battery"],
    )

    error = ProviderTransportError(
        "invalid model output",
        retryable=False,
    )

    with pytest.raises(
        ProviderTransportError,
        match="invalid model output",
    ):
        evaluate_grounded_generation(
            generator=FakeGenerator(
                {
                    "broken": error,
                }
            ),
            queries=[query],
            generation_provider=("transformers"),
            generation_model=("Qwen/Qwen3-0.6B"),
        )


def test_continue_on_error_records_failure_and_continues() -> None:
    queries = [
        GenerationEvaluationQuery(
            query_id="q1",
            query="broken",
            expected_answerable=True,
            expected_terms=["battery"],
        ),
        GenerationEvaluationQuery(
            query_id="q2",
            query="working",
            expected_answerable=True,
            expected_terms=["thermal"],
        ),
    ]

    generator = FakeGenerator(
        {
            "broken": ProviderTransportError(
                "invalid model output",
                retryable=False,
            ),
            "working": supported_answer(
                "working",
                answer_text=("Thermal evidence."),
            ),
        }
    )

    report = evaluate_grounded_generation(
        generator=generator,
        queries=queries,
        generation_provider=("transformers"),
        generation_model=("Qwen/Qwen3-0.6B"),
        continue_on_error=True,
    )

    assert report.query_count == 2

    assert report.completed_query_count == 1

    assert report.generation_failure_count == 1

    assert report.generation_failure_rate == 0.5

    assert report.correct_answerability_count == 1

    assert report.answerability_accuracy == 0.5

    assert report.completed_answerable_count == 1

    assert report.answerable_completion_rate == 0.5

    assert report.expected_term_count == 2

    assert report.matched_expected_term_count == 1

    assert report.expected_term_recall == 0.5

    assert report.structurally_valid_answer_count == 1

    assert report.structural_validity_rate == 0.5

    failed = report.query_results[0]

    assert failed.generation_failed is True

    assert failed.failure_type == "provider_transport"

    assert failed.predicted_answerable is None

    assert failed.insufficient_evidence is None

    assert failed.answerability_correct is False

    assert failed.answer == ""

    assert failed.matched_terms == []

    assert failed.expected_term_recall == 0.0

    assert failed.structurally_valid is False

    assert generator.received_queries == [
        "broken",
        "working",
    ]


def test_failed_unanswerable_query_is_not_counted_as_refusal() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="broken unsupported",
        expected_answerable=False,
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator(
            {
                "broken unsupported": (
                    ProviderTransportError(
                        "bad JSON",
                        retryable=False,
                    )
                )
            }
        ),
        queries=[query],
        generation_provider=("transformers"),
        generation_model=("Qwen/Qwen3-0.6B"),
        continue_on_error=True,
    )

    assert report.generation_failure_count == 1

    assert report.completed_query_count == 0

    assert report.refusal_count == 0

    assert report.correctly_refused_unanswerable_count == 0

    assert report.unsupported_refusal_rate == 0.0

    assert report.answerability_accuracy == 0.0

    assert report.structural_validity_rate == 0.0


def test_response_validation_error_is_normalized() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="invalid response",
        expected_answerable=True,
        expected_terms=["battery"],
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator(
            {"invalid response": (ProviderResponseValidationError("schema mismatch"))}
        ),
        queries=[query],
        generation_provider=("transformers"),
        generation_model=("Qwen/Qwen3-0.6B"),
        continue_on_error=True,
    )

    result = report.query_results[0]

    assert result.generation_failed is True

    assert result.failure_type == "response_validation"


def test_value_error_is_normalized_as_generation_validation() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="invalid generation",
        expected_answerable=True,
        expected_terms=["battery"],
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator(
            {"invalid generation": (ValueError("generation validation failed"))}
        ),
        queries=[query],
        generation_provider=("transformers"),
        generation_model=("Qwen/Qwen3-0.6B"),
        continue_on_error=True,
    )

    result = report.query_results[0]

    assert result.failure_type == "generation_validation"


def test_runtime_error_is_normalized_as_generation() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="runtime failure",
        expected_answerable=True,
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator({"runtime failure": (RuntimeError("runtime failed"))}),
        queries=[query],
        generation_provider=("transformers"),
        generation_model=("Qwen/Qwen3-0.6B"),
        continue_on_error=True,
    )

    assert report.query_results[0].failure_type == "generation"


def test_unknown_exception_is_normalized() -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="unknown failure",
        expected_answerable=True,
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator({"unknown failure": (KeyError("missing"))}),
        queries=[query],
        generation_provider=("transformers"),
        generation_model=("Qwen/Qwen3-0.6B"),
        continue_on_error=True,
    )

    assert report.query_results[0].failure_type == "unknown"


def test_write_generation_evaluation_report(
    tmp_path: Path,
) -> None:
    query = GenerationEvaluationQuery(
        query_id="q1",
        query="unsupported",
        expected_answerable=False,
    )

    report = evaluate_grounded_generation(
        generator=FakeGenerator({"unsupported": (refusal_answer("unsupported"))}),
        queries=[query],
        generation_provider="fake",
        generation_model="test",
    )

    output = tmp_path / "report.json"

    write_generation_evaluation_report(
        output,
        report,
    )

    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["query_count"] == 1

    assert data["completed_query_count"] == 1

    assert data["generation_failure_count"] == 0

    assert data["generation_failure_rate"] == 0.0

    assert data["unsupported_refusal_rate"] == 1.0

    assert data["query_results"][0]["query_id"] == "q1"
