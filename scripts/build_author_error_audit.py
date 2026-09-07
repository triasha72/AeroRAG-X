#!/usr/bin/env python3
"""Build a deterministic 50-case author audit from the frozen aerospace set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/evaluation/source_grounded_review_v0_1_512.template.jsonl"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=50)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.source.read_text().splitlines()]
    if args.size < 1 or args.size > len(rows):
        raise ValueError("size must fit within the frozen review set")
    rows.sort(key=lambda row: hashlib.sha256(row["query_id"].encode()).hexdigest())
    output = [
        {
            "query_id": row["query_id"],
            "reviewer_role": "project_author",
            "answer_supported": None,
            "citation_correct": None,
            "abstention_correct": None,
            "error_category": None,
            "notes": None,
        }
        for row in rows[: args.size]
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(row) for row in output) + "\n")


if __name__ == "__main__":
    main()
