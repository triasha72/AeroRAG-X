import json
from pathlib import Path

from aeroragx.evaluation.semantic import (
    load_semantic_annotations,
    normalize_semantic_text,
)

ROOT = Path(__file__).resolve().parents[1]

ANNOTATION_PATH = ROOT / "data" / "evaluation" / "generation_semantic_concepts_v0_1.jsonl"

CALIBRATION_PATH = ROOT / "data" / "evaluation" / "semantic_match_calibration_v0_1.jsonl"


def test_semantic_similarity_calibration_dataset() -> None:
    annotations = load_semantic_annotations(ANNOTATION_PATH)

    known_concepts = {
        concept.concept_id for annotation in annotations for concept in annotation.expected_concepts
    }

    rows = [
        json.loads(line)
        for line in CALIBRATION_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert rows

    pair_ids = [row["pair_id"] for row in rows]

    assert len(pair_ids) == len(set(pair_ids))

    labels = [row["label"] for row in rows]

    assert set(labels) == {
        "MATCH",
        "NO_MATCH",
    }

    assert labels.count("MATCH") == labels.count("NO_MATCH")

    for row in rows:
        assert row["concept_id"] in known_concepts

        assert row["reference_text"].strip()
        assert row["candidate_text"].strip()

        if row["label"] == "NO_MATCH":
            assert normalize_semantic_text(row["reference_text"]) != normalize_semantic_text(
                row["candidate_text"]
            )
