import json
from pathlib import Path

import pytest

from aeroragx.evaluation.semantic import (
    ExpectedConcept,
    SemanticQueryAnnotation,
    evaluate_alias_concept_coverage,
    load_semantic_annotations,
    normalize_semantic_text,
)


def test_normalize_semantic_text() -> None:
    assert normalize_semantic_text("Cell-to-Cell Thermal Runaway") == "cell to cell thermal runaway"


def test_expected_concept_rejects_duplicate_phrase() -> None:
    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        ExpectedConcept(
            concept_id="thermal_runaway",
            canonical_text="thermal runaway",
            accepted_phrases=[
                "Thermal   Runaway",
            ],
        )


def test_semantic_annotation_rejects_duplicate_ids() -> None:
    concept = ExpectedConcept(
        concept_id="thermal_runaway",
        canonical_text="thermal runaway",
    )

    with pytest.raises(
        ValueError,
        match="concept IDs must be unique",
    ):
        SemanticQueryAnnotation(
            query_id="core_001",
            expected_concepts=[
                concept,
                concept,
            ],
        )


def test_alias_coverage_matches_canonical_and_alias() -> None:
    annotation = SemanticQueryAnnotation(
        query_id="core_001",
        expected_concepts=[
            ExpectedConcept(
                concept_id="thermal_runaway",
                canonical_text="thermal runaway",
            ),
            ExpectedConcept(
                concept_id="cell_propagation",
                canonical_text=("cell to cell propagation"),
                accepted_phrases=[
                    "cascade into neighboring cells",
                ],
            ),
        ],
    )

    result = evaluate_alias_concept_coverage(
        answer=("Thermal runaway may cascade into neighboring cells."),
        annotation=annotation,
    )

    assert result.concept_count == 2
    assert result.matched_concept_count == 2
    assert result.semantic_concept_coverage == 1.0
    assert result.concept_matches[0].match_method == "canonical"
    assert result.concept_matches[1].match_method == "alias"


def test_alias_coverage_records_unmatched_concept() -> None:
    annotation = SemanticQueryAnnotation(
        query_id="core_001",
        expected_concepts=[
            ExpectedConcept(
                concept_id="thermal_runaway",
                canonical_text="thermal runaway",
            ),
            ExpectedConcept(
                concept_id="containment",
                canonical_text="battery containment",
            ),
        ],
    )

    result = evaluate_alias_concept_coverage(
        answer="Thermal runaway can propagate.",
        annotation=annotation,
    )

    assert result.matched_concept_count == 1
    assert result.semantic_concept_coverage == 0.5

    unmatched = result.concept_matches[1]

    assert unmatched.matched is False
    assert unmatched.match_method is None
    assert unmatched.matched_phrase is None


def test_load_semantic_annotations(tmp_path: Path) -> None:
    path = tmp_path / "semantic.jsonl"

    path.write_text(
        json.dumps(
            {
                "query_id": "core_001",
                "expected_concepts": [
                    {
                        "concept_id": ("thermal_runaway"),
                        "canonical_text": ("thermal runaway"),
                        "accepted_phrases": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    annotations = load_semantic_annotations(path)

    assert len(annotations) == 1
    assert annotations[0].query_id == "core_001"


def test_loader_rejects_duplicate_query_ids(
    tmp_path: Path,
) -> None:
    path = tmp_path / "semantic.jsonl"

    row = {
        "query_id": "core_001",
        "expected_concepts": [
            {
                "concept_id": "thermal_runaway",
                "canonical_text": ("thermal runaway"),
                "accepted_phrases": [],
            }
        ],
    }

    path.write_text(
        json.dumps(row) + "\n" + json.dumps(row) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate semantic query ID",
    ):
        load_semantic_annotations(path)
