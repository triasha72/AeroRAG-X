import json
import subprocess
import sys
from pathlib import Path


def test_author_audit_is_sampled_and_role_is_disclosed(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    subprocess.run(
        [sys.executable, "scripts/build_author_error_audit.py", "--output", str(target)],
        check=True,
    )
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert len(rows) == 50
    assert {row["reviewer_role"] for row in rows} == {"project_author"}
    assert all(row["answer_supported"] is None for row in rows)
    assert all(row["query"] for row in rows)
    assert all(row["judged_relevant_chunk_ids"] for row in rows)
    assert all(len(row["retrieved_chunk_ids"]) == 10 for row in rows)
