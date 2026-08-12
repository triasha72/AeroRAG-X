"""Paired evaluation for one-pass and bounded adaptive retrieval."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.generation.adaptive_retrieval import AdaptiveRetrievalTrace
from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
    GenerationEvaluationReport,
    GenerationQueryEvaluation,
    GroundedGenerationSystem,
    evaluate_grounded_generation,
)
from aeroragx.generation.grounded import GroundedAnswer, RAGStageTimings

type AdaptiveRetrievalConditionName = Literal[
    "single_pass",
    "bounded_adaptive",
]

type AdaptiveRetrievalEvaluationVerdict = Literal[
    "benefit_observed",
    "safe_no_recovery_activated",
    "safe_no_measured_benefit",
    "baseline_parity_failed",
    "integrity_regression",
    "quality_regression",
]


class AdaptiveRetrievalEvaluationConfig(BaseModel):
    """Frozen protocol and paths for the Phase 26 paired study."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(default="0.1", min_length=1)
    phase: Literal[26] = 26

    queries_input: Path
    protected_baseline_report: Path
    phase25_baseline_manifest: Path

    chunks_input: Path
    bm25_config: Path
    dense_config: Path
    hybrid_config: Path
    reranker_config: Path
    generation_config: Path
    sufficiency_config: Path
    facet_retrieval_config: Path | None = None
    adaptive_retrieval_config: Path
    embeddings_input: Path
    metadata_input: Path
    manifest_input: Path

    candidate_top_k: int = Field(default=20, ge=1, le=100)
    evidence_top_k: int = Field(default=5, ge=1, le=100)

    maximum_retrieval_passes: int = Field(default=2, ge=1, le=2)
    maximum_query_rewrites: int = Field(default=1, ge=0, le=1)
    minimum_successful_recoveries: int = Field(default=1, ge=1)

    frozen_inputs: list[Path] = Field(min_length=1)
    pinned_input_sha256: dict[Path, str] = Field(min_length=1)

    inputs_output: Path
    baseline_output: Path
    adaptive_output: Path
    comparison_output: Path
    report_output: Path

    protected_constraints: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_protocol(self) -> Self:
        """Ensure the configured experiment cannot exceed Phase 25 bounds."""

        if self.maximum_query_rewrites != self.maximum_retrieval_passes - 1:
            raise ValueError("maximum_query_rewrites must equal maximum_retrieval_passes - 1.")

        if self.evidence_top_k > self.candidate_top_k:
            raise ValueError("evidence_top_k must not exceed candidate_top_k.")

        required_inputs = {
            self.queries_input,
            self.protected_baseline_report,
            self.phase25_baseline_manifest,
            self.chunks_input,
            self.bm25_config,
            self.dense_config,
            self.generation_config,
            self.sufficiency_config,
            self.hybrid_config,
            self.reranker_config,
            self.adaptive_retrieval_config,
            self.embeddings_input,
            self.metadata_input,
            self.manifest_input,
        }

        if self.facet_retrieval_config is not None:
            required_inputs.add(self.facet_retrieval_config)

        declared_inputs = set(self.frozen_inputs)
        missing = required_inputs - declared_inputs

        if missing:
            formatted = ", ".join(str(path) for path in sorted(missing))
            raise ValueError(f"frozen_inputs is missing required Phase 26 inputs: {formatted}.")

        protected_inputs = {
            self.queries_input,
            self.protected_baseline_report,
            self.phase25_baseline_manifest,
            self.bm25_config,
            self.dense_config,
            self.hybrid_config,
            self.reranker_config,
            self.generation_config,
            self.sufficiency_config,
            self.adaptive_retrieval_config,
            self.manifest_input,
        }

        if self.facet_retrieval_config is not None:
            protected_inputs.add(self.facet_retrieval_config)

        pinned_paths = set(self.pinned_input_sha256)
        missing_pins = protected_inputs - pinned_paths

        if missing_pins:
            formatted = ", ".join(str(path) for path in sorted(missing_pins))
            raise ValueError(
                f"pinned_input_sha256 is missing required Phase 26 inputs: {formatted}."
            )

        malformed_pins = [
            str(path)
            for path, digest in self.pinned_input_sha256.items()
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)
        ]

        if malformed_pins:
            formatted = ", ".join(sorted(malformed_pins))
            raise ValueError(f"pinned_input_sha256 contains invalid SHA-256 values: {formatted}.")

        return self


class ProtectedBaselineParity(BaseModel):
    """Whether the newly executed single-pass condition matches the frozen baseline."""

    model_config = ConfigDict(extra="forbid")

    protected_report_path: str = Field(min_length=1)
    checked_item_count: int = Field(ge=1)
    matched_item_count: int = Field(ge=0)
    mismatched_items: list[str] = Field(default_factory=list)
    matched: bool

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        """Keep summary counts consistent with listed mismatches."""

        if self.matched_item_count > self.checked_item_count:
            raise ValueError("matched_item_count must not exceed checked_item_count.")

        if self.matched != (not self.mismatched_items):
            raise ValueError("matched must agree with mismatched_items.")

        return self


