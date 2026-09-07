"""Fail-closed readiness check for a future independently reviewed v0.6 set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _ids(path: Path) -> set[str]:
    rows = _rows(path)
    ids = {str(row.get("id", row.get("query_id", ""))) for row in rows}
    if not ids or "" in ids:
        raise ValueError(f"{path} must contain non-empty id or query_id fields")
    return ids


def _review_ids(path: Path, reviewer: str) -> set[str]:
    rows = _rows(path)
    result = set()
    for row in rows:
        query_id = str(row.get("query_id", row.get("id", "")))
        if not query_id or row.get("reviewer") not in (None, reviewer):
            raise ValueError(f"{path} has an invalid {reviewer} response row")
        result.add(query_id)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--heldout", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--protected", type=Path, required=True)
    parser.add_argument("--review-a", type=Path, required=True)
    parser.add_argument("--review-b", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    heldout = _ids(args.heldout)
    development = _ids(args.development)
    protected = _ids(args.protected)
    review_a = _review_ids(args.review_a, "A")
    review_b = _review_ids(args.review_b, "B")
    checks = {
        "heldout_nonempty": bool(heldout),
        "heldout_disjoint_from_development": not heldout & development,
        "heldout_disjoint_from_protected": not heldout & protected,
        "review_a_complete": review_a == heldout,
        "review_b_complete": review_b == heldout,
        "reviewers_independent_files": args.review_a.resolve() != args.review_b.resolve(),
    }
    result = {
        "version": "0.1",
        "status": "ready_for_model_evaluation" if all(checks.values()) else "blocked",
        "checks": checks,
        "heldout_query_count": len(heldout),
        "heldout_sha256": hashlib.sha256(args.heldout.read_bytes()).hexdigest(),
        "review_a_sha256": hashlib.sha256(args.review_a.read_bytes()).hexdigest(),
        "review_b_sha256": hashlib.sha256(args.review_b.read_bytes()).hexdigest(),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "ready_for_model_evaluation":
        raise SystemExit("v0.6 held-out readiness is blocked")


if __name__ == "__main__":
    main()
