"""Regression policy checks for frozen generation-evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class GenerationMetricThresholds(BaseModel):
    """Minimum acceptable values for frozen generation metrics."""

    model_config = ConfigDict(extra="forbid")

    answerability_accuracy: float = Field(ge=0.0, le=1.0)
    answerable_completion_rate: float = Field(ge=0.0, le=1.0)
    unsupported_refusal_rate: float = Field(ge=0.0, le=1.0)
    claim_citation_coverage_rate: float = Field(ge=0.0, le=1.0)
    citation_reference_validity_rate: float = Field(ge=0.0, le=1.0)
    source_document_coverage_rate: float = Field(ge=0.0, le=1.0)
    expected_term_recall: float = Field(ge=0.0, le=1.0)
    structural_validity_rate: float = Field(ge=0.0, le=1.0)


class GenerationReportExpectation(BaseModel):
    """Identity fields that must remain stable for a frozen report."""

    model_config = ConfigDict(extra="forbid")

    query_count: int = Field(ge=1)
    generation_provider: str = Field(min_length=1)
    generation_model: str = Field(min_length=1)


class GenerationRegressionPolicy(BaseModel):
    """A versioned policy for one frozen generation benchmark report."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    report_path: Path
    expected: GenerationReportExpectation
    minimum_metrics: GenerationMetricThresholds


class FrozenGenerationReport(BaseModel):
    """The subset of report fields required by the regression policy."""

    model_config = ConfigDict(extra="ignore")

    query_count: int = Field(ge=1)
    generation_provider: str = Field(min_length=1)
    generation_model: str = Field(min_length=1)
    answerability_accuracy: float = Field(ge=0.0, le=1.0)
    answerable_completion_rate: float = Field(ge=0.0, le=1.0)
    unsupported_refusal_rate: float = Field(ge=0.0, le=1.0)
    claim_citation_coverage_rate: float = Field(ge=0.0, le=1.0)
    citation_reference_validity_rate: float = Field(ge=0.0, le=1.0)
    source_document_coverage_rate: float = Field(ge=0.0, le=1.0)
    expected_term_recall: float = Field(ge=0.0, le=1.0)
    structural_validity_rate: float = Field(ge=0.0, le=1.0)


def load_generation_regression_policy(path: Path) -> GenerationRegressionPolicy:
    """Load and validate a YAML generation-regression policy."""

    if not path.exists():
        raise FileNotFoundError(f"Regression policy not found: {path}")

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Regression policy root must be a YAML mapping.")

    try:
        return GenerationRegressionPolicy.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid regression policy {path}.") from exc


def load_frozen_generation_report(path: Path) -> FrozenGenerationReport:
    """Load the fields required for one frozen generation report check."""

    if not path.exists():
        raise FileNotFoundError(f"Frozen generation report not found: {path}")

    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in frozen generation report {path}.") from exc

    try:
        return FrozenGenerationReport.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid frozen generation report {path}.") from exc


def check_generation_regression(
    *,
    policy: GenerationRegressionPolicy,
    report: FrozenGenerationReport,
) -> list[str]:
    """Return every violated identity or minimum-metric requirement."""

    failures: list[str] = []
    expected = policy.expected

    if report.query_count != expected.query_count:
        failures.append(f"query_count: expected {expected.query_count}, found {report.query_count}")

    if report.generation_provider != expected.generation_provider:
        failures.append(
            "generation_provider: "
            f"expected {expected.generation_provider!r}, "
            f"found {report.generation_provider!r}"
        )

    if report.generation_model != expected.generation_model:
        failures.append(
            "generation_model: "
            f"expected {expected.generation_model!r}, "
            f"found {report.generation_model!r}"
        )

    for metric_name, minimum in policy.minimum_metrics.model_dump().items():
        actual = getattr(report, metric_name)

        if actual < minimum:
            failures.append(f"{metric_name}: found {actual:.4f}, required at least {minimum:.4f}")

    return failures
