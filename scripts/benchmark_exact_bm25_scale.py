"""Memory-bounded exact BM25 benchmark for large JSONL snapshots."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import re
import statistics
import time
from array import array
from collections import Counter, defaultdict
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")


def rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def resolve_parent_id(record: dict[str, object], chunk_id: str) -> str:
    """Treat a null/blank parent as a root chunk, never as the string 'None'."""

    return str(record.get("parent_chunk_id") or chunk_id)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def evaluate_parent_ranking(
    parents: list[str],
    relevant: set[str],
) -> tuple[float, float]:
    """Score a ranking while allowing each judged parent to contribute once."""

    matched: set[str] = set()
    gains: list[float] = []
    for parent in parents:
        gain = parent in relevant and parent not in matched
        gains.append(1.0 if gain else 0.0)
        if gain:
            matched.add(parent)
    recall = len(matched) / len(relevant)
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(relevant))))
    return recall, dcg / ideal


def best_per_parent(
    touched: set[int],
    scores: array,
    chunk_ids: list[str],
    parent_ids: list[str],
) -> list[int]:
    """Return the best-scoring child for each parent before top-k selection."""

    best: dict[str, int] = {}
    for index in touched:
        parent = parent_ids[index]
        incumbent = best.get(parent)
        if incumbent is None or (-scores[index], chunk_ids[index]) < (
            -scores[incumbent],
            chunk_ids[incumbent],
        ):
            best[parent] = index
    return heapq.nsmallest(
        10,
        best.values(),
        key=lambda index: (-scores[index], chunk_ids[index]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    queries = rows(args.queries)
    qrels = {str(row["query_id"]): set(row["relevant_chunk_ids"]) for row in rows(args.qrels)}
    query_tokens = {
        str(row["query_id"]): TOKEN.findall(str(row["query"]).lower()) for row in queries
    }
    indexed_terms = set().union(*map(set, query_tokens.values()))
    postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
    chunk_ids: list[str] = []
    parent_ids: list[str] = []
    lengths = array("I")
    started = time.perf_counter()
    with args.chunks.open(encoding="utf-8") as handle:
        for document_index, line in enumerate(handle):
            record = json.loads(line)
            tokens = TOKEN.findall(str(record.get("text", "")).lower())
            counts = Counter(token for token in tokens if token in indexed_terms)
            for term, frequency in counts.items():
                postings[term].append((document_index, frequency))
            chunk_id = str(record["chunk_id"])
            chunk_ids.append(chunk_id)
            parent_ids.append(resolve_parent_id(record, chunk_id))
            lengths.append(len(tokens))
    build_seconds = time.perf_counter() - started
    document_count = len(chunk_ids)
    average_length = sum(lengths) / document_count
    top10: dict[str, list[str]] = {}
    top10_parents: dict[str, list[str]] = {}
    collapsed_top10: dict[str, list[str]] = {}
    collapsed_top10_parents: dict[str, list[str]] = {}
    recalls: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []
    collapsed_recalls: list[float] = []
    collapsed_ndcgs: list[float] = []
    collapse_latencies: list[float] = []
    k1, b = 1.5, 0.75
    for query in queries:
        query_id = str(query["query_id"])
        started = time.perf_counter()
        scores = array("d", [0.0]) * document_count
        touched: set[int] = set()
        for term in dict.fromkeys(query_tokens[query_id]):
            term_postings = postings.get(term, [])
            if not term_postings:
                continue
            frequency_documents = len(term_postings)
            inverse_frequency = math.log(
                1 + (document_count - frequency_documents + 0.5) / (frequency_documents + 0.5)
            )
            for index, frequency in term_postings:
                normalization = 1 - b + b * (lengths[index] / average_length)
                scores[index] += (
                    inverse_frequency * frequency * (k1 + 1) / (frequency + k1 * normalization)
                )
                touched.add(index)
        ranked = heapq.nsmallest(10, touched, key=lambda index: (-scores[index], chunk_ids[index]))
        latencies.append((time.perf_counter() - started) * 1000)
        retrieved = [chunk_ids[index] for index in ranked]
        parents = [parent_ids[index] for index in ranked]
        top10[query_id] = retrieved
        top10_parents[query_id] = parents
        relevant = qrels[query_id]
        recall, ndcg = evaluate_parent_ranking(parents, relevant)
        recalls.append(recall)
        ndcgs.append(ndcg)

        collapse_started = time.perf_counter()
        collapsed_ranked = best_per_parent(touched, scores, chunk_ids, parent_ids)
        collapse_latencies.append((time.perf_counter() - collapse_started) * 1000)
        collapsed = [chunk_ids[index] for index in collapsed_ranked]
        collapsed_parents = [parent_ids[index] for index in collapsed_ranked]
        collapsed_top10[query_id] = collapsed
        collapsed_top10_parents[query_id] = collapsed_parents
        collapsed_recall, collapsed_ndcg = evaluate_parent_ranking(
            collapsed_parents,
            relevant,
        )
        collapsed_recalls.append(collapsed_recall)
        collapsed_ndcgs.append(collapsed_ndcg)
    raw_measurement = {
        "corpus_chunks": document_count,
        "query_count": len(queries),
        "method": "exact BM25 k1=1.5 b=0.75 raw segment ranking",
        "index_build_seconds": build_seconds,
        "recall_at_10": statistics.mean(recalls),
        "ndcg_at_10": statistics.mean(ndcgs),
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
    }
    collapsed_measurement = {
        "corpus_chunks": document_count,
        "query_count": len(queries),
        "method": "exact BM25 with best-child-per-parent collapse before top-10",
        "index_build_seconds": build_seconds,
        "recall_at_10": statistics.mean(collapsed_recalls),
        "ndcg_at_10": statistics.mean(collapsed_ndcgs),
        "p50_latency_ms": percentile(
            [base + collapse for base, collapse in zip(latencies, collapse_latencies, strict=True)],
            0.50,
        ),
        "p95_latency_ms": percentile(
            [base + collapse for base, collapse in zip(latencies, collapse_latencies, strict=True)],
            0.95,
        ),
        "p50_collapse_overhead_ms": percentile(collapse_latencies, 0.50),
        "p95_collapse_overhead_ms": percentile(collapse_latencies, 0.95),
    }
    report = {
        "raw_measurement": raw_measurement,
        "parent_collapsed_measurement": collapsed_measurement,
        "top10": top10,
        "top10_parent_chunks": top10_parents,
        "parent_collapsed_top10": collapsed_top10,
        "parent_collapsed_top10_parent_chunks": collapsed_top10_parents,
    }
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    report["report_sha256"] = hashlib.sha256(encoded).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