class AdaptiveRetrievalQueryDiagnostics(BaseModel):
    """Retrieval trace and timing facts for one condition and one query."""

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    generation_failed: bool

    total_latency_ms: float = Field(ge=0.0)
    retrieval_ms: float | None = Field(default=None, ge=0.0)
    evidence_build_ms: float | None = Field(default=None, ge=0.0)
    sufficiency_ms: float | None = Field(default=None, ge=0.0)

    retrieval_attempt_count: int | None = Field(default=None, ge=1, le=2)
    query_rewrite_count: int | None = Field(default=None, ge=0, le=1)

    adaptive_trace: AdaptiveRetrievalTrace | None = None
    trace_valid: bool | None = None
    provenance_valid: bool | None = None
    bounds_respected: bool | None = None

    recovery_triggered: bool = False
    recovery_succeeded: bool = False
    recovery_grounded_refusal: bool = False

    @model_validator(mode="after")
    def validate_recovery_state(self) -> Self:
        """Reject impossible recovery summaries."""

        if self.recovery_succeeded and not self.recovery_triggered:
            raise ValueError("recovery_succeeded requires recovery_triggered.")

        if self.recovery_grounded_refusal and not self.recovery_triggered:
            raise ValueError("recovery_grounded_refusal requires recovery_triggered.")

        if self.recovery_succeeded and self.recovery_grounded_refusal:
            raise ValueError("A recovery cannot both generate and refuse.")

        if self.adaptive_trace is None:
            if self.recovery_triggered or self.recovery_succeeded or self.recovery_grounded_refusal:
                raise ValueError("Recovery facts require an adaptive_trace.")

        return self


class AdaptiveRetrievalConditionReport(BaseModel):
    """One side of a paired retrieval evaluation."""

    model_config = ConfigDict(extra="forbid")

    condition: AdaptiveRetrievalConditionName
    generation_report: GenerationEvaluationReport
    query_diagnostics: list[AdaptiveRetrievalQueryDiagnostics]

    total_retrieval_attempts: int = Field(ge=0)
    total_query_rewrites: int = Field(ge=0)
    recovery_trigger_count: int = Field(ge=0)
    successful_recovery_count: int = Field(ge=0)
    recovery_grounded_refusal_count: int = Field(ge=0)

    missing_trace_count: int = Field(ge=0)
    invalid_trace_count: int = Field(ge=0)
    invalid_provenance_count: int = Field(ge=0)
    bound_violation_count: int = Field(ge=0)

    mean_total_latency_ms: float | None = Field(default=None, ge=0.0)
    p50_total_latency_ms: float | None = Field(default=None, ge=0.0)
    p95_total_latency_ms: float | None = Field(default=None, ge=0.0)
    mean_retrieval_ms: float | None = Field(default=None, ge=0.0)
    p50_retrieval_ms: float | None = Field(default=None, ge=0.0)
    p95_retrieval_ms: float | None = Field(default=None, ge=0.0)
    mean_evidence_build_ms: float | None = Field(default=None, ge=0.0)
    mean_retrieval_attempt_count: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_condition_totals(self) -> Self:
        """Ensure report-level counts reflect the query diagnostics."""

        if len(self.query_diagnostics) != self.generation_report.query_count:
            raise ValueError("query_diagnostics count must match generation_report.query_count.")

        if self.successful_recovery_count > self.recovery_trigger_count:
            raise ValueError("successful_recovery_count must not exceed recovery_trigger_count.")

        if self.recovery_grounded_refusal_count > self.recovery_trigger_count:
            raise ValueError(
                "recovery_grounded_refusal_count must not exceed recovery_trigger_count."
            )

        expected_total_retrieval_attempts = sum(
            diagnostic.retrieval_attempt_count or 0
            for diagnostic in self.query_diagnostics
            if not diagnostic.generation_failed
        )
        expected_total_query_rewrites = sum(
            diagnostic.query_rewrite_count or 0
            for diagnostic in self.query_diagnostics
            if not diagnostic.generation_failed
        )
        expected_recovery_triggers = sum(
            diagnostic.recovery_triggered for diagnostic in self.query_diagnostics
        )
        expected_successful_recoveries = sum(
            diagnostic.recovery_succeeded for diagnostic in self.query_diagnostics
        )
        expected_recovery_refusals = sum(
            diagnostic.recovery_grounded_refusal for diagnostic in self.query_diagnostics
        )
        expected_missing_traces = (
            sum(
                not diagnostic.generation_failed and diagnostic.adaptive_trace is None
                for diagnostic in self.query_diagnostics
            )
            if self.condition == "bounded_adaptive"
            else 0
        )
        expected_invalid_traces = sum(
            diagnostic.trace_valid is False for diagnostic in self.query_diagnostics
        )
        expected_invalid_provenance = sum(
            diagnostic.provenance_valid is False for diagnostic in self.query_diagnostics
        )
        expected_bound_violations = sum(
            diagnostic.bounds_respected is False for diagnostic in self.query_diagnostics
        )

        if self.total_retrieval_attempts != expected_total_retrieval_attempts:
            raise ValueError("total_retrieval_attempts does not match query diagnostics.")

        if self.total_query_rewrites != expected_total_query_rewrites:
            raise ValueError("total_query_rewrites does not match query diagnostics.")

        if self.recovery_trigger_count != expected_recovery_triggers:
            raise ValueError("recovery_trigger_count does not match query diagnostics.")

        if self.successful_recovery_count != expected_successful_recoveries:
            raise ValueError("successful_recovery_count does not match query diagnostics.")

        if self.recovery_grounded_refusal_count != expected_recovery_refusals:
            raise ValueError("recovery_grounded_refusal_count does not match query diagnostics.")

        if self.missing_trace_count != expected_missing_traces:
            raise ValueError("missing_trace_count does not match query diagnostics.")

        if self.invalid_trace_count != expected_invalid_traces:
            raise ValueError("invalid_trace_count does not match query diagnostics.")

        if self.invalid_provenance_count != expected_invalid_provenance:
            raise ValueError("invalid_provenance_count does not match query diagnostics.")

        if self.bound_violation_count != expected_bound_violations:
            raise ValueError("bound_violation_count does not match query diagnostics.")

        return self


class AdaptiveRetrievalMetricDeltas(BaseModel):
    """Adaptive-minus-single-pass deltas for Phase 26 metrics."""

    model_config = ConfigDict(extra="forbid")

    generation_failure_rate: float
    answerability_accuracy: float
    answerable_completion_rate: float
    unsupported_refusal_rate: float
    claim_citation_coverage_rate: float
    citation_reference_validity_rate: float
    source_document_coverage_rate: float
    expected_term_recall: float
    structural_validity_rate: float

    mean_total_latency_ms: float | None = None
    p95_total_latency_ms: float | None = None
    mean_retrieval_ms: float | None = None
    p95_retrieval_ms: float | None = None
    mean_evidence_build_ms: float | None = None
    mean_retrieval_attempt_count: float | None = None


