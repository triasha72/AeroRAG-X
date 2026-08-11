"""Closed-book local-model generation and evaluation."""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
)
from aeroragx.generation.structured_provider import (
    ProviderResponseValidationError,
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelTransport,
)

type ClosedBookCondition = Literal[
    "base",
    "lora",
]

type ClosedBookFailureType = Literal[
    "provider_transport",
    "response_validation",
    "unknown",
]


_CANONICAL_REFUSAL_ANSWER = "I do not have sufficient reliable knowledge to answer this question."


class ClosedBookClaim(BaseModel):
    """One technical claim in a closed-book response."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(
        min_length=1,
    )


class ClosedBookResponse(BaseModel):
    """Structured response for one closed-book query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    answer: str = Field(
        min_length=1,
    )

    claims: list[ClosedBookClaim] = Field(
        default_factory=list,
        max_length=8,
    )

    insufficient_knowledge: bool

    @model_validator(mode="after")
    def validate_response_state(
        self,
    ) -> Self:
        """Enforce supported/refusal response invariants."""

        if any(not claim.text.strip() for claim in self.claims):
            raise ValueError("Closed-book claims must not be blank.")

        normalized_claims = [" ".join(claim.text.casefold().split()) for claim in self.claims]

        if len(normalized_claims) != len(set(normalized_claims)):
            raise ValueError("Closed-book claims must not contain duplicates.")

        if self.insufficient_knowledge:
            if self.claims:
                raise ValueError("An insufficient-knowledge response must not contain claims.")

            return self

        if not self.claims:
            raise ValueError("A supported closed-book response must contain at least one claim.")

        return self


class ClosedBookQueryEvaluation(BaseModel):
    """Evaluation result for one closed-book query."""

    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str

    expected_answerable: bool

    predicted_answerable: bool | None
    answerability_correct: bool

    answer: str

    generation_failed: bool
    failure_type: ClosedBookFailureType | None

    claim_count: int = Field(ge=0)

    expected_terms: list[str]
    matched_terms: list[str]

    expected_term_recall: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    structurally_valid: bool


class ClosedBookEvaluationReport(BaseModel):
    """Aggregate closed-book evaluation report."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.2"

    condition: ClosedBookCondition

    generation_model: str
    adapter_enabled: bool

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

    answerable_claim_count: int = Field(ge=0)

    unanswerable_claim_count: int = Field(ge=0)

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

    expected_term_recall: float = Field(
        ge=0.0,
        le=1.0,
    )

    structural_validity_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    claims_per_answerable_query: float = Field(ge=0.0)

    query_results: list[ClosedBookQueryEvaluation]


class ClosedBookQueryTelemetry(BaseModel):
    """Telemetry for one closed-book model invocation."""

    model_config = ConfigDict(extra="forbid")

    query_id: str

    generation_failed: bool

    latency_seconds: float = Field(ge=0.0)

    input_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    output_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    total_tokens: int | None = Field(
        default=None,
        ge=0,
    )


class ClosedBookTelemetryReport(BaseModel):
    """Aggregate closed-book provider telemetry."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.2"

    condition: ClosedBookCondition
    generation_model: str
    adapter_enabled: bool

    query_count: int = Field(ge=0)

    successful_call_count: int = Field(ge=0)

    total_input_tokens: int = Field(ge=0)

    total_output_tokens: int = Field(ge=0)

    total_tokens: int = Field(ge=0)

    mean_latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )

    p50_latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )

    p95_latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )

    query_telemetry: list[ClosedBookQueryTelemetry]


