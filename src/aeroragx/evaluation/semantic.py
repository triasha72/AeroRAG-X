"""Semantic-quality evaluation primitives for frozen generation outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

type ConceptMatchMethod = Literal[
    "canonical",
    "alias",
]


class ExpectedConcept(BaseModel):
    """One technical concept expected in an answer."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    concept_id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9][a-z0-9_]*$",
    )
    canonical_text: str = Field(min_length=1)
    accepted_phrases: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_phrases(self) -> Self:
        """Reject blank and duplicate semantic formulations."""

        phrases = [
            self.canonical_text,
            *self.accepted_phrases,
        ]

        normalized = [normalize_semantic_text(value) for value in phrases]

        if any(not value for value in normalized):
            raise ValueError("Semantic concept phrases must not be blank.")

        if len(normalized) != len(set(normalized)):
            raise ValueError("Semantic concept phrases must be unique after normalization.")

        return self


class SemanticQueryAnnotation(BaseModel):
    """Expected concepts for one protected answerable query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(min_length=1)
    expected_concepts: list[ExpectedConcept] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_concepts(self) -> Self:
        """Reject duplicate concept identifiers."""

        concept_ids = [concept.concept_id for concept in self.expected_concepts]

        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("Semantic concept IDs must be unique within each query.")

        return self


class ConceptMatch(BaseModel):
    """One deterministic concept-match decision."""

    model_config = ConfigDict(extra="forbid")

    concept_id: str
    matched: bool
    match_method: ConceptMatchMethod | None = None
    matched_phrase: str | None = None


class SemanticQueryResult(BaseModel):
    """Semantic concept coverage for one answer."""

    model_config = ConfigDict(extra="forbid")

    query_id: str
    concept_count: int = Field(ge=1)
    matched_concept_count: int = Field(ge=0)
    semantic_concept_coverage: float = Field(
        ge=0.0,
        le=1.0,
    )
    concept_matches: list[ConceptMatch]


def normalize_semantic_text(value: str) -> str:
    """Normalize text for deterministic phrase matching."""

    casefolded = value.casefold()

    punctuation_normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        casefolded,
    )

    return " ".join(punctuation_normalized.split())


def load_semantic_annotations(
    path: Path,
) -> list[SemanticQueryAnnotation]:
    """Load versioned semantic annotations from JSONL."""

    annotations: list[SemanticQueryAnnotation] = []
    seen_query_ids: set[str] = set()

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        try:
            raw_value = json.loads(line)

        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number} of {path}.") from exc

        try:
            annotation = SemanticQueryAnnotation.model_validate(raw_value)

        except ValidationError as exc:
            raise ValueError(
                f"Invalid semantic annotation on line {line_number} of {path}."
            ) from exc

        if annotation.query_id in seen_query_ids:
            raise ValueError(f"Duplicate semantic query ID {annotation.query_id!r}.")

        seen_query_ids.add(annotation.query_id)
        annotations.append(annotation)

    if not annotations:
        raise ValueError("Semantic annotation file must not be empty.")

    return annotations


def evaluate_alias_concept_coverage(
    *,
    answer: str,
    annotation: SemanticQueryAnnotation,
) -> SemanticQueryResult:
    """Evaluate deterministic canonical/alias concept coverage."""

    normalized_answer = normalize_semantic_text(answer)

    matches: list[ConceptMatch] = []

    for concept in annotation.expected_concepts:
        candidates: list[tuple[ConceptMatchMethod, str]] = [
            (
                "canonical",
                concept.canonical_text,
            ),
            *[("alias", phrase) for phrase in concept.accepted_phrases],
        ]

        concept_match: ConceptMatch | None = None

        for match_method, phrase in candidates:
            normalized_phrase = normalize_semantic_text(phrase)

            if normalized_phrase in normalized_answer:
                concept_match = ConceptMatch(
                    concept_id=concept.concept_id,
                    matched=True,
                    match_method=match_method,
                    matched_phrase=phrase,
                )
                break

        if concept_match is None:
            concept_match = ConceptMatch(
                concept_id=concept.concept_id,
                matched=False,
            )

        matches.append(concept_match)

    matched_count = sum(match.matched for match in matches)

    concept_count = len(matches)

    return SemanticQueryResult(
        query_id=annotation.query_id,
        concept_count=concept_count,
        matched_concept_count=matched_count,
        semantic_concept_coverage=(matched_count / concept_count),
        concept_matches=matches,
    )
