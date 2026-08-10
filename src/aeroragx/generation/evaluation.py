"""Deterministic structural evaluation for grounded answers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from aeroragx.generation.grounded import GroundedAnswer
from aeroragx.generation.structured_provider import (
    ProviderResponseValidationError,
    ProviderTransportError,
)

type GenerationFailureType = Literal[
    "provider_transport",
    "response_validation",
    "generation_validation",
    "generation",
    "unknown",
]


class GenerationEvaluationQuery(BaseModel):
    """One answerability-labeled generation query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_answerable: bool
    expected_terms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_expected_terms(self) -> Self:
        """Reject blank or duplicate expected terms."""

        normalized = [_normalize_text(term) for term in self.expected_terms]

        if any(not term for term in normalized):
            raise ValueError("expected_terms must not contain blank values.")

        if len(normalized) != len(set(normalized)):
            raise ValueError("expected_terms must not contain duplicates.")

        if not self.expected_answerable and self.expected_terms:
            raise ValueError("Unanswerable queries must not define expected_terms.")

        return self


class GenerationQueryEvaluation(BaseModel):
    """Evaluation details for one grounded answer."""

    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str
    expected_answerable: bool

    predicted_answerable: bool | None
    answerability_correct: bool
    insufficient_evidence: bool | None

    answer: str

    generation_failed: bool = False
    failure_type: GenerationFailureType | None = None

    claim_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    source_document_count: int = Field(ge=0)

    cited_claim_count: int = Field(ge=0)
    total_citation_reference_count: int = Field(ge=0)
    valid_citation_reference_count: int = Field(ge=0)
    source_backed_citation_count: int = Field(ge=0)

    expected_terms: list[str]
    matched_terms: list[str]

    expected_term_recall: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    structurally_valid: bool