class ClosedBookGenerator:
    """Generate structured answers without retrieved evidence."""

    prompt_version = "closed-book-json-v0.1"

    def __init__(
        self,
        *,
        model_name: str,
        transport: StructuredModelTransport,
        timeout_seconds: float = 30.0,
    ) -> None:
        normalized_model_name = model_name.strip()

        if not normalized_model_name:
            raise ValueError("model_name must not be blank.")

        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive.")

        self._model_name = normalized_model_name

        self._transport = transport

        self._timeout_seconds = timeout_seconds

    @property
    def model_name(self) -> str:
        """Return the configured model name."""

        return self._model_name

    def generate(
        self,
        query: str,
    ) -> tuple[
        ClosedBookResponse,
        ProviderUsage | None,
    ]:
        """Generate one closed-book response."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query must not be blank.")

        system_prompt = (
            "You are the AeroRAG-X closed-book "
            "evaluation component.\n"
            f"Prompt version: "
            f"{self.prompt_version}.\n\n"
            "No retrieved evidence is available "
            "for this evaluation.\n"
            "Answer only from the model's internal "
            "knowledge.\n\n"
            "Return exactly one JSON object using "
            "this schema:\n"
            "{\n"
            '  "answer": "string",\n'
            '  "claims": [\n'
            "    {\n"
            '      "text": "string"\n'
            "    }\n"
            "  ],\n"
            '  "insufficient_knowledge": false\n'
            "}\n\n"
            "For a refusal, use:\n"
            "{\n"
            '  "answer": "I do not have sufficient '
            'reliable knowledge to answer this question.",\n'
            '  "claims": [],\n'
            '  "insufficient_knowledge": true\n'
            "}\n\n"
            "Rules:\n"
            "1. Use exactly the keys answer, claims, "
            "and insufficient_knowledge.\n"
            "2. Each claims entry must be an object "
            "containing exactly one key: text.\n"
            "3. Do not output evidence_ids, citations, "
            "URLs, page numbers, source metadata, or "
            "insufficient_evidence.\n"
            "4. If reliable knowledge is insufficient, "
            "set insufficient_knowledge=true and return "
            "an empty claims array.\n"
            "5. Otherwise set "
            "insufficient_knowledge=false and return "
            "at least one concise technical claim.\n"
            "6. Keep claims non-redundant.\n"
            "7. Return no markdown, code fences, prefix, "
            "or suffix outside the JSON object."
        )

        request = StructuredModelRequest(
            model_name=self._model_name,
            system_prompt=system_prompt,
            user_prompt=normalized_query,
            response_schema=cast(
                dict[str, object],
                ClosedBookResponse.model_json_schema(),
            ),
        )

        result = self._transport.complete(
            request=request,
            timeout_seconds=(self._timeout_seconds),
        )

        normalized_payload = _normalize_closed_book_payload(result.payload)

        try:
            response = ClosedBookResponse.model_validate(normalized_payload)

        except ValidationError as exc:
            raise ProviderResponseValidationError(
                "Closed-book model output failed the required response contract."
            ) from exc

        return (
            response,
            result.usage,
        )


def _normalize_closed_book_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize only the canonical closed-book refusal shape.

    The model sometimes emits the exact canonical refusal answer
    while either:
    - attaching explanatory claims despite
      insufficient_knowledge=true; or
    - omitting insufficient_knowledge entirely.

    Only the exact canonical refusal sentence is normalized.
    Other malformed or contradictory outputs remain invalid.
    """

    normalized = dict(payload)

    answer = normalized.get("answer")

    if not isinstance(
        answer,
        str,
    ):
        return normalized

    if _normalize_text(answer) != _normalize_text(_CANONICAL_REFUSAL_ANSWER):
        return normalized

    if "insufficient_knowledge" not in normalized:
        normalized["insufficient_knowledge"] = True

    if normalized.get("insufficient_knowledge") is True:
        normalized["claims"] = []

    return normalized


