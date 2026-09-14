"""Tests for the external-evaluation file boundary."""

from __future__ import annotations

import json

import pytest

from aeroragx.evaluation.external import (
    load_external_questions,
    write_external_run,
)


def test_load_external_questions_rejects_duplicates(tmp_path) -> None:
    path = tmp_path / "questions.jsonl"
    path.write_text(
        "\n".join(
            json.dumps({"question_id": "EXT-1", "question": "Question?"})
            for _ in range(2)
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_external_questions(path)


def test_write_external_run_hashes_inputs_and_outputs(tmp_path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("frozen", encoding="utf-8")
    output_dir = tmp_path / "run"
    record = {
        "question_id": "EXT-1",
        "question": "Question?",
        "answer": {"answer": "Answer"},
        "retrieved_passages": [],
    }

    write_external_run(
        output_dir=output_dir,
        records=[record],
        system_version="v1",
        git_commit="abc",
        input_files={"input": input_file},
    )

    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["question_count"] == 1
    assert manifest["input_sha256"]["input"]
    assert manifest["output_sha256"]["system_outputs.jsonl"]
