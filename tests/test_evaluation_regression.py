"""Tests for frozen generation-evaluation regression checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aeroragx.evaluation.regression import (
    FrozenGenerationReport,
    GenerationMetricThresholds,
    GenerationRegressionPolicy,
    GenerationReportExpectation,
    check_generation_regression,
    load_frozen_generation_report,
    load_generation_regression_policy,
)


def _report(**overrides: object) -> FrozenGenerationReport:
    values: dict[str, object] = {
        "query_count": 32,
        "generation_provider": "fake",
        "generation_model": "deterministic-grounded-v0",
        "answerability_accuracy": 1.0,
        "answerable_completion_rate": 1.0,
        "unsupported_refusal_rate": 1.0,
        "claim_citation_coverage_rate": 1.0,
        "citation_reference_validity_rate": 1.0,
        "source_document_coverage_rate": 1.0,
        "expected_term_recall": 0.8793,
        "structural_validity_rate": 1.0,
    }
    values.update(overrides)
    return FrozenGenerationReport.model_validate(values)


def _policy() -> GenerationRegressionPolicy:
    return GenerationRegressionPolicy(
        version="0.1",
        report_path=Path(
            "artifacts/evaluation/generation_deterministic_v0_3_phase17_baseline.json"
        ),
        expected=GenerationReportExpectation(
            query_count=32,
            generation_provider="fake",
            generation_model="deterministic-grounded-v0",
        ),
        minimum_metrics=GenerationMetricThresholds(
            answerability_accuracy=1.0,
            answerable_completion_rate=1.0,
            unsupported_refusal_rate=1.0,
            claim_citation_coverage_rate=1.0,
            citation_reference_validity_rate=1.0,
            source_document_coverage_rate=1.0,
            expected_term_recall=0.87,
            structural_validity_rate=1.0,
        ),
    )


def test_generation_regression_accepts_a_report_meeting_policy() -> None:
    assert check_generation_regression(policy=_policy(), report=_report()) == []


def test_generation_regression_reports_each_violation() -> None:
    report = _report(query_count=31, expected_term_recall=0.86)

    failures = check_generation_regression(policy=_policy(), report=report)

    assert failures == [
        "query_count: expected 32, found 31",
        "expected_term_recall: found 0.8600, required at least 0.8700",
    ]


def test_policy_loader_reads_valid_yaml(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
version: "0.1"
report_path: artifacts/evaluation/generation_deterministic_v0_3_phase17_baseline.json
expected:
  query_count: 32
  generation_provider: fake
  generation_model: deterministic-grounded-v0
minimum_metrics:
  answerability_accuracy: 1.0
  answerable_completion_rate: 1.0
  unsupported_refusal_rate: 1.0
  claim_citation_coverage_rate: 1.0
  citation_reference_validity_rate: 1.0
  source_document_coverage_rate: 1.0
  expected_term_recall: 0.87
  structural_validity_rate: 1.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    policy = load_generation_regression_policy(policy_path)

    assert policy.expected.query_count == 32
    assert policy.minimum_metrics.expected_term_recall == 0.87


def test_policy_loader_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("- not\n- a mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mapping"):
        load_generation_regression_policy(policy_path)


def test_report_loader_reads_required_summary_fields(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(_report().model_dump()),
        encoding="utf-8",
    )

    report = load_frozen_generation_report(report_path)

    assert report.generation_provider == "fake"
    assert report.expected_term_recall == 0.8793
