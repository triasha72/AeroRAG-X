"""Quality and leakage guards for GRPO experiment datasets."""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase


class DatasetFileManifest(BaseModel):
    """Frozen identity and composition of one case file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_count: int = Field(ge=1)
    answerable_count: int = Field(ge=0)
    unanswerable_count: int = Field(ge=0)


class GRPODatasetManifest(BaseModel):
    """Evidence that training and protected evaluation inputs were validated."""

    model_config = ConfigDict(extra="forbid")

    version: str = "v0_1"
    near_duplicate_threshold: float
    training: DatasetFileManifest
    protected_evaluation: DatasetFileManifest


def validate_disjoint_case_ids(
    training_case_ids: Iterable[str],
    evaluation_case_ids: Iterable[str],
) -> None:
    """Reject any case-ID overlap between post-training and frozen evaluation."""

    training = set(training_case_ids)
    evaluation = set(evaluation_case_ids)
    overlap = sorted(training & evaluation)
    if overlap:
        raise ValueError(f"GRPO training/evaluation case IDs must be disjoint: {overlap}")


def _normalized_query(value: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in value).split())


def validate_case_quality(cases: list[GroundedAgentTrainingCase], *, label: str) -> None:
    """Reject duplicate IDs and internally inconsistent answer/evidence contracts."""

    case_ids = [case.case_id for case in cases]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"{label} contains duplicate case IDs: {duplicates}")

    normalized_queries: set[str] = set()
    for case in cases:
        normalized = _normalized_query(case.query)
        if normalized in normalized_queries:
            raise ValueError(f"{label} contains a duplicate normalized query: {case.case_id}")
        normalized_queries.add(normalized)

        evidence_ids = [item.evidence_id for item in case.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError(f"{label} case {case.case_id} contains duplicate evidence IDs")
        missing_citations = sorted(set(case.expected_citation_ids) - set(evidence_ids))
        if missing_citations:
            raise ValueError(
                f"{label} case {case.case_id} cites unknown evidence IDs: {missing_citations}"
            )
        if case.answerable and (not case.evidence or not case.reference_answer):
            raise ValueError(
                f"{label} answerable case {case.case_id} requires evidence and a reference answer"
            )
        if not case.answerable and (case.reference_answer or case.expected_citation_ids):
            raise ValueError(
                f"{label} unanswerable case {case.case_id} cannot define an answer or citations"
            )


def validate_no_near_duplicate_queries(
    training_cases: list[GroundedAgentTrainingCase],
    evaluation_cases: list[GroundedAgentTrainingCase],
    *,
    threshold: float = 0.92,
) -> None:
    """Reject likely paraphrase leakage across the train/evaluation boundary."""

    for training_case in training_cases:
        training_query = _normalized_query(training_case.query)
        for evaluation_case in evaluation_cases:
            ratio = SequenceMatcher(
                None, training_query, _normalized_query(evaluation_case.query)
            ).ratio()
            if ratio >= threshold:
                raise ValueError(
                    "GRPO training/evaluation queries are near duplicates: "
                    f"{training_case.case_id}, {evaluation_case.case_id} ({ratio:.3f})"
                )


def _file_manifest(path: Path, cases: list[GroundedAgentTrainingCase]) -> DatasetFileManifest:
    return DatasetFileManifest(
        path=str(path),
        sha256=sha256(path.read_bytes()).hexdigest(),
        case_count=len(cases),
        answerable_count=sum(case.answerable for case in cases),
        unanswerable_count=sum(not case.answerable for case in cases),
    )


def build_dataset_manifest(
    *,
    training_path: Path,
    training_cases: list[GroundedAgentTrainingCase],
    evaluation_path: Path,
    evaluation_cases: list[GroundedAgentTrainingCase],
    near_duplicate_threshold: float = 0.92,
) -> GRPODatasetManifest:
    """Validate both splits and return their reproducible identities."""

    validate_case_quality(training_cases, label="training")
    validate_case_quality(evaluation_cases, label="protected evaluation")
    validate_disjoint_case_ids(
        (case.case_id for case in training_cases),
        (case.case_id for case in evaluation_cases),
    )
    validate_no_near_duplicate_queries(
        training_cases,
        evaluation_cases,
        threshold=near_duplicate_threshold,
    )
    return GRPODatasetManifest(
        near_duplicate_threshold=near_duplicate_threshold,
        training=_file_manifest(training_path, training_cases),
        protected_evaluation=_file_manifest(evaluation_path, evaluation_cases),
    )
