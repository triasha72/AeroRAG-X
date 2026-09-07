import json
import subprocess
import sys
from pathlib import Path


def test_checked_in_corruption_suite_rejects_wrong_source_ids() -> None:
    root = Path(__file__).parents[1]
    summary = json.loads(
        (root / "artifacts/evaluation/citation_corruption_summary_v1.json").read_text()
    )
    assert summary["case_count"] == 200
    assert summary["detection_rate"] == 1.0
    assert summary["decision"] == "passed"


def test_corruption_builder_is_reproducible(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/build_citation_corruption_suite.py",
            "--queries",
            "data/evaluation/source_grounded_queries_v0_1_512.jsonl",
            "--qrels",
            "data/evaluation/source_grounded_qrels_v0_1_512.jsonl",
            "--retrieval",
            "artifacts/evaluation/source_grounded_reranker_v0_1_512.json",
            "--output",
            str(tmp_path / "cases.jsonl"),
            "--summary-output",
            str(tmp_path / "summary.json"),
        ],
        check=True,
    )
    assert json.loads((tmp_path / "summary.json").read_text())["detected"] == 200
