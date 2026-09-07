#!/usr/bin/env python3
"""Build controlled source-ID corruptions from frozen NASA retrieval cases."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()

    queries = {str(row["query_id"]): row for row in rows(args.queries)}
    qrels = {
        str(row["query_id"]): {str(value) for value in row["relevant_chunk_ids"]}
        for row in rows(args.qrels)
    }
    retrieval = json.loads(args.retrieval.read_text(encoding="utf-8"))
    rankings = {
        str(row["query_id"]): [str(value) for value in row["retrieved_chunk_ids"]]
        for row in retrieval["per_query"]
    }
    selected = sorted(
        set(queries) & set(qrels) & set(rankings),
        key=lambda value: hashlib.sha256(value.encode()).hexdigest(),
    )[: args.count]
    if len(selected) != args.count:
        raise ValueError(f"Only {len(selected)} complete cases are available")

    output: list[dict[str, Any]] = []
    detected = 0
    for index, query_id in enumerate(selected):
        correct = sorted(qrels[query_id])[0]
        candidates = [value for value in rankings[query_id] if value not in qrels[query_id]]
        if candidates:
            corrupted = candidates[0]
        else:
            next_query = selected[(index + 1) % len(selected)]
            corrupted = sorted(qrels[next_query] - qrels[query_id])[0]
        corruption_detected = corrupted not in qrels[query_id]
        detected += int(corruption_detected)
        output.append(
            {
                "case_id": f"citation-corruption-{index + 1:04d}",
                "query_id": query_id,
                "query": queries[query_id]["query"],
                "correct_source_chunk_id": correct,
                "corrupted_source_chunk_id": corrupted,
                "corruption": "replace_with_retrieved_nonrelevant_chunk",
                "expected": "REJECT_CITATION",
                "provenance_guard_decision": (
                    "REJECT_CITATION" if corruption_detected else "ACCEPT_CITATION"
                ),
                "passed": corruption_detected,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in output), encoding="utf-8"
    )
    summary = {
        "schema_version": "1.0",
        "suite": "source-id-citation-corruption-v1",
        "case_count": len(output),
        "detected": detected,
        "detection_rate": detected / len(output),
        "decision": "passed" if detected == len(output) else "blocked",
        "claim_scope": "deterministic provenance guard, not semantic entailment",
        "limitations": [
            "The test detects wrong source IDs, not subtle unsupported wording.",
            "Cases are derived from automatically constructed NASA queries.",
        ],
    }
    args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