class AdaptiveRetrievalSafetyChecks(BaseModel):
    """Predeclared Phase 26 integrity and non-regression checks."""

    model_config = ConfigDict(extra="forbid")

    baseline_parity: bool
    no_generation_failure_increase: bool
    all_adaptive_traces_valid: bool
    all_adaptive_provenance_valid: bool
    all_adaptive_bounds_respected: bool
    claim_citation_coverage_not_decreased: bool
    citation_reference_validity_not_decreased: bool
    source_document_coverage_not_decreased: bool
    structural_validity_not_decreased: bool
    unsupported_refusal_not_decreased: bool
    answerability_accuracy_not_decreased: bool
    answerable_completion_not_decreased: bool
    expected_term_recall_not_decreased: bool
    quality_improvement_observed: bool

    integrity_passed: bool
    quality_non_regression_passed: bool

    @model_validator(mode="after")
    def validate_summary(self) -> Self:
        """Prevent a report from claiming a pass when any check failed."""

        integrity_components = [
            self.no_generation_failure_increase,
            self.all_adaptive_traces_valid,
            self.all_adaptive_provenance_valid,
            self.all_adaptive_bounds_respected,
            self.claim_citation_coverage_not_decreased,
            self.citation_reference_validity_not_decreased,
            self.source_document_coverage_not_decreased,
            self.structural_validity_not_decreased,
            self.unsupported_refusal_not_decreased,
        ]

        if self.integrity_passed != all(integrity_components):
            raise ValueError("integrity_passed must match its component checks.")

        quality_components = [
            self.answerability_accuracy_not_decreased,
            self.answerable_completion_not_decreased,
            self.expected_term_recall_not_decreased,
        ]

        if self.quality_non_regression_passed != all(quality_components):
            raise ValueError("quality_non_regression_passed must match its component checks.")

        return self


class AdaptiveRetrievalEvaluationReport(BaseModel):
    """Complete Phase 26 comparison result for one frozen query set."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"
    phase: Literal[26] = 26
    evaluation: Literal["bounded_adaptive_retrieval"] = "bounded_adaptive_retrieval"

    protected_baseline_parity: ProtectedBaselineParity
    single_pass: AdaptiveRetrievalConditionReport
    bounded_adaptive: AdaptiveRetrievalConditionReport
    deltas: AdaptiveRetrievalMetricDeltas
    safety_checks: AdaptiveRetrievalSafetyChecks

    verdict: AdaptiveRetrievalEvaluationVerdict
    interpretation: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class _CapturedGeneration:
    """One answer object and its complete generator wall-clock duration."""

    answer: GroundedAnswer | None
    total_latency_ms: float


class _TimingCapturingGenerator:
    """Capture answers and wall-clock timings without rerunning a condition."""

    def __init__(
        self,
        delegate: GroundedGenerationSystem,
    ) -> None:
        self._delegate = delegate
        self.captured: list[_CapturedGeneration] = []

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        started_at = perf_counter()

        try:
            answer = self._delegate.generate(
                query,
                reranker_model=reranker_model,
            )

        except Exception:
            self.captured.append(
                _CapturedGeneration(
                    answer=None,
                    total_latency_ms=_elapsed_ms(started_at),
                )
            )
            raise

        self.captured.append(
            _CapturedGeneration(
                answer=answer,
                total_latency_ms=_elapsed_ms(started_at),
            )
        )

        return answer


def load_adaptive_retrieval_evaluation_config(
    path: Path,
) -> AdaptiveRetrievalEvaluationConfig:
    """Load the frozen Phase 26 evaluation protocol."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Adaptive-retrieval evaluation configuration must contain a YAML mapping.")

    return AdaptiveRetrievalEvaluationConfig.model_validate(raw_data)


def evaluate_adaptive_retrieval(
    *,
    single_pass_generator: GroundedGenerationSystem,
    bounded_adaptive_generator: GroundedGenerationSystem,
    queries: Sequence[GenerationEvaluationQuery],
    generation_provider: str,
    generation_model: str,
    protected_baseline: Mapping[str, object],
    config: AdaptiveRetrievalEvaluationConfig,
    reranker_model: str | None = None,
) -> AdaptiveRetrievalEvaluationReport:
    """Run both conditions once and make the predeclared Phase 26 comparison."""

    if not queries:
        raise ValueError("Adaptive-retrieval evaluation requires at least one query.")

    single_pass = _evaluate_condition(
        condition="single_pass",
        generator=single_pass_generator,
        queries=queries,
        generation_provider=generation_provider,
        generation_model=generation_model,
        reranker_model=reranker_model,
        config=config,
    )

    bounded_adaptive = _evaluate_condition(
        condition="bounded_adaptive",
        generator=bounded_adaptive_generator,
        queries=queries,
        generation_provider=generation_provider,
        generation_model=generation_model,
        reranker_model=reranker_model,
        config=config,
    )

    parity = compare_protected_baseline(
        report=single_pass.generation_report,
        protected_baseline=protected_baseline,
        protected_report_path=config.protected_baseline_report,
    )

    deltas = _metric_deltas(
        single_pass=single_pass,
        bounded_adaptive=bounded_adaptive,
    )

    safety_checks = _safety_checks(
        parity=parity,
        single_pass=single_pass,
        bounded_adaptive=bounded_adaptive,
    )

    verdict, interpretation = _verdict(
        parity=parity,
        bounded_adaptive=bounded_adaptive,
        safety_checks=safety_checks,
        config=config,
    )

    return AdaptiveRetrievalEvaluationReport(
        protected_baseline_parity=parity,
        single_pass=single_pass,
        bounded_adaptive=bounded_adaptive,
        deltas=deltas,
        safety_checks=safety_checks,
        verdict=verdict,
        interpretation=interpretation,
    )