class GenerationEvaluationReport(BaseModel):
    """Aggregate grounded-generation evaluation report."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"

    query_count: int = Field(ge=0)
    completed_query_count: int = Field(ge=0)
    generation_failure_count: int = Field(ge=0)

    answerable_query_count: int = Field(ge=0)
    unanswerable_query_count: int = Field(ge=0)

    predicted_answerable_count: int = Field(ge=0)
    refusal_count: int = Field(ge=0)
    correct_answerability_count: int = Field(ge=0)

    completed_answerable_count: int = Field(ge=0)

    correctly_refused_unanswerable_count: int = Field(ge=0)

    total_claim_count: int = Field(ge=0)
    cited_claim_count: int = Field(ge=0)

    total_citation_reference_count: int = Field(ge=0)

    valid_citation_reference_count: int = Field(ge=0)

    citation_count: int = Field(ge=0)

    source_backed_citation_count: int = Field(ge=0)

    expected_term_count: int = Field(ge=0)

    matched_expected_term_count: int = Field(ge=0)

    structurally_valid_answer_count: int = Field(ge=0)

    generation_failure_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    answerability_accuracy: float = Field(
        ge=0.0,
        le=1.0,
    )

    answerable_completion_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    unsupported_refusal_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    claim_citation_coverage_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    citation_reference_validity_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    source_document_coverage_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    expected_term_recall: float = Field(
        ge=0.0,
        le=1.0,
    )

    structural_validity_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    reranker_model: str | None = None
    generation_provider: str
    generation_model: str

    query_results: list[GenerationQueryEvaluation]


class GroundedGenerationSystem(Protocol):
    """Generation interface required by the evaluator."""

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        """Generate one grounded answer."""

        ...


def load_generation_evaluation_queries(
    path: Path,
) -> list[GenerationEvaluationQuery]:
    """Load answerability-labeled generation queries."""

    queries: list[GenerationEvaluationQuery] = []

    seen_query_ids: set[str] = set()

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        try:
            raw_value = json.loads(line)

        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number} of {path}.") from exc

        try:
            query = GenerationEvaluationQuery.model_validate(raw_value)

        except ValidationError as exc:
            raise ValueError(f"Invalid generation query on line {line_number} of {path}.") from exc

        if query.query_id in seen_query_ids:
            raise ValueError(f"Duplicate generation query ID {query.query_id!r}.")

        seen_query_ids.add(query.query_id)

        queries.append(query)

    if not queries:
        raise ValueError("Generation evaluation query file must not be empty.")

    return queries


def evaluate_grounded_generation(
    *,
    generator: GroundedGenerationSystem,
    queries: Sequence[GenerationEvaluationQuery],
    generation_provider: str,
    generation_model: str,
    reranker_model: str | None = None,
    continue_on_error: bool = False,
) -> GenerationEvaluationReport:
    """Evaluate answerability, citations, and structure."""

    if not queries:
        raise ValueError("Generation evaluation requires at least one query.")

    query_ids = [query.query_id for query in queries]

    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Generation evaluation queries contain duplicate IDs.")

    results: list[GenerationQueryEvaluation] = []

    for query in queries:
        try:
            answer = generator.generate(
                query.query,
                reranker_model=reranker_model,
            )

        except Exception as error:
            if not continue_on_error:
                raise

            results.append(
                _failed_query_evaluation(
                    query=query,
                    error=error,
                )
            )

            continue

        results.append(
            _evaluate_one_query(
                query=query,
                answer=answer,
            )
        )

    query_count = len(results)

    completed_query_count = sum(not result.generation_failed for result in results)

    generation_failure_count = sum(result.generation_failed for result in results)

    answerable_query_count = sum(result.expected_answerable for result in results)

    unanswerable_query_count = query_count - answerable_query_count

    predicted_answerable_count = sum(result.predicted_answerable is True for result in results)

    refusal_count = sum(
        (not result.generation_failed and result.predicted_answerable is False)
        for result in results
    )

    correct_answerability_count = sum(result.answerability_correct for result in results)

    completed_answerable_count = sum(
        (
            not result.generation_failed
            and result.expected_answerable
            and result.predicted_answerable is True
        )
        for result in results
    )

    correctly_refused_unanswerable_count = sum(
        (
            not result.generation_failed
            and not result.expected_answerable
            and result.predicted_answerable is False
        )
        for result in results
    )

    total_claim_count = sum(result.claim_count for result in results)

    cited_claim_count = sum(result.cited_claim_count for result in results)

    total_citation_reference_count = sum(
        result.total_citation_reference_count for result in results
    )

    valid_citation_reference_count = sum(
        result.valid_citation_reference_count for result in results
    )

    citation_count = sum(result.citation_count for result in results)

    source_backed_citation_count = sum(result.source_backed_citation_count for result in results)

    expected_term_count = sum(len(result.expected_terms) for result in results)

    matched_expected_term_count = sum(len(result.matched_terms) for result in results)

    structurally_valid_answer_count = sum(result.structurally_valid for result in results)

    return GenerationEvaluationReport(
        query_count=query_count,
        completed_query_count=(completed_query_count),
        generation_failure_count=(generation_failure_count),
        answerable_query_count=(answerable_query_count),
        unanswerable_query_count=(unanswerable_query_count),
        predicted_answerable_count=(predicted_answerable_count),
        refusal_count=refusal_count,
        correct_answerability_count=(correct_answerability_count),
        completed_answerable_count=(completed_answerable_count),
        correctly_refused_unanswerable_count=(correctly_refused_unanswerable_count),
        total_claim_count=(total_claim_count),
        cited_claim_count=(cited_claim_count),
        total_citation_reference_count=(total_citation_reference_count),
        valid_citation_reference_count=(valid_citation_reference_count),
        citation_count=citation_count,
        source_backed_citation_count=(source_backed_citation_count),
        expected_term_count=(expected_term_count),
        matched_expected_term_count=(matched_expected_term_count),
        structurally_valid_answer_count=(structurally_valid_answer_count),
        generation_failure_rate=(
            _safe_rate(
                generation_failure_count,
                query_count,
            )
        ),
        answerability_accuracy=(
            _safe_rate(
                correct_answerability_count,
                query_count,
            )
        ),
        answerable_completion_rate=(
            _safe_rate(
                completed_answerable_count,
                answerable_query_count,
            )
        ),
        unsupported_refusal_rate=(
            _safe_rate(
                correctly_refused_unanswerable_count,
                unanswerable_query_count,
            )
        ),
        claim_citation_coverage_rate=(
            _safe_rate(
                cited_claim_count,
                total_claim_count,
            )
        ),
        citation_reference_validity_rate=(
            _safe_rate(
                valid_citation_reference_count,
                total_citation_reference_count,
            )
        ),
        source_document_coverage_rate=(
            _safe_rate(
                source_backed_citation_count,
                citation_count,
            )
        ),
        expected_term_recall=(
            _safe_rate(
                matched_expected_term_count,
                expected_term_count,
            )
        ),
        structural_validity_rate=(
            _safe_rate(
                structurally_valid_answer_count,
                query_count,
            )
        ),
        reranker_model=reranker_model,
        generation_provider=(generation_provider),
        generation_model=generation_model,
        query_results=results,
    )


def write_generation_evaluation_report(
    path: Path,
    report: GenerationEvaluationReport,
) -> None:
    """Write a formatted generation report."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def _evaluate_one_query(
    *,
    query: GenerationEvaluationQuery,
    answer: GroundedAnswer,
) -> GenerationQueryEvaluation:
    """Evaluate one successfully generated answer."""

    predicted_answerable = not answer.insufficient_evidence

    answerability_correct = predicted_answerable == query.expected_answerable

    valid_citation_ids = {citation.citation_id for citation in answer.citations}

    citation_references = [
        citation_id for claim in answer.claims for citation_id in claim.citation_ids
    ]

    valid_citation_reference_count = sum(
        citation_id in valid_citation_ids for citation_id in citation_references
    )

    cited_claim_count = sum(bool(claim.citation_ids) for claim in answer.claims)

    source_by_document = {source.document_id: source for source in answer.source_documents}

    source_backed_citation_count = 0

    for citation in answer.citations:
        source = source_by_document.get(citation.document_id)

        if source is None:
            continue

        if citation.chunk_id not in source.chunk_ids:
            continue

        page_range = (
            str(citation.page_start)
            if (citation.page_start == citation.page_end)
            else (f"{citation.page_start}-{citation.page_end}")
        )

        if page_range not in source.page_ranges:
            continue

        source_backed_citation_count += 1

    normalized_answer = _normalize_text(answer.answer)

    matched_terms = [
        term for term in query.expected_terms if (_normalize_text(term) in normalized_answer)
    ]

    expected_term_recall = None

    if query.expected_terms:
        expected_term_recall = _safe_rate(
            len(matched_terms),
            len(query.expected_terms),
        )

    structurally_valid = _is_structurally_valid(
        answer=answer,
        cited_claim_count=(cited_claim_count),
        valid_citation_reference_count=(valid_citation_reference_count),
        total_citation_reference_count=(len(citation_references)),
        source_backed_citation_count=(source_backed_citation_count),
    )

    return GenerationQueryEvaluation(
        query_id=query.query_id,
        query=query.query,
        expected_answerable=(query.expected_answerable),
        predicted_answerable=(predicted_answerable),
        answerability_correct=(answerability_correct),
        insufficient_evidence=(answer.insufficient_evidence),
        answer=answer.answer,
        generation_failed=False,
        failure_type=None,
        claim_count=len(answer.claims),
        citation_count=(len(answer.citations)),
        source_document_count=(len(answer.source_documents)),
        cited_claim_count=(cited_claim_count),
        total_citation_reference_count=(len(citation_references)),
        valid_citation_reference_count=(valid_citation_reference_count),
        source_backed_citation_count=(source_backed_citation_count),
        expected_terms=(query.expected_terms),
        matched_terms=matched_terms,
        expected_term_recall=(expected_term_recall),
        structurally_valid=(structurally_valid),
    )


