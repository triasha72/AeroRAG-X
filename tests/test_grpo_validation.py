"""Tests for post-training/evaluation leakage guards."""

from pathlib import Path

import pytest

from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.validation import (
    build_dataset_manifest,
    validate_case_quality,
    validate_disjoint_case_ids,
    validate_no_near_duplicate_queries,
)


def case(case_id: str, query: str, *, answerable: bool = False) -> GroundedAgentTrainingCase:
    return GroundedAgentTrainingCase(case_id=case_id, query=query, answerable=answerable)


def test_case_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="disjoint"):
        validate_disjoint_case_ids(["train-1", "shared"], ["eval-1", "shared"])


def test_answerable_case_requires_evidence_and_reference() -> None:
    with pytest.raises(ValueError, match="requires evidence"):
        validate_case_quality([case("c1", "query", answerable=True)], label="training")


def test_near_duplicate_query_is_rejected() -> None:
    with pytest.raises(ValueError, match="near duplicates"):
        validate_no_near_duplicate_queries(
            [case("train", "What is the wing span of this aircraft?")],
            [case("eval", "What is the wing-span of this aircraft")],
        )


def test_manifest_freezes_file_hashes(tmp_path: Path) -> None:
    training_path = tmp_path / "training.jsonl"
    evaluation_path = tmp_path / "evaluation.jsonl"
    training_path.write_text("training\n", encoding="utf-8")
    evaluation_path.write_text("evaluation\n", encoding="utf-8")
    manifest = build_dataset_manifest(
        training_path=training_path,
        training_cases=[case("train", "training question")],
        evaluation_path=evaluation_path,
        evaluation_cases=[case("eval", "different protected question")],
    )
    assert manifest.training.case_count == 1
    assert len(manifest.training.sha256) == 64
