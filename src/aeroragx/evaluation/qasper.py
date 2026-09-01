"""QASPER human-evidence normalization for external retrieval evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class QasperQuestion:
    question_id: str
    question: str
    evidence_paragraph_indices: frozenset[int]
    annotation_count: int


def normalize_text(value: str) -> str:
    return _SPACE.sub(" ", value).strip().casefold()


def paper_paragraphs(paper: dict[str, Any]) -> list[str]:
    return [
        paragraph.strip()
        for section in paper["full_text"]
        for paragraph in section["paragraphs"]
        if paragraph.strip()
    ]


def evidence_indices(paragraphs: list[str], evidence: list[str]) -> frozenset[int]:
    normalized = [normalize_text(paragraph) for paragraph in paragraphs]
    matches: set[int] = set()
    for span in evidence:
        target = normalize_text(span)
        if not target:
            continue
        for index, paragraph in enumerate(normalized):
            if target in paragraph or paragraph in target:
                matches.add(index)
    return frozenset(matches)


def answerable_questions(paper: dict[str, Any]) -> tuple[QasperQuestion, ...]:
    paragraphs = paper_paragraphs(paper)
    questions: list[QasperQuestion] = []
    for qa in paper["qas"]:
        answerable = [item for item in qa["answers"] if not item["answer"]["unanswerable"]]
        if not answerable:
            continue
        evidence = [span for item in answerable for span in item["answer"]["evidence"]]
        indices = evidence_indices(paragraphs, evidence)
        if not indices:
            continue
        questions.append(
            QasperQuestion(
                question_id=str(qa["question_id"]),
                question=str(qa["question"]).strip(),
                evidence_paragraph_indices=indices,
                annotation_count=len(answerable),
            )
        )
    return tuple(questions)
