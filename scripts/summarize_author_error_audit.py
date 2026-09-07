#!/usr/bin/env python3
"""Validate and summarize a completed, disclosed author audit."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.audit.read_text().splitlines() if line]
    if len(rows) < 50:
        raise ValueError("A complete author audit requires at least 50 cases")
    required = ("answer_supported", "citation_correct", "abstention_correct")
    for row in rows:
        if row.get("reviewer_role") != "project_author":
            raise ValueError("Every row must disclose reviewer_role=project_author")
        if any(not isinstance(row.get(field), bool) for field in required):
            raise ValueError(f"Incomplete audit decision for {row.get('query_id')}")
    categories = Counter(str(row.get("error_category") or "none") for row in rows)
    result = {
        "schema_version": "1.0",
        "reviewer_role": "project_author",
        "case_count": len(rows),
        "complete": True,
        "rates": {
            field: sum(bool(row[field]) for row in rows) / len(rows) for field in required
        },
        "error_categories": dict(sorted(categories.items())),
        "claim_scope": "disclosed project-author error audit",
        "non_claims": [
            "This is not independent review.",
            "This is not aerospace safety validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