def compare_protected_baseline(
    *,
    report: GenerationEvaluationReport,
    protected_baseline: Mapping[str, object],
    protected_report_path: Path,
) -> ProtectedBaselineParity:
    """Compare selected baseline facts with the frozen held-out artifact."""

    metric_names = [
        "query_count",
        "answerable_query_count",
        "unanswerable_query_count",
        "answerability_accuracy",
        "answerable_completion_rate",
        "unsupported_refusal_rate",
        "claim_citation_coverage_rate",
        "citation_reference_validity_rate",
        "source_document_coverage_rate",
        "expected_term_recall",
        "structural_validity_rate",
        "generation_provider",
        "generation_model",
        "reranker_model",
    ]

    mismatched_items: list[str] = []
    matched_item_count = 0

    observed = report.model_dump(mode="python")

    for metric_name in metric_names:
        expected_value = protected_baseline.get(metric_name)
        observed_value = observed.get(metric_name)

        if _equal_metric_values(expected_value, observed_value):
            matched_item_count += 1
        else:
            mismatched_items.append(metric_name)

    expected_query_rows = protected_baseline.get("query_results")
    observed_query_rows = observed["query_results"]
    checked_item_count = len(metric_names)

    if not isinstance(expected_query_rows, list):
        checked_item_count += 1
        mismatched_items.append("query_results")

    elif len(expected_query_rows) != len(observed_query_rows):
        checked_item_count += 1
        mismatched_items.append("query_results.count")

    else:
        for index, expected_row in enumerate(expected_query_rows):
            checked_item_count += 1

            if not isinstance(expected_row, Mapping):
                mismatched_items.append(f"query_results[{index}]")
                continue

            observed_row = observed_query_rows[index]
            expected_query_id = expected_row.get("query_id")
            observed_query_id = observed_row.get("query_id")

            if _equal_metric_values(expected_query_id, observed_query_id):
                matched_item_count += 1
            else:
                mismatched_items.append(f"query_results[{index}].query_id")

            for field_name, expected_value in expected_row.items():
                if field_name == "query_id":
                    continue

                checked_item_count += 1
                observed_value = observed_row.get(field_name)

                if _equal_metric_values(expected_value, observed_value):
                    matched_item_count += 1
                else:
                    mismatched_items.append(f"query_results[{expected_query_id!s}].{field_name}")

    return ProtectedBaselineParity(
        protected_report_path=str(protected_report_path),
        checked_item_count=checked_item_count,
        matched_item_count=matched_item_count,
        mismatched_items=mismatched_items,
        matched=not mismatched_items,
    )


def write_adaptive_retrieval_condition_report(
    path: Path,
    report: AdaptiveRetrievalConditionReport,
) -> None:
    """Write one condition's full Phase 26 output as JSON."""

    _write_json(path, report.model_dump(mode="json"))


def write_adaptive_retrieval_evaluation_report(
    path: Path,
    report: AdaptiveRetrievalEvaluationReport,
) -> None:
    """Write the complete paired Phase 26 comparison as JSON."""

    _write_json(path, report.model_dump(mode="json"))


def render_adaptive_retrieval_evaluation_markdown(
    report: AdaptiveRetrievalEvaluationReport,
) -> str:
    """Render a concise human-readable Phase 26 result without new analysis."""

    baseline = report.single_pass
    adaptive = report.bounded_adaptive
    deltas = report.deltas
    safety = report.safety_checks

    lines = [
        "# Phase 26 bounded adaptive-retrieval evaluation v0.1",
        "",
        "## Scope",
        "",
        (
            "This paired study compares frozen single-pass retrieval with the Phase 25 "
            "bounded adaptive policy on the protected held-out v0.4 query set. "
            "The adaptive policy permits at most two retrieval passes and one "
            "deterministic rewrite."
        ),
        "",
        "## Protocol integrity",
        "",
        f"- Protected baseline parity: **{_pass_fail(report.protected_baseline_parity.matched)}**",
        f"- Adaptive trace validity: **{_pass_fail(safety.all_adaptive_traces_valid)}**",
        f"- Adaptive provenance validity: **{_pass_fail(safety.all_adaptive_provenance_valid)}**",
        f"- Retrieval bounds respected: **{_pass_fail(safety.all_adaptive_bounds_respected)}**",
        f"- Predeclared quality improvement: **{_pass_fail(safety.quality_improvement_observed)}**",
        "",
        "## Generation and grounding metrics",
        "",
        "| Metric | Single pass | Bounded adaptive | Adaptive - single pass |",
        "|---|---:|---:|---:|",
    ]

    metric_rows = [
        (
            "Answerability accuracy",
            baseline.generation_report.answerability_accuracy,
            adaptive.generation_report.answerability_accuracy,
            deltas.answerability_accuracy,
        ),
        (
            "Answerable completion",
            baseline.generation_report.answerable_completion_rate,
            adaptive.generation_report.answerable_completion_rate,
            deltas.answerable_completion_rate,
        ),
        (
            "Unsupported refusal",
            baseline.generation_report.unsupported_refusal_rate,
            adaptive.generation_report.unsupported_refusal_rate,
            deltas.unsupported_refusal_rate,
        ),
        (
            "Citation-reference validity",
            baseline.generation_report.citation_reference_validity_rate,
            adaptive.generation_report.citation_reference_validity_rate,
            deltas.citation_reference_validity_rate,
        ),
        (
            "Structural validity",
            baseline.generation_report.structural_validity_rate,
            adaptive.generation_report.structural_validity_rate,
            deltas.structural_validity_rate,
        ),
        (
            "Expected-term recall",
            baseline.generation_report.expected_term_recall,
            adaptive.generation_report.expected_term_recall,
            deltas.expected_term_recall,
        ),
    ]

    for name, baseline_value, adaptive_value, delta in metric_rows:
        lines.append(
            f"| {name} | {_percentage(baseline_value)} | {_percentage(adaptive_value)} | "
            f"{_signed_percentage(delta)} |"
        )

    lines.extend(
        [
            "",
            "## Adaptive-retrieval behavior",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Recovery triggers | {adaptive.recovery_trigger_count} |",
            f"| Successful recoveries | {adaptive.successful_recovery_count} |",
            f"| Recovery grounded refusals | {adaptive.recovery_grounded_refusal_count} |",
            f"| Total retrieval attempts | {adaptive.total_retrieval_attempts} |",
            f"| Total query rewrites | {adaptive.total_query_rewrites} |",
            "",
            "## Latency",
            "",
            "| Metric | Single pass | Bounded adaptive | Adaptive - single pass |",
            "|---|---:|---:|---:|",
            (
                f"| Mean total latency | {_milliseconds(baseline.mean_total_latency_ms)} | "
                f"{_milliseconds(adaptive.mean_total_latency_ms)} | "
                f"{_signed_milliseconds(deltas.mean_total_latency_ms)} |"
            ),
            (
                f"| P95 total latency | {_milliseconds(baseline.p95_total_latency_ms)} | "
                f"{_milliseconds(adaptive.p95_total_latency_ms)} | "
                f"{_signed_milliseconds(deltas.p95_total_latency_ms)} |"
            ),
            (
                f"| Mean retrieval latency | {_milliseconds(baseline.mean_retrieval_ms)} | "
                f"{_milliseconds(adaptive.mean_retrieval_ms)} | "
                f"{_signed_milliseconds(deltas.mean_retrieval_ms)} |"
            ),
            "",
            "## Decision",
            "",
            f"**Verdict: `{report.verdict}`**",
            "",
            report.interpretation,
            "",
            "## Guardrails",
            "",
            "- The protected held-out query set, labels, retrieval settings, "
            "sufficiency settings, and decision rules were not tuned after observing this run.",
            "- A successful recovery means the first assessment was insufficient and "
            "the second assessment was sufficient.",
            "- Results report this fixed policy; they do not establish universal "
            "retrieval quality.",
            "",
        ]
    )

    return "\n".join(lines)


