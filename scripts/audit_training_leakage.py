#!/usr/bin/env python3
"""Audit candidate LoRA training data for protected benchmark leakage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
)
from aeroragx.training.dataset import (
    LeakageAuditReport,
    audit_training_leakage,
    load_training_examples,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Check LoRA training JSONL for deterministic "
            "overlap with protected AeroRAG-X evaluation data."
        )
    )

    parser.add_argument(
        "--training-input",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--protected-queries",
        type=Path,
        default=Path("data/evaluation/generation_queries_v0_3.jsonl"),
    )

    parser.add_argument(
        "--protected-generation-report",
        type=Path,
        default=Path("artifacts/evaluation/generation_transformers_base_v0_1.json"),
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def main() -> int:
    """Run leakage audit and return shell exit code."""

    args = parse_args()

    training_examples = load_training_examples(args.training_input)

    protected_queries = load_generation_evaluation_queries(args.protected_queries)

    protected_query_lookup = {query.query_id: query.query for query in protected_queries}

    protected_answers = _load_supported_protected_answers(args.protected_generation_report)

    report = audit_training_leakage(
        training_examples,
        protected_queries=(protected_query_lookup),
        protected_answers=(protected_answers),
    )

    _print_report(report)

    if args.report_output is not None:
        args.report_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.report_output.write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

        print(
            "Report:",
            args.report_output,
        )

    return 1 if report.has_leakage else 0


def _load_supported_protected_answers(
    path: Path,
) -> dict[str, str]:
    """Load answerable benchmark outputs for overlap checks."""

    raw_value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw_value, dict):
        raise ValueError("Protected generation report must contain a JSON object.")

    query_results = raw_value.get("query_results")

    if not isinstance(
        query_results,
        list,
    ):
        raise ValueError("Protected generation report must contain query_results.")

    answers: dict[str, str] = {}

    for row in query_results:
        if not isinstance(row, dict):
            raise ValueError("Protected query result must contain a JSON object.")

        if row.get("expected_answerable") is not True:
            continue

        if row.get("generation_failed") is True:
            continue

        query_id = row.get("query_id")

        answer = row.get("answer")

        if not isinstance(
            query_id,
            str,
        ):
            raise ValueError("Protected query result has invalid query_id.")

        if not isinstance(
            answer,
            str,
        ):
            raise ValueError("Protected query result has invalid answer.")

        normalized_answer = answer.strip()

        if not normalized_answer:
            continue

        answers[query_id] = normalized_answer

    return answers


def _print_report(
    report: LeakageAuditReport,
) -> None:
    """Print compact leakage-audit results."""

    print()
    print("AeroRAG-X training leakage audit")
    print("-------------------------------")

    print(
        "Training examples:",
        report.training_example_count,
    )

    print(
        "Protected queries:",
        report.protected_query_count,
    )

    print(
        "Protected answers:",
        report.protected_answer_count,
    )

    print(
        "Findings:",
        len(report.findings),
    )

    if not report.findings:
        print()
        print("No deterministic leakage was detected.")

        return

    print()

    for finding in report.findings:
        print(
            finding.training_example_id,
            "->",
            finding.kind,
            "->",
            finding.protected_reference,
        )


if __name__ == "__main__":
    raise SystemExit(main())
