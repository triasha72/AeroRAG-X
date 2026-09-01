#!/usr/bin/env python3
"""Promote the 512-case candidate only after two complete independent reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--review-a", type=Path, required=True)
    parser.add_argument("--review-b", type=Path, required=True)
    parser.add_argument("--protected-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--minimum-accepted", type=int, default=500)
    return parser.parse_args()


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _index(rows: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    indexed = {str(row["query_id"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"Duplicate query IDs in {name}.")
    return indexed


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_review(row: dict[str, Any], query_id: str) -> None:
    if not isinstance(row.get("reviewer_id"), str) or not row["reviewer_id"].strip():
        raise ValueError(f"Missing reviewer_id for {query_id}.")
    for field in ("query_is_clear", "source_supports_query", "relevant_chunk_correct"):
        if not isinstance(row.get(field), bool):
            raise ValueError(f"{field} is not complete for {query_id}.")
    if row.get("decision") not in {"ACCEPT", "REJECT"}:
        raise ValueError(f"Invalid decision for {query_id}.")
    expected = all(
        bool(row[field])
        for field in ("query_is_clear", "source_supports_query", "relevant_chunk_correct")
    )
    if (row["decision"] == "ACCEPT") != expected:
        raise ValueError(f"Decision contradicts review fields for {query_id}.")


def main() -> None:
    args = parse_args()
    queries = _rows(args.queries)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("status") != "candidate_requires_independent_review":
        raise SystemExit("Input manifest is not an unreviewed candidate.")
    if manifest.get("queries_sha256") != _sha(args.queries):
        raise SystemExit("Candidate query checksum differs from the manifest.")
    if len(queries) < 500 or len(queries) != int(manifest.get("case_count", -1)):
        raise SystemExit("Candidate must contain the complete manifested 500+ cases.")

    query_index = _index(queries, "queries")
    review_a = _index(_rows(args.review_a), "review A")
    review_b = _index(_rows(args.review_b), "review B")
    if set(review_a) != set(query_index) or set(review_b) != set(query_index):
        raise SystemExit("Both reviewers must cover every candidate query exactly once.")

    reviewer_a_ids = {str(row.get("reviewer_id", "")).strip() for row in review_a.values()}
    reviewer_b_ids = {str(row.get("reviewer_id", "")).strip() for row in review_b.values()}
    if len(reviewer_a_ids) != 1 or len(reviewer_b_ids) != 1 or reviewer_a_ids == reviewer_b_ids:
        raise SystemExit("Reviews must come from two distinct, consistently identified reviewers.")

    accepted: list[dict[str, Any]] = []
    agreement = 0
    disagreements: list[str] = []
    for query_id in sorted(query_index):
        left, right = review_a[query_id], review_b[query_id]
        _validate_review(left, query_id)
        _validate_review(right, query_id)
        if left["decision"] == right["decision"]:
            agreement += 1
        else:
            disagreements.append(query_id)
        if left["decision"] == right["decision"] == "ACCEPT":
            accepted.append({**query_index[query_id], "review_status": "independently_accepted"})

    if disagreements:
        raise SystemExit(
            f"Independent-review disagreements require adjudication: {len(disagreements)} cases."
        )
    if len(accepted) < args.minimum_accepted:
        raise SystemExit(
            f"Only {len(accepted)} cases were independently accepted; "
            f"require {args.minimum_accepted}."
        )

    args.protected_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.protected_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in accepted),
        encoding="utf-8",
    )
    summary = {
        "version": "0.1",
        "status": "protected_independently_reviewed",
        "candidate_count": len(queries),
        "accepted_count": len(accepted),
        "reviewer_count": 2,
        "raw_decision_agreement": agreement / len(queries),
        "disagreement_count": 0,
        "candidate_queries_sha256": _sha(args.queries),
        "review_a_sha256": _sha(args.review_a),
        "review_b_sha256": _sha(args.review_b),
        "protected_queries_sha256": _sha(args.protected_output),
    }
    args.summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
