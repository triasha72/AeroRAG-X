#!/usr/bin/env python3
"""Reject adaptive evidence policies that pass only by behaving like fixed top-3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return cast(dict[str, Any], value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-decision", type=Path, required=True)
    parser.add_argument("--budget-decisions", type=Path, required=True)
    parser.add_argument("--adaptive-vs-top3", type=Path, required=True)
    parser.add_argument("--minimum-expansions", type=int, default=3)
    parser.add_argument("--minimum-retained-top3", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    quality = _load(args.quality_decision)
    budget = _load(args.budget_decisions)
    paired = _load(args.adaptive_vs_top3)
    decisions = budget.get("decisions", [])
    if not isinstance(decisions, list):
        raise ValueError("Budget decisions must contain a decisions list.")
    expanded = int(budget.get("expanded_count", 0))
    retained = int(budget.get("retained_top3_count", 0))
    effective_higher = int(paired.get("treatment_higher_token_query_count", 0))
    invalid_expansions = sum(
        bool(row.get("expanded")) and not bool(row.get("maximum_sufficient"))
        for row in decisions
        if isinstance(row, dict)
    )
    checks = {
        "quality_and_efficiency_gate_passed": quality.get("status") == "promoted",
        "mixed_policy_expanded_enough": expanded >= args.minimum_expansions,
        "mixed_policy_retained_top3_enough": retained >= args.minimum_retained_top3,
        "expansion_changed_provider_input": effective_higher >= args.minimum_expansions,
        "all_expansions_recover_sufficiency": invalid_expansions == 0,
    }
    result = {
        "version": "0.1",
        "status": "promoted" if all(checks.values()) else "rejected",
        "checks": checks,
        "expanded_count": expanded,
        "retained_top3_count": retained,
        "effective_higher_token_query_count": effective_higher,
        "invalid_expansion_count": invalid_expansions,
        "minimum_expansions": args.minimum_expansions,
        "minimum_retained_top3": args.minimum_retained_top3,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "promoted":
        raise SystemExit("Adaptive evidence budget failed one or more policy-activity gates.")


if __name__ == "__main__":
    main()
