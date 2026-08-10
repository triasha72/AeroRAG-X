"""Provider-telemetry aggregation for grounded-generation evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
    GenerationEvaluationReport,
    GenerationFailureType,
    GenerationQueryEvaluation,
    GroundedGenerationSystem,
    evaluate_grounded_generation,
)
from aeroragx.generation.grounded import (
    GroundedAnswer,
)

type ProviderKind = Literal[
    "deterministic",
    "remote",
    "local_model",
]


class GenerationQueryProviderTelemetry(BaseModel):
    """Provider telemetry captured for one query."""

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)

    expected_answerable: bool

    generation_failed: bool

    failure_type: GenerationFailureType | None = None

    provider_called: bool | None = None

    provider_call_policy_correct: bool | None = None

    attempts: int | None = Field(
        default=None,
        ge=1,
    )

    latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )

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

    estimated_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
    )

    prompt_injection_safe: bool | None = None


class ProviderTelemetrySummary(BaseModel):
    """Aggregate provider telemetry for a run."""

    model_config = ConfigDict(extra="forbid")

    provider_kind: ProviderKind

    telemetry_expected: bool

    remote_provider: bool

    query_count: int = Field(ge=0)

    provider_call_count: int = Field(ge=0)

    provider_bypass_count: int = Field(ge=0)

    provider_call_unknown_count: int = Field(ge=0)

    provider_call_policy_evaluated_count: int = Field(ge=0)

    provider_call_policy_correct_count: int = Field(ge=0)

    provider_total_attempts: int = Field(ge=0)

    provider_retried_call_count: int = Field(ge=0)

    provider_total_input_tokens: int = Field(ge=0)

    provider_total_output_tokens: int = Field(ge=0)

    provider_total_tokens: int = Field(ge=0)

    provider_total_estimated_cost_usd: float = Field(ge=0.0)

    provider_bypass_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    provider_call_policy_accuracy: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    provider_retry_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

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

    mean_input_tokens: float | None = Field(
        default=None,
        ge=0.0,
    )

    mean_output_tokens: float | None = Field(
        default=None,
        ge=0.0,
    )

    mean_estimated_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
    )


class GenerationTelemetryEvaluationReport(BaseModel):
    """Generation evaluation plus telemetry."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"

    generation_report: GenerationEvaluationReport

    provider_summary: ProviderTelemetrySummary

    query_telemetry: list[GenerationQueryProviderTelemetry]


class _CapturingGenerator:
    """Capture successful and failed generations."""

    def __init__(
        self,
        delegate: GroundedGenerationSystem,
    ) -> None:
        self._delegate = delegate

        self.answers: list[GroundedAnswer | None] = []

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        try:
            answer = self._delegate.generate(
                query,
                reranker_model=reranker_model,
            )

        except Exception:
            self.answers.append(None)
            raise

        self.answers.append(answer)

        return answer


def evaluate_grounded_generation_with_telemetry(
    *,
    generator: GroundedGenerationSystem,
    queries: Sequence[GenerationEvaluationQuery],
    generation_provider: str,
    generation_model: str,
    reranker_model: str | None = None,
    continue_on_error: bool = True,
) -> GenerationTelemetryEvaluationReport:
    """Run generation once and aggregate telemetry."""

    capturing_generator = _CapturingGenerator(generator)

    generation_report = evaluate_grounded_generation(
        generator=capturing_generator,
        queries=queries,
        generation_provider=(generation_provider),
        generation_model=(generation_model),
        reranker_model=(reranker_model),
        continue_on_error=(continue_on_error),
    )

    if len(capturing_generator.answers) != len(queries):
        raise RuntimeError("Generation telemetry capture count does not match query count.")

    if len(generation_report.query_results) != len(queries):
        raise RuntimeError("Generation evaluation result count does not match query count.")

    provider_kind = _provider_kind(generation_provider)

    telemetry_expected = _telemetry_expected(provider_kind)

    query_telemetry = [
        _build_query_telemetry(
            query=query,
            answer=answer,
            evaluation=evaluation,
            telemetry_expected=(telemetry_expected),
        )
        for (
            query,
            answer,
            evaluation,
        ) in zip(
            queries,
            capturing_generator.answers,
            generation_report.query_results,
            strict=True,
        )
    ]

    return GenerationTelemetryEvaluationReport(
        generation_report=(generation_report),
        provider_summary=(
            _summarize_provider_telemetry(
                query_telemetry,
                provider_kind=(provider_kind),
                telemetry_expected=(telemetry_expected),
            )
        ),
        query_telemetry=(query_telemetry),
    )