def write_adaptive_retrieval_evaluation_markdown(
    path: Path,
    report: AdaptiveRetrievalEvaluationReport,
) -> None:
    """Write the Phase 26 human-readable evaluation report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_adaptive_retrieval_evaluation_markdown(report),
        encoding="utf-8",
    )


def _evaluate_condition(
    *,
    condition: AdaptiveRetrievalConditionName,
    generator: GroundedGenerationSystem,
    queries: Sequence[GenerationEvaluationQuery],
    generation_provider: str,
    generation_model: str,
    reranker_model: str | None,
    config: AdaptiveRetrievalEvaluationConfig,
) -> AdaptiveRetrievalConditionReport:
    """Run a condition exactly once per query and retain diagnostics."""

    capturing_generator = _TimingCapturingGenerator(generator)

    generation_report = evaluate_grounded_generation(
        generator=capturing_generator,
        queries=queries,
        generation_provider=generation_provider,
        generation_model=generation_model,
        reranker_model=reranker_model,
        continue_on_error=True,
    )

    if len(capturing_generator.captured) != len(queries):
        raise RuntimeError("Captured generation count does not match query count.")

    if len(generation_report.query_results) != len(queries):
        raise RuntimeError("Generation evaluation result count does not match query count.")

    query_diagnostics = [
        _query_diagnostics(
            condition=condition,
            evaluation=evaluation,
            captured=captured,
            config=config,
        )
        for evaluation, captured in zip(
            generation_report.query_results,
            capturing_generator.captured,
            strict=True,
        )
    ]

    timing_rows = [
        diagnostic for diagnostic in query_diagnostics if not diagnostic.generation_failed
    ]
    retrieval_attempts = [
        diagnostic.retrieval_attempt_count
        for diagnostic in timing_rows
        if diagnostic.retrieval_attempt_count is not None
    ]

    return AdaptiveRetrievalConditionReport(
        condition=condition,
        generation_report=generation_report,
        query_diagnostics=query_diagnostics,
        total_retrieval_attempts=sum(retrieval_attempts),
        total_query_rewrites=sum(diagnostic.query_rewrite_count or 0 for diagnostic in timing_rows),
        recovery_trigger_count=sum(
            diagnostic.recovery_triggered for diagnostic in query_diagnostics
        ),
        successful_recovery_count=sum(
            diagnostic.recovery_succeeded for diagnostic in query_diagnostics
        ),
        recovery_grounded_refusal_count=sum(
            diagnostic.recovery_grounded_refusal for diagnostic in query_diagnostics
        ),
        missing_trace_count=sum(
            condition == "bounded_adaptive"
            and not diagnostic.generation_failed
            and diagnostic.adaptive_trace is None
            for diagnostic in query_diagnostics
        ),
        invalid_trace_count=sum(
            diagnostic.trace_valid is False for diagnostic in query_diagnostics
        ),
        invalid_provenance_count=sum(
            diagnostic.provenance_valid is False for diagnostic in query_diagnostics
        ),
        bound_violation_count=sum(
            diagnostic.bounds_respected is False for diagnostic in query_diagnostics
        ),
        mean_total_latency_ms=_mean([diagnostic.total_latency_ms for diagnostic in timing_rows]),
        p50_total_latency_ms=_percentile(
            [diagnostic.total_latency_ms for diagnostic in timing_rows],
            0.50,
        ),
        p95_total_latency_ms=_percentile(
            [diagnostic.total_latency_ms for diagnostic in timing_rows],
            0.95,
        ),
        mean_retrieval_ms=_mean(
            [
                diagnostic.retrieval_ms
                for diagnostic in timing_rows
                if diagnostic.retrieval_ms is not None
            ]
        ),
        p50_retrieval_ms=_percentile(
            [
                diagnostic.retrieval_ms
                for diagnostic in timing_rows
                if diagnostic.retrieval_ms is not None
            ],
            0.50,
        ),
        p95_retrieval_ms=_percentile(
            [
                diagnostic.retrieval_ms
                for diagnostic in timing_rows
                if diagnostic.retrieval_ms is not None
            ],
            0.95,
        ),
        mean_evidence_build_ms=_mean(
            [
                diagnostic.evidence_build_ms
                for diagnostic in timing_rows
                if diagnostic.evidence_build_ms is not None
            ]
        ),
        mean_retrieval_attempt_count=_mean(retrieval_attempts),
    )


def _query_diagnostics(
    *,
    condition: AdaptiveRetrievalConditionName,
    evaluation: GenerationQueryEvaluation,
    captured: _CapturedGeneration,
    config: AdaptiveRetrievalEvaluationConfig,
) -> AdaptiveRetrievalQueryDiagnostics:
    """Extract timing and trace diagnostics from one captured answer."""

    answer = captured.answer

    if answer is None:
        return AdaptiveRetrievalQueryDiagnostics(
            query_id=evaluation.query_id,
            generation_failed=True,
            total_latency_ms=captured.total_latency_ms,
        )

    timings = answer.stage_timings

    if condition == "single_pass":
        return _single_pass_diagnostics(
            evaluation=evaluation,
            captured=captured,
            timings=timings,
        )

    return _adaptive_diagnostics(
        evaluation=evaluation,
        captured=captured,
        answer=answer,
        timings=timings,
        config=config,
    )


def _single_pass_diagnostics(
    *,
    evaluation: GenerationQueryEvaluation,
    captured: _CapturedGeneration,
    timings: RAGStageTimings | None,
) -> AdaptiveRetrievalQueryDiagnostics:
    """Return condition-neutral facts for the frozen single-pass baseline."""

    return AdaptiveRetrievalQueryDiagnostics(
        query_id=evaluation.query_id,
        generation_failed=False,
        total_latency_ms=captured.total_latency_ms,
        retrieval_ms=(timings.retrieval_ms if timings is not None else None),
        evidence_build_ms=(timings.evidence_build_ms if timings is not None else None),
        sufficiency_ms=(timings.sufficiency_ms if timings is not None else None),
        retrieval_attempt_count=(timings.retrieval_attempt_count if timings is not None else None),
        query_rewrite_count=(timings.query_rewrite_count if timings is not None else None),
    )


def _adaptive_diagnostics(
    *,
    evaluation: GenerationQueryEvaluation,
    captured: _CapturedGeneration,
    answer: GroundedAnswer,
    timings: RAGStageTimings | None,
    config: AdaptiveRetrievalEvaluationConfig,
) -> AdaptiveRetrievalQueryDiagnostics:
    """Validate the bounded trace retained by one adaptive answer."""

    trace = (
        answer.retrieval_metadata.adaptive_retrieval
        if answer.retrieval_metadata is not None
        else None
    )

    trace_valid = _adaptive_trace_valid(
        trace=trace,
        answer=answer,
        timings=timings,
        config=config,
    )
    provenance_valid = _adaptive_provenance_valid(trace)
    bounds_respected = _adaptive_bounds_respected(
        trace=trace,
        timings=timings,
        config=config,
    )

    if trace is None:
        recovery_triggered = False
        recovery_succeeded = False
        recovery_grounded_refusal = False

    else:
        recovery_triggered = len(trace.attempts) == 2
        recovery_succeeded = recovery_triggered and trace.retrieval_terminal_state == "generate"
        recovery_grounded_refusal = (
            recovery_triggered and trace.retrieval_terminal_state == "grounded_refusal"
        )

    return AdaptiveRetrievalQueryDiagnostics(
        query_id=evaluation.query_id,
        generation_failed=False,
        total_latency_ms=captured.total_latency_ms,
        retrieval_ms=(timings.retrieval_ms if timings is not None else None),
        evidence_build_ms=(timings.evidence_build_ms if timings is not None else None),
        sufficiency_ms=(timings.sufficiency_ms if timings is not None else None),
        retrieval_attempt_count=(timings.retrieval_attempt_count if timings is not None else None),
        query_rewrite_count=(timings.query_rewrite_count if timings is not None else None),
        adaptive_trace=trace,
        trace_valid=trace_valid,
        provenance_valid=provenance_valid,
        bounds_respected=bounds_respected,
        recovery_triggered=recovery_triggered,
        recovery_succeeded=recovery_succeeded,
        recovery_grounded_refusal=recovery_grounded_refusal,
    )


def _adaptive_trace_valid(
    *,
    trace: AdaptiveRetrievalTrace | None,
    answer: GroundedAnswer,
    timings: RAGStageTimings | None,
    config: AdaptiveRetrievalEvaluationConfig,
) -> bool:
    """Verify that a trace agrees with answer state and recorded timings."""

    if trace is None:
        return False

    if len(trace.attempts) > config.maximum_retrieval_passes:
        return False

    if trace.retrieval_terminal_state == "generate" and answer.insufficient_evidence:
        return False

    if trace.retrieval_terminal_state == "grounded_refusal" and not answer.insufficient_evidence:
        return False

    if timings is None:
        return True

    rewrite_count = 1 if trace.rewritten_query is not None else 0

    return (
        timings.retrieval_attempt_count == len(trace.attempts)
        and timings.query_rewrite_count == rewrite_count
    )


def _adaptive_provenance_valid(
    trace: AdaptiveRetrievalTrace | None,
) -> bool:
    """Check that every retained adaptive attempt accounts for all evidence."""

    if trace is None:
        return False

    for attempt in trace.attempts:
        if attempt.returned_evidence_count != len(attempt.evidence_provenance):
            return False

        if attempt.used_evidence_count > attempt.returned_evidence_count:
            return False

        for provenance in attempt.evidence_provenance:
            if provenance.attempt_number != attempt.attempt_number:
                return False

            if not (
                provenance.chunk_id
                and provenance.citation_url
                and provenance.source_url
                and provenance.document_sha256
            ):
                return False

    return True


def _adaptive_bounds_respected(
    *,
    trace: AdaptiveRetrievalTrace | None,
    timings: RAGStageTimings | None,
    config: AdaptiveRetrievalEvaluationConfig,
) -> bool:
    """Check the trace and timing facts against the fixed Phase 25 bounds."""

    if trace is None:
        return False

    rewrite_count = 1 if trace.rewritten_query is not None else 0

    if len(trace.attempts) > config.maximum_retrieval_passes:
        return False

    if rewrite_count > config.maximum_query_rewrites:
        return False

    if timings is None:
        return True

    return (
        timings.retrieval_attempt_count <= config.maximum_retrieval_passes
        and timings.query_rewrite_count <= config.maximum_query_rewrites
    )


def _metric_deltas(
    *,
    single_pass: AdaptiveRetrievalConditionReport,
    bounded_adaptive: AdaptiveRetrievalConditionReport,
) -> AdaptiveRetrievalMetricDeltas:
    """Calculate bounded-adaptive minus single-pass metrics."""

    baseline = single_pass.generation_report
    adaptive = bounded_adaptive.generation_report

    return AdaptiveRetrievalMetricDeltas(
        generation_failure_rate=_delta(
            adaptive.generation_failure_rate,
            baseline.generation_failure_rate,
        ),
        answerability_accuracy=_delta(
            adaptive.answerability_accuracy,
            baseline.answerability_accuracy,
        ),
        answerable_completion_rate=_delta(
            adaptive.answerable_completion_rate,
            baseline.answerable_completion_rate,
        ),
        unsupported_refusal_rate=_delta(
            adaptive.unsupported_refusal_rate,
            baseline.unsupported_refusal_rate,
        ),
        claim_citation_coverage_rate=_delta(
            adaptive.claim_citation_coverage_rate,
            baseline.claim_citation_coverage_rate,
        ),
        citation_reference_validity_rate=_delta(
            adaptive.citation_reference_validity_rate,
            baseline.citation_reference_validity_rate,
        ),
        source_document_coverage_rate=_delta(
            adaptive.source_document_coverage_rate,
            baseline.source_document_coverage_rate,
        ),
        expected_term_recall=_delta(
            adaptive.expected_term_recall,
            baseline.expected_term_recall,
        ),
        structural_validity_rate=_delta(
            adaptive.structural_validity_rate,
            baseline.structural_validity_rate,
        ),
        mean_total_latency_ms=_optional_delta(
            bounded_adaptive.mean_total_latency_ms,
            single_pass.mean_total_latency_ms,
        ),
        p95_total_latency_ms=_optional_delta(
            bounded_adaptive.p95_total_latency_ms,
            single_pass.p95_total_latency_ms,
        ),
        mean_retrieval_ms=_optional_delta(
            bounded_adaptive.mean_retrieval_ms,
            single_pass.mean_retrieval_ms,
        ),
        p95_retrieval_ms=_optional_delta(
            bounded_adaptive.p95_retrieval_ms,
            single_pass.p95_retrieval_ms,
        ),
        mean_evidence_build_ms=_optional_delta(
            bounded_adaptive.mean_evidence_build_ms,
            single_pass.mean_evidence_build_ms,
        ),
        mean_retrieval_attempt_count=_optional_delta(
            bounded_adaptive.mean_retrieval_attempt_count,
            single_pass.mean_retrieval_attempt_count,
        ),
    )


def _safety_checks(
    *,
    parity: ProtectedBaselineParity,
    single_pass: AdaptiveRetrievalConditionReport,
    bounded_adaptive: AdaptiveRetrievalConditionReport,
) -> AdaptiveRetrievalSafetyChecks:
    """Apply the decision rules declared before running the held-out comparison."""

    baseline = single_pass.generation_report
    adaptive = bounded_adaptive.generation_report

    no_generation_failure_increase = (
        adaptive.generation_failure_rate <= baseline.generation_failure_rate
    )
    all_adaptive_traces_valid = (
        bounded_adaptive.missing_trace_count == 0 and bounded_adaptive.invalid_trace_count == 0
    )
    all_adaptive_provenance_valid = bounded_adaptive.invalid_provenance_count == 0
    all_adaptive_bounds_respected = bounded_adaptive.bound_violation_count == 0
    claim_citation_coverage_not_decreased = (
        adaptive.claim_citation_coverage_rate >= baseline.claim_citation_coverage_rate
    )
    citation_reference_validity_not_decreased = (
        adaptive.citation_reference_validity_rate >= baseline.citation_reference_validity_rate
    )
    source_document_coverage_not_decreased = (
        adaptive.source_document_coverage_rate >= baseline.source_document_coverage_rate
    )
    structural_validity_not_decreased = (
        adaptive.structural_validity_rate >= baseline.structural_validity_rate
    )
    unsupported_refusal_not_decreased = (
        adaptive.unsupported_refusal_rate >= baseline.unsupported_refusal_rate
    )
    answerability_accuracy_not_decreased = (
        adaptive.answerability_accuracy >= baseline.answerability_accuracy
    )
    answerable_completion_not_decreased = (
        adaptive.answerable_completion_rate >= baseline.answerable_completion_rate
    )
    expected_term_recall_not_decreased = (
        adaptive.expected_term_recall >= baseline.expected_term_recall
    )
    quality_improvement_observed = any(
        [
            adaptive.answerability_accuracy > baseline.answerability_accuracy,
            adaptive.answerable_completion_rate > baseline.answerable_completion_rate,
            adaptive.expected_term_recall > baseline.expected_term_recall,
        ]
    )

    integrity_passed = all(
        [
            no_generation_failure_increase,
            all_adaptive_traces_valid,
            all_adaptive_provenance_valid,
            all_adaptive_bounds_respected,
            claim_citation_coverage_not_decreased,
            citation_reference_validity_not_decreased,
            source_document_coverage_not_decreased,
            structural_validity_not_decreased,
            unsupported_refusal_not_decreased,
        ]
    )
    quality_non_regression_passed = all(
        [
            answerability_accuracy_not_decreased,
            answerable_completion_not_decreased,
            expected_term_recall_not_decreased,
        ]
    )

    return AdaptiveRetrievalSafetyChecks(
        baseline_parity=parity.matched,
        no_generation_failure_increase=no_generation_failure_increase,
        all_adaptive_traces_valid=all_adaptive_traces_valid,
        all_adaptive_provenance_valid=all_adaptive_provenance_valid,
        all_adaptive_bounds_respected=all_adaptive_bounds_respected,
        claim_citation_coverage_not_decreased=claim_citation_coverage_not_decreased,
        citation_reference_validity_not_decreased=citation_reference_validity_not_decreased,
        source_document_coverage_not_decreased=source_document_coverage_not_decreased,
        structural_validity_not_decreased=structural_validity_not_decreased,
        unsupported_refusal_not_decreased=unsupported_refusal_not_decreased,
        answerability_accuracy_not_decreased=answerability_accuracy_not_decreased,
        answerable_completion_not_decreased=answerable_completion_not_decreased,
        expected_term_recall_not_decreased=expected_term_recall_not_decreased,
        quality_improvement_observed=quality_improvement_observed,
        integrity_passed=integrity_passed,
        quality_non_regression_passed=quality_non_regression_passed,
    )


def _verdict(
    *,
    parity: ProtectedBaselineParity,
    bounded_adaptive: AdaptiveRetrievalConditionReport,
    safety_checks: AdaptiveRetrievalSafetyChecks,
    config: AdaptiveRetrievalEvaluationConfig,
) -> tuple[AdaptiveRetrievalEvaluationVerdict, str]:
    """Classify the fixed policy without tuning or post-hoc thresholds."""

    if not parity.matched:
        return (
            "baseline_parity_failed",
            (
                "The newly executed single-pass condition does not match the protected "
                "baseline artifact, so the paired result is not interpretable."
            ),
        )

    if not safety_checks.integrity_passed:
        return (
            "integrity_regression",
            (
                "The bounded policy violated a predeclared integrity or grounding "
                "non-regression condition."
            ),
        )

    if not safety_checks.quality_non_regression_passed:
        return (
            "quality_regression",
            (
                "The bounded policy preserved integrity but reduced at least one "
                "predeclared answer-quality metric."
            ),
        )

    if (
        bounded_adaptive.successful_recovery_count >= config.minimum_successful_recoveries
        and safety_checks.quality_improvement_observed
    ):
        return (
            "benefit_observed",
            (
                "The bounded policy achieved the predeclared minimum number of "
                "successful recoveries and improved a predeclared answer-quality metric "
                "without an integrity or quality regression."
            ),
        )

    if bounded_adaptive.recovery_trigger_count == 0:
        return (
            "safe_no_recovery_activated",
            (
                "The bounded policy preserved the protected baseline and all integrity "
                "checks, but the held-out query set did not trigger recovery."
            ),
        )

    return (
        "safe_no_measured_benefit",
        (
            "The bounded policy activated safely, but it did not reach the predeclared "
            "minimum number of successful recoveries on this held-out query set."
        ),
    )


def _equal_metric_values(
    expected: object,
    observed: object,
) -> bool:
    """Compare benchmark metrics exactly for text and near-exactly for floats."""

    if isinstance(expected, float) and isinstance(observed, (int, float)):
        return abs(expected - float(observed)) <= 1e-12

    return expected == observed


def _delta(
    adaptive: float,
    baseline: float,
) -> float:
    """Return a stable adaptive-minus-baseline numeric delta."""

    return round(adaptive - baseline, 6)


def _optional_delta(
    adaptive: float | None,
    baseline: float | None,
) -> float | None:
    """Return a delta only when both conditions measured the metric."""

    if adaptive is None or baseline is None:
        return None

    return _delta(adaptive, baseline)


def _mean(
    values: Sequence[int | float],
) -> float | None:
    """Return one stable mean, or None when no value was recorded."""

    if not values:
        return None

    return round(sum(values) / len(values), 3)


def _percentile(
    values: Sequence[int | float],
    quantile: float,
) -> float | None:
    """Return an interpolated percentile without a new dependency."""

    if not values:
        return None

    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1.")

    ordered = sorted(float(value) for value in values)

    if len(ordered) == 1:
        return round(ordered[0], 3)

    position = (len(ordered) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index

    return round(
        ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction,
        3,
    )


def _elapsed_ms(
    started_at: float,
) -> float:
    """Return a non-negative, rounded wall-clock duration."""

    return round(max((perf_counter() - started_at) * 1000.0, 0.0), 3)


def _write_json(
    path: Path,
    value: object,
) -> None:
    """Write one formatted JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _percentage(value: float) -> str:
    """Format a fraction for the Markdown report."""

    return f"{100.0 * value:.2f}%"


def _signed_percentage(value: float) -> str:
    """Format a signed fraction delta for the Markdown report."""

    return f"{100.0 * value:+.2f} pp"


def _milliseconds(value: float | None) -> str:
    """Format an optional millisecond measurement."""

    return "not measured" if value is None else f"{value:.3f} ms"


def _signed_milliseconds(value: float | None) -> str:
    """Format an optional signed millisecond delta."""

    return "not measured" if value is None else f"{value:+.3f} ms"


def _pass_fail(value: bool) -> str:
    """Format a boolean decision for Markdown."""

    return "PASS" if value else "FAIL"
