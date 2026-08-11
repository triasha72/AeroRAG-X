import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

V01_PATH = ROOT / "data" / "evaluation" / "semantic_match_calibration_v0_1.jsonl"

V02_PATH = ROOT / "data" / "evaluation" / "semantic_match_calibration_v0_2.jsonl"


def load_rows(
    path: Path,
) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_hard_calibration_dataset_is_balanced() -> None:
    rows = load_rows(V02_PATH)

    assert len(rows) == 90

    labels = Counter(str(row["label"]) for row in rows)

    assert labels == {
        "MATCH": 45,
        "NO_MATCH": 45,
    }

    concepts = {str(row["concept_id"]) for row in rows}

    assert len(concepts) == 45

    pair_ids = {str(row["pair_id"]) for row in rows}

    assert len(pair_ids) == 90


def test_hard_calibration_preserves_v01_positives() -> None:
    v01 = load_rows(V01_PATH)
    v02 = load_rows(V02_PATH)

    v01_positive = {
        (
            str(row["concept_id"]),
            str(row["reference_text"]),
            str(row["candidate_text"]),
        )
        for row in v01
        if row["label"] == "MATCH"
    }

    v02_positive = {
        (
            str(row["concept_id"]),
            str(row["reference_text"]),
            str(row["candidate_text"]),
        )
        for row in v02
        if row["label"] == "MATCH"
    }

    assert len(v01_positive) == 45
    assert v02_positive == v01_positive