def write_generation_telemetry_evaluation_report(
    path: Path,
    report: (GenerationTelemetryEvaluationReport),
) -> None:
    """Write a formatted telemetry report."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def _build_query_telemetry(
    *,
    query: GenerationEvaluationQuery,
    answer: GroundedAnswer | None,
    evaluation: GenerationQueryEvaluation,
    telemetry_expected: bool,
) -> GenerationQueryProviderTelemetry:
    if evaluation.generation_failed:
        return GenerationQueryProviderTelemetry(
            query_id=query.query_id,
            expected_answerable=(query.expected_answerable),
            generation_failed=True,
            failure_type=(evaluation.failure_type),
            provider_called=None,
            provider_call_policy_correct=None,
        )

    if answer is None:
        raise RuntimeError("Successful generation result is missing its captured answer.")

    telemetry = (
        answer.retrieval_metadata.provider_telemetry
        if (answer.retrieval_metadata is not None)
        else None
    )

    usage = telemetry.usage if telemetry is not None else None

    provider_called = telemetry is not None

    return GenerationQueryProviderTelemetry(
        query_id=query.query_id,
        expected_answerable=(query.expected_answerable),
        generation_failed=False,
        failure_type=None,
        provider_called=(provider_called),
        provider_call_policy_correct=(
            (provider_called == query.expected_answerable) if telemetry_expected else None
        ),
        attempts=(telemetry.attempts if telemetry is not None else None),
        latency_seconds=(telemetry.latency_seconds if telemetry is not None else None),
        input_tokens=(usage.input_tokens if usage is not None else None),
        output_tokens=(usage.output_tokens if usage is not None else None),
        total_tokens=(usage.total_tokens if usage is not None else None),
        estimated_cost_usd=(telemetry.estimated_cost_usd if telemetry is not None else None),
        prompt_injection_safe=(telemetry.prompt_injection_safe if telemetry is not None else None),
    )


def _summarize_provider_telemetry(
    rows: Sequence[GenerationQueryProviderTelemetry],
    *,
    provider_kind: ProviderKind,
    telemetry_expected: bool,
) -> ProviderTelemetrySummary:
    provider_call_count = sum(row.provider_called is True for row in rows)

    provider_bypass_count = (
        sum(row.provider_called is False for row in rows) if telemetry_expected else 0
    )

    provider_call_unknown_count = (
        sum(row.provider_called is None for row in rows) if telemetry_expected else 0
    )

    policy_rows = [row for row in rows if (row.provider_call_policy_correct is not None)]

    provider_call_policy_evaluated_count = len(policy_rows)

    provider_call_policy_correct_count = sum(
        (row.provider_call_policy_correct is True) for row in policy_rows
    )

    provider_total_attempts = sum(row.attempts or 0 for row in rows)

    provider_retried_call_count = sum(
        (row.attempts is not None and row.attempts > 1) for row in rows
    )

    provider_total_input_tokens = sum(row.input_tokens or 0 for row in rows)

    provider_total_output_tokens = sum(row.output_tokens or 0 for row in rows)

    provider_total_tokens = sum(row.total_tokens or 0 for row in rows)

    provider_total_estimated_cost_usd = sum(row.estimated_cost_usd or 0.0 for row in rows)

    latencies = [row.latency_seconds for row in rows if row.latency_seconds is not None]

    input_tokens = [row.input_tokens for row in rows if row.input_tokens is not None]

    output_tokens = [row.output_tokens for row in rows if row.output_tokens is not None]

    costs = [row.estimated_cost_usd for row in rows if (row.estimated_cost_usd is not None)]

    known_provider_call_count = provider_call_count + provider_bypass_count

    provider_bypass_rate = None

    if telemetry_expected and known_provider_call_count > 0:
        provider_bypass_rate = _safe_rate(
            provider_bypass_count,
            known_provider_call_count,
        )

    provider_call_policy_accuracy = None

    if telemetry_expected and (provider_call_policy_evaluated_count > 0):
        provider_call_policy_accuracy = _safe_rate(
            provider_call_policy_correct_count,
            provider_call_policy_evaluated_count,
        )

    provider_retry_rate = None

    if telemetry_expected:
        provider_retry_rate = _safe_rate(
            provider_retried_call_count,
            provider_call_count,
        )

    return ProviderTelemetrySummary(
        provider_kind=provider_kind,
        telemetry_expected=(telemetry_expected),
        remote_provider=(provider_kind == "remote"),
        query_count=len(rows),
        provider_call_count=(provider_call_count),
        provider_bypass_count=(provider_bypass_count),
        provider_call_unknown_count=(provider_call_unknown_count),
        provider_call_policy_evaluated_count=(provider_call_policy_evaluated_count),
        provider_call_policy_correct_count=(provider_call_policy_correct_count),
        provider_total_attempts=(provider_total_attempts),
        provider_retried_call_count=(provider_retried_call_count),
        provider_total_input_tokens=(provider_total_input_tokens),
        provider_total_output_tokens=(provider_total_output_tokens),
        provider_total_tokens=(provider_total_tokens),
        provider_total_estimated_cost_usd=(provider_total_estimated_cost_usd),
        provider_bypass_rate=(provider_bypass_rate),
        provider_call_policy_accuracy=(provider_call_policy_accuracy),
        provider_retry_rate=(provider_retry_rate),
        mean_latency_seconds=(_mean(latencies)),
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
        mean_input_tokens=(_mean(input_tokens)),
        mean_output_tokens=(_mean(output_tokens)),
        mean_estimated_cost_usd=(_mean(costs)),
    )


def _provider_kind(
    provider_name: str,
) -> ProviderKind:
    normalized = provider_name.strip().casefold()

    if normalized in {
        "fake",
        "deterministic",
        "extractive",
    }:
        return "deterministic"

    if normalized in {
        "transformers",
        "huggingface",
    }:
        return "local_model"

    return "remote"


def _telemetry_expected(
    provider_kind: ProviderKind,
) -> bool:
    return provider_kind != "deterministic"


def _mean(
    values: Sequence[int | float],
) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def _percentile(
    values: Sequence[int | float],
    quantile: float,
) -> float | None:
    if not values:
        return None

    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1.")

    ordered = sorted(float(value) for value in values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * quantile

    lower_index = int(position)

    upper_index = min(
        lower_index + 1,
        len(ordered) - 1,
    )

    fraction = position - lower_index

    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


def _safe_rate(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 1.0

    return numerator / denominator