def _failed_query_evaluation(
    *,
    query: GenerationEvaluationQuery,
    error: Exception,
) -> GenerationQueryEvaluation:
    """Create a deterministic failed-query result."""

    expected_term_recall = None

    if query.expected_terms:
        expected_term_recall = 0.0

    return GenerationQueryEvaluation(
        query_id=query.query_id,
        query=query.query,
        expected_answerable=(query.expected_answerable),
        predicted_answerable=None,
        answerability_correct=False,
        insufficient_evidence=None,
        answer="",
        generation_failed=True,
        failure_type=(_normalize_generation_failure(error)),
        claim_count=0,
        citation_count=0,
        source_document_count=0,
        cited_claim_count=0,
        total_citation_reference_count=0,
        valid_citation_reference_count=0,
        source_backed_citation_count=0,
        expected_terms=(query.expected_terms),
        matched_terms=[],
        expected_term_recall=(expected_term_recall),
        structurally_valid=False,
    )


def _normalize_generation_failure(
    error: Exception,
) -> GenerationFailureType:
    """Map exceptions to stable benchmark categories."""

    if isinstance(
        error,
        ProviderTransportError,
    ):
        return "provider_transport"

    if isinstance(
        error,
        ProviderResponseValidationError,
    ):
        return "response_validation"

    if isinstance(
        error,
        ValueError,
    ):
        return "generation_validation"

    if isinstance(
        error,
        RuntimeError,
    ):
        return "generation"

    return "unknown"


def _is_structurally_valid(
    *,
    answer: GroundedAnswer,
    cited_claim_count: int,
    valid_citation_reference_count: int,
    total_citation_reference_count: int,
    source_backed_citation_count: int,
) -> bool:
    """Check citation and refusal structure."""

    if answer.insufficient_evidence:
        return not answer.claims and not answer.citations and not answer.source_documents

    return (
        bool(answer.claims)
        and (cited_claim_count == len(answer.claims))
        and (valid_citation_reference_count == total_citation_reference_count)
        and (source_backed_citation_count == len(answer.citations))
    )


def _safe_rate(
    numerator: int,
    denominator: int,
) -> float:
    """Return a bounded deterministic rate."""

    if denominator == 0:
        return 1.0

    return numerator / denominator


def _normalize_text(
    value: str,
) -> str:
    """Normalize text for term matching."""

    return " ".join(value.casefold().split())
