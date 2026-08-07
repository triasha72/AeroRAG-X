"""Provider-telemetry aggregation for grounded-generation evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
    GenerationEvaluationReport,
    GroundedGenerationSystem,
    evaluate_grounded_generation,
)
from aeroragx.generation.grounded import GroundedAnswer


class GenerationQueryProviderTelemetry(BaseModel):
    """Provider telemetry captured for one evaluation query."""

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    expected_answerable: bool
    provider_called: bool
    provider_call_policy_correct: bool | None = None
    attempts: int | None = Field(default=None, ge=1)
    latency_seconds: float | None = Field(default=None, ge=0.0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    prompt_injection_safe: bool | None = None


class ProviderTelemetrySummary(BaseModel):
    """Aggregate remote-provider telemetry for an evaluation run."""

    model_config = ConfigDict(extra="forbid")

    remote_provider: bool
    query_count: int = Field(ge=0)
    provider_call_count: int = Field(ge=0)
    provider_bypass_count: int = Field(ge=0)
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
    mean_latency_seconds: float | None = Field(default=None, ge=0.0)
    p50_latency_seconds: float | None = Field(default=None, ge=0.0)
    p95_latency_seconds: float | None = Field(default=None, ge=0.0)
    mean_input_tokens: float | None = Field(default=None, ge=0.0)
    mean_output_tokens: float | None = Field(default=None, ge=0.0)
    mean_estimated_cost_usd: float | None = Field(default=None, ge=0.0)


class GenerationTelemetryEvaluationReport(BaseModel):
    """Generation evaluation paired with provider telemetry."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"
    generation_report: GenerationEvaluationReport
    provider_summary: ProviderTelemetrySummary
    query_telemetry: list[GenerationQueryProviderTelemetry]


class _CapturingGenerator:
    """Capture answers while preserving the normal generation interface."""

    def __init__(
        self,
        delegate: GroundedGenerationSystem,
    ) -> None:
        self._delegate = delegate
        self.answers: list[GroundedAnswer] = []

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        answer = self._delegate.generate(
            query,
            reranker_model=reranker_model,
        )
        self.answers.append(answer)
        return answer


def evaluate_grounded_generation_with_telemetry(
    *,
    generator: GroundedGenerationSystem,
    queries: Sequence[GenerationEvaluationQuery],
    generation_provider: str,
    generation_model: str,
    reranker_model: str | None = None,
) -> GenerationTelemetryEvaluationReport:
    """Run generation once and aggregate remote-provider telemetry."""

    capturing_generator = _CapturingGenerator(generator)

    generation_report = evaluate_grounded_generation(
        generator=capturing_generator,
        queries=queries,
        generation_provider=generation_provider,
        generation_model=generation_model,
        reranker_model=reranker_model,
    )

    if len(capturing_generator.answers) != len(queries):
        raise RuntimeError("Generation telemetry capture count does not match query count.")

    remote_provider = _is_remote_provider(generation_provider)

    query_telemetry = [
        _build_query_telemetry(
            query=query,
            answer=answer,
            remote_provider=remote_provider,
        )
        for query, answer in zip(
            queries,
            capturing_generator.answers,
            strict=True,
        )
    ]

    return GenerationTelemetryEvaluationReport(
        generation_report=generation_report,
        provider_summary=_summarize_provider_telemetry(
            query_telemetry,
            remote_provider=remote_provider,
        ),
        query_telemetry=query_telemetry,
    )


def write_generation_telemetry_evaluation_report(
    path: Path,
    report: GenerationTelemetryEvaluationReport,
) -> None:
    """Write a formatted generation telemetry report."""

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
    answer: GroundedAnswer,
    remote_provider: bool,
) -> GenerationQueryProviderTelemetry:
    telemetry = (
        answer.retrieval_metadata.provider_telemetry
        if answer.retrieval_metadata is not None
        else None
    )
    usage = telemetry.usage if telemetry is not None else None
    provider_called = telemetry is not None

    return GenerationQueryProviderTelemetry(
        query_id=query.query_id,
        expected_answerable=query.expected_answerable,
        provider_called=provider_called,
        provider_call_policy_correct=(
            provider_called == query.expected_answerable if remote_provider else None
        ),
        attempts=telemetry.attempts if telemetry is not None else None,
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
    remote_provider: bool,
) -> ProviderTelemetrySummary:
    provider_call_count = sum(row.provider_called for row in rows)
    provider_bypass_count = len(rows) - provider_call_count if remote_provider else 0
    provider_call_policy_correct_count = (
        sum(row.provider_call_policy_correct is True for row in rows) if remote_provider else 0
    )
    provider_total_attempts = sum(row.attempts or 0 for row in rows)
    provider_retried_call_count = sum(row.attempts is not None and row.attempts > 1 for row in rows)
    provider_total_input_tokens = sum(row.input_tokens or 0 for row in rows)
    provider_total_output_tokens = sum(row.output_tokens or 0 for row in rows)
    provider_total_tokens = sum(row.total_tokens or 0 for row in rows)
    provider_total_estimated_cost_usd = sum(row.estimated_cost_usd or 0.0 for row in rows)

    latencies = [row.latency_seconds for row in rows if row.latency_seconds is not None]
    input_tokens = [row.input_tokens for row in rows if row.input_tokens is not None]
    output_tokens = [row.output_tokens for row in rows if row.output_tokens is not None]
    costs = [row.estimated_cost_usd for row in rows if row.estimated_cost_usd is not None]

    return ProviderTelemetrySummary(
        remote_provider=remote_provider,
        query_count=len(rows),
        provider_call_count=provider_call_count,
        provider_bypass_count=provider_bypass_count,
        provider_call_policy_correct_count=(provider_call_policy_correct_count),
        provider_total_attempts=provider_total_attempts,
        provider_retried_call_count=provider_retried_call_count,
        provider_total_input_tokens=provider_total_input_tokens,
        provider_total_output_tokens=provider_total_output_tokens,
        provider_total_tokens=provider_total_tokens,
        provider_total_estimated_cost_usd=(provider_total_estimated_cost_usd),
        provider_bypass_rate=(
            _safe_rate(
                provider_bypass_count,
                len(rows),
            )
            if remote_provider
            else None
        ),
        provider_call_policy_accuracy=(
            _safe_rate(
                provider_call_policy_correct_count,
                len(rows),
            )
            if remote_provider
            else None
        ),
        provider_retry_rate=(
            _safe_rate(
                provider_retried_call_count,
                provider_call_count,
            )
            if remote_provider
            else None
        ),
        mean_latency_seconds=_mean(latencies),
        p50_latency_seconds=_percentile(
            latencies,
            0.50,
        ),
        p95_latency_seconds=_percentile(
            latencies,
            0.95,
        ),
        mean_input_tokens=_mean(input_tokens),
        mean_output_tokens=_mean(output_tokens),
        mean_estimated_cost_usd=_mean(costs),
    )


def _is_remote_provider(provider_name: str) -> bool:
    normalized = provider_name.strip().casefold()

    return normalized not in {
        "fake",
        "deterministic",
        "extractive",
    }


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
