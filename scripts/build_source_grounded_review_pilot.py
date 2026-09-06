#!/usr/bin/env python3
"""Build two matching 25-case pilot sheets from the frozen 512-case review set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def build_pilot(source: Path, output_dir: Path, size: int = 25) -> None:
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    if size < 1 or size > len(rows):
        raise ValueError("size must be between 1 and the number of source rows")
    rows.sort(key=lambda row: hashlib.sha256(row["query_id"].encode()).hexdigest())
    selected = sorted(rows[:size], key=lambda row: row["query_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    for reviewer in ("reviewer_a", "reviewer_b"):
        target = output_dir / f"source_grounded_pilot_{reviewer}.jsonl"
        target.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in selected) + "\n",
            encoding="utf-8",
        )
    manifest = {
        "schema_version": "1.0",
        "purpose": "unpaid_volunteer_pilot",
        "cases": size,
        "full_study_cases": len(rows),
        "reviewers_required": 2,
        "compensation": "none",
        "human_reviews_completed": False,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/evaluation/source_grounded_review_v0_1_512.template.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--size", type=int, default=25)
    args = parser.parse_args()
    build_pilot(args.source, args.output_dir, args.size)


if __name__ == "__main__":
    main()
