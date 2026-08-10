"""Validated training-example schemas and leakage auditing utilities."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aeroragx.generation.provider import ProviderResponse

type LeakageKind = Literal[
    "protected_example_id",
    "exact_query",
    "normalized_query",
    "exact_target_answer",
    "normalized_target_answer",
]


class TrainingEvidence(BaseModel):
    """One provenance-preserving evidence record used during training."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    evidence_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

    document_id: int = Field(ge=1)
    chunk_id: str = Field(min_length=1)


class TrainingExample(BaseModel):
    """One supervised grounded-generation training example."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    example_id: str = Field(min_length=1)
    query: str = Field(min_length=1)

    max_claims: int = Field(
        default=6,
        ge=1,
        le=100,
    )

    evidence: list[TrainingEvidence] = Field(
        min_length=1,
    )

    response: ProviderResponse

    @model_validator(mode="after")
    def validate_grounded_training_example(self) -> Self:
        """Enforce the same grounding invariants used during inference."""

        evidence_ids = [item.evidence_id for item in self.evidence]

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Training evidence IDs must be unique.")

        chunk_ids = [item.chunk_id for item in self.evidence]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Training evidence chunk IDs must be unique.")

        if len(self.response.claims) > self.max_claims:
            raise ValueError("Training response contains more claims than max_claims.")

        if self.response.insufficient_evidence:
            if self.response.claims:
                raise ValueError(
                    "An insufficient-evidence training response must not contain claims."
                )

            return self

        if not self.response.claims:
            raise ValueError("A supported training response must contain at least one claim.")

        valid_evidence_ids = set(evidence_ids)

        for claim in self.response.claims:
            if not claim.evidence_ids:
                raise ValueError(
                    "Every supported training claim must reference at least one evidence ID."
                )

            if len(claim.evidence_ids) != len(set(claim.evidence_ids)):
                raise ValueError("A training claim contains duplicate evidence IDs.")

            unknown_ids = set(claim.evidence_ids) - valid_evidence_ids

            if unknown_ids:
                raise ValueError(
                    "Training response referenced unknown evidence IDs: "
                    + ", ".join(sorted(unknown_ids))
                )

        return self

    @property
    def source_document_ids(self) -> tuple[int, ...]:
        """Return sorted unique source-document IDs."""

        return tuple(sorted({item.document_id for item in self.evidence}))


class LeakageFinding(BaseModel):
    """One detected overlap with protected evaluation material."""

    model_config = ConfigDict(
        extra="forbid",
    )

    kind: LeakageKind

    training_example_id: str = Field(
        min_length=1,
    )

    protected_reference: str = Field(
        min_length=1,
    )


class LeakageAuditReport(BaseModel):
    """Summary of deterministic training-data leakage checks."""

    model_config = ConfigDict(
        extra="forbid",
    )

    training_example_count: int = Field(
        ge=0,
    )

    protected_query_count: int = Field(
        ge=0,
    )

    protected_answer_count: int = Field(
        ge=0,
    )

    findings: list[LeakageFinding]

    @property
    def has_leakage(self) -> bool:
        """Return whether any protected overlap was found."""

        return bool(self.findings)


def load_training_examples(
    path: Path,
) -> list[TrainingExample]:
    """Load validated JSONL training examples."""

    examples: list[TrainingExample] = []

    seen_example_ids: set[str] = set()

    for line_number, raw_line in enumerate(
        path.read_text(
            encoding="utf-8",
        ).splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        try:
            raw_value = json.loads(line)

        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid training JSON on line {line_number} of {path}.") from exc

        try:
            example = TrainingExample.model_validate(raw_value)

        except ValidationError as exc:
            raise ValueError(f"Invalid training example on line {line_number} of {path}.") from exc

        if example.example_id in seen_example_ids:
            raise ValueError(f"Duplicate training example ID {example.example_id!r}.")

        seen_example_ids.add(example.example_id)

        examples.append(example)

    if not examples:
        raise ValueError("Training example file must not be empty.")

    return examples


def write_training_examples(
    path: Path,
    examples: Sequence[TrainingExample],
) -> None:
    """Write deterministic JSONL training examples."""

    if not examples:
        raise ValueError("At least one training example is required.")

    example_ids = [example.example_id for example in examples]

    if len(example_ids) != len(set(example_ids)):
        raise ValueError("Training examples contain duplicate IDs.")

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = "\n".join(example.model_dump_json() for example in examples)

    path.write_text(
        content + "\n",
        encoding="utf-8",
    )


def normalize_training_text(
    value: str,
) -> str:
    """Normalize text for deterministic leakage comparison."""

    return " ".join(value.casefold().split())


def audit_training_leakage(
    examples: Sequence[TrainingExample],
    *,
    protected_queries: Mapping[str, str],
    protected_answers: Mapping[str, str],
) -> LeakageAuditReport:
    """Check deterministic overlap with protected evaluation material."""

    findings: list[LeakageFinding] = []

    protected_query_ids = set(protected_queries)

    exact_query_lookup = _first_reference_lookup(
        protected_queries,
        normalize=False,
    )

    normalized_query_lookup = _first_reference_lookup(
        protected_queries,
        normalize=True,
    )

    exact_answer_lookup = _first_reference_lookup(
        protected_answers,
        normalize=False,
    )

    normalized_answer_lookup = _first_reference_lookup(
        protected_answers,
        normalize=True,
    )

    for example in examples:
        if example.example_id in protected_query_ids:
            findings.append(
                LeakageFinding(
                    kind="protected_example_id",
                    training_example_id=(example.example_id),
                    protected_reference=(example.example_id),
                )
            )

        exact_query_reference = exact_query_lookup.get(example.query)

        if exact_query_reference is not None:
            findings.append(
                LeakageFinding(
                    kind="exact_query",
                    training_example_id=(example.example_id),
                    protected_reference=(exact_query_reference),
                )
            )

        else:
            normalized_query_reference = normalized_query_lookup.get(
                normalize_training_text(example.query)
            )

            if normalized_query_reference is not None:
                findings.append(
                    LeakageFinding(
                        kind="normalized_query",
                        training_example_id=(example.example_id),
                        protected_reference=(normalized_query_reference),
                    )
                )

        if example.response.insufficient_evidence:
            continue

        exact_answer_reference = exact_answer_lookup.get(example.response.answer)

        if exact_answer_reference is not None:
            findings.append(
                LeakageFinding(
                    kind="exact_target_answer",
                    training_example_id=(example.example_id),
                    protected_reference=(exact_answer_reference),
                )
            )

            continue

        normalized_answer_reference = normalized_answer_lookup.get(
            normalize_training_text(example.response.answer)
        )

        if normalized_answer_reference is not None:
            findings.append(
                LeakageFinding(
                    kind="normalized_target_answer",
                    training_example_id=(example.example_id),
                    protected_reference=(normalized_answer_reference),
                )
            )

    return LeakageAuditReport(
        training_example_count=len(examples),
        protected_query_count=(len(protected_queries)),
        protected_answer_count=(len(protected_answers)),
        findings=findings,
    )


def _first_reference_lookup(
    values: Mapping[str, str],
    *,
    normalize: bool,
) -> dict[str, str]:
    """Create deterministic value-to-reference lookup."""

    lookup: dict[str, str] = {}

    for reference in sorted(values):
        value = values[reference]

        key = normalize_training_text(value) if normalize else value

        if not key:
            continue

        lookup.setdefault(
            key,
            reference,
        )

    return lookup
