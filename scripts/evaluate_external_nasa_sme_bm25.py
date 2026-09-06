#!/usr/bin/env python3
"""Evaluate exact BM25 on the revision-pinned NASA SME benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from aeroragx.retrieval.bm25 import tokenize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _ranking_metrics(ranking: list[str], relevant: set[str], cutoff: int) -> tuple[float, float]:
    gains = [1.0 if item in relevant else 0.0 for item in ranking]
    recall = sum(gains) / len(relevant)
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(relevant), cutoff)))
    return recall, dcg / ideal if ideal else 0.0


def main() -> None:
    args = parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be positive")

    corpus_path = args.benchmark_root / "corpus.jsonl"
    queries_path = args.benchmark_root / "queries.jsonl"
    qrel_paths = [
        args.benchmark_root / "qrels" / f"{name}.tsv" for name in ("earth", "astro", "planetary")
    ]
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt.get("evidence_class") != "independent_expert_queries":
        raise SystemExit("Receipt is not classified as independent expert-query evidence.")

    queries = [
        json.loads(line) for line in queries_path.read_text(encoding="utf-8").splitlines() if line
    ]
    query_by_id = {str(row["_id"]): row for row in queries}
    qrels: defaultdict[str, set[str]] = defaultdict(set)
    qrel_row_count = 0
    for path in qrel_paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                qrel_row_count += 1
                if float(row["score"]) > 0:
                    qrels[str(row["query-id"])].add(str(row["corpus-id"]))
    unknown = sorted(set(qrels) - set(query_by_id))
    if unknown:
        raise SystemExit(f"Qrels reference unknown query IDs: {unknown[:5]}")

    judged_ids = sorted(qrels, key=lambda value: int(value))
    query_terms = {
        query_id: tokenize(str(query_by_id[query_id]["text"])) for query_id in judged_ids
    }
    indexed_terms = set().union(*(set(terms) for terms in query_terms.values()))
    postings: defaultdict[str, list[tuple[int, int]]] = defaultdict(list)
    document_ids: list[str] = []
    lengths: list[int] = []
    build_started = time.perf_counter()
    with corpus_path.open(encoding="utf-8") as handle:
        for document_index, line in enumerate(handle):
            row = json.loads(line)
            text = " ".join(
                str(row.get(field) or "")
                for field in (
                    "name",
                    "title",
                    "description",
                    "topics",
                    "readme_cleaned",
                    "additional_context",
                )
            )
            tokens = tokenize(text)
            counts = Counter(token for token in tokens if token in indexed_terms)
            for term, frequency in counts.items():
                postings[term].append((document_index, frequency))
            document_ids.append(str(row["_id"]))
            lengths.append(len(tokens))
    build_seconds = time.perf_counter() - build_started
    average_length = statistics.fmean(lengths)

    recalls: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []
    observations: list[dict[str, object]] = []
    k1, b = 1.5, 0.75
    for query_id in judged_ids:
        started = time.perf_counter()
        scores: defaultdict[int, float] = defaultdict(float)
        for term in dict.fromkeys(query_terms[query_id]):
            term_postings = postings.get(term, [])
            document_frequency = len(term_postings)
            if not document_frequency:
                continue
            inverse_frequency = math.log(
                1 + (len(document_ids) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            for index, frequency in term_postings:
                normalization = 1 - b + b * lengths[index] / average_length
                scores[index] += (
                    inverse_frequency * frequency * (k1 + 1) / (frequency + k1 * normalization)
                )
        ranked = heapq.nsmallest(
            args.top_k,
            scores,
            key=lambda index: (-scores[index], document_ids[index]),
        )
        latency_ms = (time.perf_counter() - started) * 1000
        ranking = [document_ids[index] for index in ranked]
        recall, ndcg = _ranking_metrics(ranking, qrels[query_id], args.top_k)
        recalls.append(recall)
        ndcgs.append(ndcg)
        latencies.append(latency_ms)
        observations.append(
            {
                "query_id": query_id,
                "division": query_by_id[query_id].get("metadata", {}).get("division"),
                "relevant_document_count": len(qrels[query_id]),
                "retrieved_document_ids": ranking,
                "recall_at_k": recall,
                "ndcg_at_k": ndcg,
                "latency_ms": latency_ms,
            }
        )

    report = {
        "version": "0.1",
        "status": "completed",
        "evidence_class": "independent_expert_queries",
        "task": "NASA software-repository discovery; not NTRS passage retrieval",
        "repository": receipt["repository"],
        "revision": receipt["revision"],
        "corpus_document_count": len(document_ids),
        "total_query_count": len(queries),
        "judged_query_count": len(judged_ids),
        "unjudged_query_count": len(queries) - len(judged_ids),
        "qrel_row_count": qrel_row_count,
        "top_k": args.top_k,
        "method": "exact BM25 k1=1.5 b=0.75",
        "index_build_seconds": build_seconds,
        "mean_recall_at_k": statistics.fmean(recalls),
        "mean_ndcg_at_k": statistics.fmean(ndcgs),
        "p50_latency_ms": _percentile(latencies, 0.5),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "inputs": {
            "receipt_sha256": _sha256(args.receipt),
            "corpus_sha256": _sha256(corpus_path),
            "queries_sha256": _sha256(queries_path),
            "qrels_sha256": {path.name: _sha256(path) for path in qrel_paths},
        },
        "query_observations": observations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "query_observations"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
