"""Check a frozen generation-evaluation report against its versioned policy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aeroragx.evaluation.regression import (
    check_generation_regression,
    load_frozen_generation_report,
    load_generation_regression_policy,
)


def main() -> int:
    """Run the frozen generation-regression policy check."""

    parser = argparse.ArgumentParser(
        description="Check a frozen generation-evaluation report against a policy."
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("configs/evaluation_regression_v0_1.yaml"),
        help="YAML regression policy path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional report path that overrides the policy value.",
    )
    args = parser.parse_args()

    try:
        policy = load_generation_regression_policy(args.policy)
        report_path = args.report if args.report is not None else policy.report_path
        report = load_frozen_generation_report(report_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Generation evaluation regression check: ERROR: {exc}", file=sys.stderr)
        return 2

    failures = check_generation_regression(policy=policy, report=report)

    if failures:
        print("Generation evaluation regression check: FAIL", file=sys.stderr)

        for failure in failures:
            print(f"- {failure}", file=sys.stderr)

        return 1

    print("Generation evaluation regression check: PASS")
    print(f"Report: {report_path}")
    print(f"Queries: {report.query_count}")
    print(f"Expected-term recall: {report.expected_term_recall:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
