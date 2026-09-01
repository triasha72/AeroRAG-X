#!/usr/bin/env python3
"""Build a reproducible 512-case retrieval-scale set with explicit review status."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

STOP = {
    "about", "after", "also", "been", "between", "could", "from", "have",
    "into", "more", "other", "results", "such", "system", "than", "that",
    "their", "there", "these", "they", "this", "through", "using", "were",
    "which", "with", "would", "figure", "table", "nasa", "report",
}
TOKEN = re.compile(r"[a-z][a-z0-9-]{3,}")


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/ntrs/v0_1/chunks.jsonl"))
    parser.add_argument("--count", type=int, default=512)
    parser.add_argument("--queries-output", type=Path, default=Path("data/evaluation/source_grounded_queries_v0_1_512.jsonl"))
    parser.add_argument("--qrels-output", type=Path, default=Path("data/evaluation/source_grounded_qrels_v0_1_512.jsonl"))
    parser.add_argument("--review-output", type=Path, default=Path("data/evaluation/source_grounded_review_v0_1_512.template.jsonl"))
    parser.add_argument("--manifest-output", type=Path, default=Path("data/evaluation/source_grounded_eval_v0_1_512_manifest.json"))
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def terms(text: str) -> list[str]:
    return [word for word in TOKEN.findall(text.casefold()) if word not in STOP]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config = args()
    if config.count < 500:
        raise SystemExit("The scale-evaluation contract requires at least 500 cases.")
    chunks = load_rows(config.chunks)
    eligible = [row for row in chunks if len(set(terms(str(row["text"])))) >= 6]
    document_frequency: Counter[str] = Counter()
    for row in eligible:
        document_frequency.update(set(terms(str(row["text"]))))

    by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_document[str(row["document_id"])].append(row)
    for rows in by_document.values():
        rows.sort(key=lambda row: (int(row["chunk_index"]), str(row["chunk_id"])))

    selected: list[dict[str, Any]] = []
    document_ids = sorted(by_document)
    offset = 0
    while len(selected) < config.count:
        added = False
        for document_id in document_ids:
            rows = by_document[document_id]
            if offset < len(rows):
                selected.append(rows[offset])
                added = True
                if len(selected) == config.count:
                    break
        if not added:
            raise SystemExit(f"Only {len(selected)} eligible distinct chunks are available.")
        offset += 1

    queries: list[dict[str, Any]] = []
    qrels: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    corpus_size = len(eligible)
    for number, row in enumerate(selected, start=1):
        counts = Counter(terms(str(row["text"])))
        ranked = sorted(
            counts,
            key=lambda word: (
                -(counts[word] * math.log((corpus_size + 1) / (document_frequency[word] + 1))),
                word,
            ),
        )
        keywords = ranked[:6]
        query_id = f"src512_{number:04d}"
        query = "What does the NASA source report about " + ", ".join(keywords) + "?"
        queries.append(
            {
                "query_id": query_id,
                "query": query,
                "construction": "deterministic_source_keyword_v0.1",
                "review_status": "automatic_candidate_not_human_validated",
                "source_document_id": str(row["document_id"]),
                "source_chunk_id": str(row["chunk_id"]),
                "source_page_start": row.get("page_start"),
                "source_page_end": row.get("page_end"),
                "expected_terms": keywords,
            }
        )
        qrels.append({"query_id": query_id, "relevant_chunk_ids": [str(row["chunk_id"])]})
        reviews.append(
            {
                "query_id": query_id,
                "reviewer_id": None,
                "query_is_clear": None,
                "source_supports_query": None,
                "relevant_chunk_correct": None,
                "decision": "PENDING",
                "notes": "",
            }
        )

    write_jsonl(config.queries_output, queries)
    write_jsonl(config.qrels_output, qrels)
    write_jsonl(config.review_output, reviews)
    manifest = {
        "version": "0.1",
        "status": "candidate_requires_independent_review",
        "case_count": len(queries),
        "document_count": len({row["source_document_id"] for row in queries}),
        "construction": "deterministic_source_keyword_v0.1",
        "allowed_claim": "retrieval-scale diagnostic after reporting automatic construction",
        "prohibited_claim": "independently validated generation quality benchmark",
        "chunks_sha256": sha(config.chunks),
        "queries_sha256": sha(config.queries_output),
        "qrels_sha256": sha(config.qrels_output),
        "review_template_sha256": sha(config.review_output),
    }
    config.manifest_output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
