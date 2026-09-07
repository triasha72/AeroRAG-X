#!/usr/bin/env python3
"""Evaluate lexical retrieval against SciFact's human evidence annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from aeroragx.evaluation.scifact import normalize_claims, normalize_corpus


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    documents = normalize_corpus(read_jsonl(args.corpus))
    claims = normalize_claims(read_jsonl(args.claims))
    doc_ids = np.asarray([document.doc_id for document in documents])
    texts = [f"{document.title} {' '.join(document.abstract)}" for document in documents]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    query_matrix = vectorizer.transform([claim.text for claim in claims])
    any_at = {1: 0, 5: 0, 10: 0}
    reciprocal_ranks = []
    for index, claim in enumerate(claims):
        order = np.asarray((query_matrix[index] @ matrix.T).toarray()).ravel().argsort()[::-1]
        ranked_ids = doc_ids[order]
        positions = [
            int(np.flatnonzero(ranked_ids == doc_id)[0]) + 1
            for doc_id in claim.evidence_doc_ids
            if np.any(ranked_ids == doc_id)
        ]
        if not positions:
            reciprocal_ranks.append(0.0)
            continue
        best = min(positions)
        reciprocal_ranks.append(1 / best)
        for cutoff in any_at:
            any_at[cutoff] += int(best <= cutoff)
    count = len(claims)
    payload = {
        "schema_version": "1.0",
        "dataset_id": "allenai/scifact",
        "dataset_license": {"claims_and_evidence": "CC-BY-4.0", "corpus": "ODC-By-1.0"},
        "split": "validation",
        "corpus_sha256": sha256(args.corpus),
        "claims_sha256": sha256(args.claims),
        "retriever": "global TF-IDF word 1-2 grams",
        "documents": len(documents),
        "evaluated_claims": count,
        "mean_reciprocal_rank": float(np.mean(reciprocal_ranks)),
        "any_evidence_document_recall_at_k": {
            str(cutoff): hits / count for cutoff, hits in any_at.items()
        },
        "contains_source_text": False,
        "limitations": [
            "SciFact covers scientific abstracts, not NASA aerospace reports.",
            "This run measures document retrieval, not generated-answer correctness.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
