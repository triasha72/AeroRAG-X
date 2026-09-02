#!/usr/bin/env python3
"""Fail closed unless a compact generation candidate saves tokens without quality regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-report", type=Path, required=True)
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--paired-efficiency", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-token-reduction", type=float, default=0.15)
    parser.add_argument("--maximum-rate-regression", type=float, default=0.03125)
    return parser.parse_args()


def _load(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return cast(dict[str, Any], value)


def main() -> None:
    args = parse_args()
    baseline, candidate, paired = map(
        _load,
        (args.baseline_report, args.candidate_report, args.paired_efficiency),
    )
    checks: dict[str, bool] = {
        "same_complete_query_contract": (baseline["query_count"] == candidate["query_count"] == 32),
        "failure_count_not_worse": (
            candidate["generation_failure_count"] <= baseline["generation_failure_count"]
        ),
    }
    for metric in (
        "answerability_accuracy",
        "answerable_completion_rate",
        "unsupported_refusal_rate",
        "claim_citation_coverage_rate",
        "citation_reference_validity_rate",
        "source_document_coverage_rate",
        "expected_term_recall",
        "structural_validity_rate",
    ):
        checks[f"{metric}_within_bound"] = (
            float(candidate[metric]) >= float(baseline[metric]) - args.maximum_rate_regression
        )
    relative_value = paired.get("relative_output_token_change")
    relative_change = float(relative_value) if relative_value is not None else None
    checks["paired_output_token_reduction"] = (
        relative_change is not None and relative_change <= -args.minimum_token_reduction
    )
    checks["paired_sample_present"] = int(paired["paired_provider_call_count"]) >= 15

    promoted = all(checks.values())
    result = {
        "version": "0.1",
        "status": "promoted" if promoted else "rejected",
        "checks": checks,
        "relative_output_token_change": relative_change,
        "minimum_token_reduction": args.minimum_token_reduction,
        "maximum_rate_regression": args.maximum_rate_regression,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not promoted:
        raise SystemExit("Compact generation candidate failed one or more promotion gates.")


if __name__ == "__main__":
    main()
