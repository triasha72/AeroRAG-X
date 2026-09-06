import json
import subprocess
import sys
from pathlib import Path


def test_builds_two_matching_source_grounded_pilots(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/build_source_grounded_review_pilot.py",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
    )
    first = (tmp_path / "source_grounded_pilot_reviewer_a.jsonl").read_text()
    second = (tmp_path / "source_grounded_pilot_reviewer_b.jsonl").read_text()
    assert first == second
    rows = [json.loads(line) for line in first.splitlines()]
    assert len(rows) == 25
    assert all(row["decision"] == "PENDING" for row in rows)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["full_study_cases"] == 512
    assert manifest["human_reviews_completed"] is False
