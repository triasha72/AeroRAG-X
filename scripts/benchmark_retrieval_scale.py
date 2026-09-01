"""Benchmark a retrieval command at 10K, 100K, and 1M chunk checkpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.retrieval.scaling import ScaleQuery, benchmark_retriever, write_scale_report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--corpus-chunks", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def load_queries(path: Path, qrels_path: Path) -> list[ScaleQuery]:
    relevance: dict[str, set[str]] = {}
    for line in qrels_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        relevance[str(row["query_id"])] = {str(item) for item in row["relevant_chunk_ids"]}

    queries: list[ScaleQuery] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        query_id = str(row["query_id"])
        if query_id not in relevance:
            raise ValueError(f"query {query_id!r} has no relevance judgments")
        queries.append(
            ScaleQuery(
                query_id=query_id,
                text=str(row["query"]),
                relevant_chunk_ids=relevance[query_id],
            )
        )
    return queries


def load_results(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("results must be a query-text to chunk-ID-list mapping")
    return {str(key): [str(item) for item in value] for key, value in data.items()}


def main() -> None:
    args = parse_arguments()
    queries = load_queries(args.queries, args.qrels)
    results = load_results(args.results)
    measurement = benchmark_retriever(
        corpus_chunks=args.corpus_chunks,
        queries=queries,
        search=lambda query, top_k: results.get(query, [])[:top_k],
        top_k=args.top_k,
    )
    write_scale_report(args.output, [measurement])


if __name__ == "__main__":
    main()
