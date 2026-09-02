#!/usr/bin/env python3
"""Run a frozen lexical retrieval baseline on QASPER human evidence spans."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from aeroragx.evaluation.qasper import answerable_questions, paper_paragraphs


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    papers = json.loads(args.data.read_text())
    ranks: list[int] = []
    complete_at = {5: 0, 10: 0, 20: 0}
    any_at = {5: 0, 10: 0, 20: 0}
    annotation_counts: list[int] = []
    skipped_unmatched_or_unanswerable = 0

    for paper in papers.values():
        paragraphs = paper_paragraphs(paper)
        questions = answerable_questions(paper)
        skipped_unmatched_or_unanswerable += len(paper["qas"]) - len(questions)
        if not questions or not paragraphs:
            continue
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        paragraph_matrix = vectorizer.fit_transform(paragraphs)
        question_matrix = vectorizer.transform([item.question for item in questions])
        scores = question_matrix @ paragraph_matrix.T
        for row_index, question in enumerate(questions):
            order = np.asarray(scores[row_index].toarray()).ravel().argsort()[::-1]
            positions = sorted(
                int(np.flatnonzero(order == evidence_index)[0]) + 1
                for evidence_index in question.evidence_paragraph_indices
            )
            ranks.append(positions[0])
            annotation_counts.append(question.annotation_count)
            for k in complete_at:
                any_at[k] += int(positions[0] <= k)
                complete_at[k] += int(positions[-1] <= k)

    count = len(ranks)
    if not count:
        raise ValueError("No answerable QASPER questions with matched evidence found")
    payload = {
        "schema_version": "1.0",
        "dataset_id": "allenai/qasper",
        "dataset_version": "0.3.0",
        "dataset_license": "CC-BY-4.0",
        "split": "validation",
        "source_sha256": sha256(args.data),
        "retriever": "within-paper TF-IDF word 1-2 grams",
        "papers": len(papers),
        "evaluated_questions": count,
        "skipped_unanswerable_or_unmatched_questions": skipped_unmatched_or_unanswerable,
        "mean_human_annotations_per_question": float(np.mean(annotation_counts)),
        "mean_reciprocal_rank": float(np.mean(1 / np.asarray(ranks))),
        "any_evidence_recall_at_k": {str(k): any_at[k] / count for k in any_at},
        "complete_evidence_recall_at_k": {str(k): complete_at[k] / count for k in complete_at},
        "contains_source_text": False,
        "limitations": [
            "QASPER covers NLP papers, not NASA aerospace reports.",
            "This run evaluates within-paper evidence retrieval, not answer generation.",
            "Evidence spans that could not be matched to a full-text paragraph "
            "are excluded and counted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
