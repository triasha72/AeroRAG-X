#!/usr/bin/env python3
"""Build a deterministic 50-case author audit packet from frozen NASA cases."""

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
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("data/evaluation/source_grounded_queries_v0_1_512.jsonl"),
    )
    parser.add_argument(
        "--qrels",
        type=Path,
        default=Path("data/evaluation/source_grounded_qrels_v0_1_512.jsonl"),
    )
    parser.add_argument(
        "--retrieval",
        type=Path,
        default=Path("artifacts/evaluation/source_grounded_reranker_v0_1_512.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=50)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.source.read_text().splitlines() if line]
    if args.size < 1 or args.size > len(rows):
        raise ValueError("size must fit within the frozen review set")
    rows.sort(key=lambda row: hashlib.sha256(row["query_id"].encode()).hexdigest())
    queries = {
        row["query_id"]: row
        for row in (json.loads(line) for line in args.queries.read_text().splitlines() if line)
    }
    qrels = {
        row["query_id"]: row["relevant_chunk_ids"]
        for row in (json.loads(line) for line in args.qrels.read_text().splitlines() if line)
    }
    retrieval = json.loads(args.retrieval.read_text())
    rankings = {row["query_id"]: row for row in retrieval["per_query"]}
    output = []
    for row in rows[: args.size]:
        query_id = row["query_id"]
        query = queries[query_id]
        ranking = rankings[query_id]
        output.append(
            {
                "query_id": query_id,
                "reviewer_role": "project_author",
                "query": query["query"],
                "expected_terms": query["expected_terms"],
                "source_document_id": query["source_document_id"],
                "source_page_start": query["source_page_start"],
                "source_page_end": query["source_page_end"],
                "judged_relevant_chunk_ids": qrels[query_id],
                "retrieved_chunk_ids": ranking["retrieved_chunk_ids"],
                "relevant_retrieved_ids": ranking["relevant_retrieved_ids"],
                "reciprocal_rank_at_10": ranking["reciprocal_rank_at_10"],
                "answer_supported": None,
                "citation_correct": None,
                "abstention_correct": None,
                "error_category": None,
                "notes": "",
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(row) for row in output) + "\n")


if __name__ == "__main__":
    main()