def evaluate_closed_book(
    *,
    generator: ClosedBookGenerator,
    queries: Sequence[GenerationEvaluationQuery],
    condition: ClosedBookCondition,
    adapter_enabled: bool,
) -> tuple[
    ClosedBookEvaluationReport,
    ClosedBookTelemetryReport,
]:
    """Evaluate one closed-book condition."""

    if not queries:
        raise ValueError("Closed-book evaluation requires at least one query.")

    query_ids = [query.query_id for query in queries]

    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Closed-book evaluation queries contain duplicate IDs.")

    results: list[ClosedBookQueryEvaluation] = []

    telemetry: list[ClosedBookQueryTelemetry] = []

    for query in queries:
        started = time.perf_counter()

        usage: ProviderUsage | None = None

        try:
            response, usage = generator.generate(query.query)

        except Exception as error:
            latency = time.perf_counter() - started

            expected_term_recall = None

            if query.expected_terms:
                expected_term_recall = 0.0

            results.append(
                ClosedBookQueryEvaluation(
                    query_id=query.query_id,
                    query=query.query,
                    expected_answerable=(query.expected_answerable),
                    predicted_answerable=None,
                    answerability_correct=False,
                    answer="",
                    generation_failed=True,
                    failure_type=(_failure_type(error)),
                    claim_count=0,
                    expected_terms=(query.expected_terms),
                    matched_terms=[],
                    expected_term_recall=(expected_term_recall),
                    structurally_valid=False,
                )
            )

            telemetry.append(
                ClosedBookQueryTelemetry(
                    query_id=query.query_id,
                    generation_failed=True,
                    latency_seconds=latency,
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                )
            )

            continue

        latency = time.perf_counter() - started

        predicted_answerable = not response.insufficient_knowledge

        normalized_answer = _normalize_text(response.answer)

        matched_terms = [
            term for term in query.expected_terms if (_normalize_text(term) in normalized_answer)
        ]

        expected_term_recall = None

        if query.expected_terms:
            expected_term_recall = _safe_rate(
                len(matched_terms),
                len(query.expected_terms),
            )

        results.append(
            ClosedBookQueryEvaluation(
                query_id=query.query_id,
                query=query.query,
                expected_answerable=(query.expected_answerable),
                predicted_answerable=(predicted_answerable),
                answerability_correct=(predicted_answerable == query.expected_answerable),
                answer=response.answer,
                generation_failed=False,
                failure_type=None,
                claim_count=len(response.claims),
                expected_terms=(query.expected_terms),
                matched_terms=(matched_terms),
                expected_term_recall=(expected_term_recall),
                structurally_valid=True,
            )
        )

        telemetry.append(
            ClosedBookQueryTelemetry(
                query_id=query.query_id,
                generation_failed=False,
                latency_seconds=latency,
                input_tokens=(None if usage is None else usage.input_tokens),
                output_tokens=(None if usage is None else usage.output_tokens),
                total_tokens=(None if usage is None else usage.total_tokens),
            )
        )

    query_count = len(results)

    completed_query_count = sum(not result.generation_failed for result in results)

    generation_failure_count = query_count - completed_query_count

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

    answerable_claim_count = sum(
        result.claim_count for result in results if result.expected_answerable
    )

    unanswerable_claim_count = sum(
        result.claim_count for result in results if not result.expected_answerable
    )

    expected_term_count = sum(len(result.expected_terms) for result in results)

    matched_expected_term_count = sum(len(result.matched_terms) for result in results)

    structurally_valid_answer_count = sum(result.structurally_valid for result in results)

    evaluation_report = ClosedBookEvaluationReport(
        condition=condition,
        generation_model=(generator.model_name),
        adapter_enabled=(adapter_enabled),
        query_count=query_count,
        completed_query_count=(completed_query_count),
        generation_failure_count=(generation_failure_count),
        answerable_query_count=(answerable_query_count),
        unanswerable_query_count=(unanswerable_query_count),
        predicted_answerable_count=(predicted_answerable_count),
        refusal_count=(refusal_count),
        correct_answerability_count=(correct_answerability_count),
        completed_answerable_count=(completed_answerable_count),
        correctly_refused_unanswerable_count=(correctly_refused_unanswerable_count),
        total_claim_count=(total_claim_count),
        answerable_claim_count=(answerable_claim_count),
        unanswerable_claim_count=(unanswerable_claim_count),
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
        claims_per_answerable_query=(
            _safe_rate(
                answerable_claim_count,
                answerable_query_count,
            )
        ),
        query_results=results,
    )

    latencies = [item.latency_seconds for item in telemetry]

    total_input_tokens = sum(item.input_tokens or 0 for item in telemetry)

    total_output_tokens = sum(item.output_tokens or 0 for item in telemetry)

    total_tokens = sum(item.total_tokens or 0 for item in telemetry)

    telemetry_report = ClosedBookTelemetryReport(
        condition=condition,
        generation_model=(generator.model_name),
        adapter_enabled=(adapter_enabled),
        query_count=query_count,
        successful_call_count=(completed_query_count),
        total_input_tokens=(total_input_tokens),
        total_output_tokens=(total_output_tokens),
        total_tokens=(total_tokens),
        mean_latency_seconds=(None if not latencies else (sum(latencies) / len(latencies))),
        p50_latency_seconds=(
            _percentile(
                latencies,
                0.50,
            )
        ),
        p95_latency_seconds=(
            _percentile(
                latencies,
                0.95,
            )
        ),
        query_telemetry=(telemetry),
    )

    return (
        evaluation_report,
        telemetry_report,
    )


def write_closed_book_evaluation_report(
    path: Path,
    report: ClosedBookEvaluationReport,
) -> None:
    """Write one closed-book evaluation report."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def write_closed_book_telemetry_report(
    path: Path,
    report: ClosedBookTelemetryReport,
) -> None:
    """Write one closed-book telemetry report."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def _failure_type(
    error: Exception,
) -> ClosedBookFailureType:
    """Normalize closed-book failures."""

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

    return "unknown"


def _safe_rate(
    numerator: int,
    denominator: int,
) -> float:
    """Return a deterministic bounded rate."""

    if denominator == 0:
        return 1.0

    return numerator / denominator


def _normalize_text(
    value: str,
) -> str:
    """Normalize text exactly like the grounded evaluator."""

    return " ".join(value.casefold().split())


def _percentile(
    values: Sequence[float],
    fraction: float,
) -> float | None:
    """Return a deterministic linearly interpolated percentile."""

    if not values:
        return None

    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must be between 0 and 1.")

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * fraction

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    weight = position - lower

    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight
