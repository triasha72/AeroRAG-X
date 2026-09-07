"""Parsers and summaries for the official TREC 2024 RAG judgments."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_topics(path: Path) -> dict[str, str]:
    topics: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            topic_id, question = line.split("\t", 1)
        except ValueError as error:
            raise ValueError(f"Invalid topic row at line {number}") from error
        if topic_id in topics:
            raise ValueError(f"Duplicate topic ID: {topic_id}")
        topics[topic_id] = question.strip()
    return topics


def summarize_trec_rag(
    topics_path: Path, retrieval_qrels_path: Path, citation_judgments_path: Path
) -> dict[str, Any]:
    topics = load_topics(topics_path)
    retrieval_labels: Counter[int] = Counter()
    judged_topics: set[str] = set()
    judged_documents: set[str] = set()
    for number, line in enumerate(
        retrieval_qrels_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 4:
            raise ValueError(f"Invalid qrels row at line {number}")
        topic_id, _, document_id, label_text = fields
        if topic_id not in topics:
            raise ValueError(f"Unknown qrels topic: {topic_id}")
        label = int(label_text)
        retrieval_labels[label] += 1
        judged_topics.add(topic_id)
        judged_documents.add(document_id)

    support_labels: Counter[int] = Counter()
    citation_topics: set[str] = set()
    run_ids: set[str] = set()
    citation_count = 0
    for number, line in enumerate(
        citation_judgments_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        topic_id = str(row["topic_id"])
        if topic_id not in topics:
            raise ValueError(f"Unknown citation topic at line {number}: {topic_id}")
        citation_topics.add(topic_id)
        run_ids.add(str(row["run_id"]))
        for sentence in row.get("sentences", []):
            for citation in sentence.get("citations", []):
                support_labels[int(citation["support"])] += 1
                citation_count += 1

    return {
        "schema_version": "1.0",
        "dataset_id": "NIST/TREC-2024-RAG",
        "evidence_role": "external_public_human_judgments",
        "topics": len(topics),
        "retrieval": {
            "judged_topics": len(judged_topics),
            "judgment_rows": sum(retrieval_labels.values()),
            "unique_documents": len(judged_documents),
            "labels": {str(key): value for key, value in sorted(retrieval_labels.items())},
        },
        "citations": {
            "judged_topics": len(citation_topics),
            "runs": len(run_ids),
            "judgment_rows": citation_count,
            "support_labels": {str(key): value for key, value in sorted(support_labels.items())},
        },
        "source_sha256": {
            "topics": sha256(topics_path),
            "retrieval_qrels": sha256(retrieval_qrels_path),
            "citation_judgments": sha256(citation_judgments_path),
        },
        "contains_source_text": False,
        "claim_scope": "benchmark readiness and judgment-distribution audit",
        "limitations": [
            "The MS MARCO passage corpus is not redistributed by this repository.",
            "These public judgments are independent but are not aerospace-specific.",
            (
                "This artifact does not claim an AeroRAG-X score until a retrieval run "
                "uses the same corpus."
            ),
        ],
    }
