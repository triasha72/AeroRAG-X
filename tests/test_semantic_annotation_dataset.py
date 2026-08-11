import json
from pathlib import Path

from aeroragx.evaluation.semantic import (
    load_semantic_annotations,
)

ROOT = Path(__file__).resolve().parents[1]

QUERY_PATH = ROOT / "data" / "evaluation" / "generation_queries_v0_3.jsonl"

ANNOTATION_PATH = ROOT / "data" / "evaluation" / "generation_semantic_concepts_v0_1.jsonl"


def test_semantic_annotations_cover_protected_answerable_queries() -> None:
    query_rows = [
        json.loads(line)
        for line in QUERY_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    expected_ids = [row["query_id"] for row in query_rows if row["expected_answerable"]]

    unsupported_ids = {row["query_id"] for row in query_rows if not row["expected_answerable"]}

    annotations = load_semantic_annotations(ANNOTATION_PATH)

    annotation_ids = [annotation.query_id for annotation in annotations]

    assert len(expected_ids) == 20
    assert annotation_ids == expected_ids
    assert not (set(annotation_ids) & unsupported_ids)

    for annotation in annotations:
        assert 2 <= len(annotation.expected_concepts) <= 5
