"""Run and preserve a collaborator-owned AeroRAG-X evaluation set."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Sequence

from aeroragx.generation.grounded import GroundedAnswerGenerator
from aeroragx.retrieval.reranker import RerankedSearchHit


@dataclass(frozen=True, slots=True)
class ExternalQuestion:
    """Question text supplied by the external evaluator."""

    question_id: str
    question: str


def load_external_questions(path: Path) -> list[ExternalQuestion]:
    """Load non-empty, uniquely identified external questions from JSONL."""

    questions: list[ExternalQuestion] = []
    seen_ids: set[str] = set()

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue

        try:
            row = json.loads(raw_line)
            question_id = str(row["question_id"]).strip()
            question = str(row["question"]).strip()
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid external question on line {line_number}.") from exc

        if not question_id or not question:
            raise ValueError(f"External question on line {line_number} has a blank ID or question.")

        if question_id in seen_ids:
            raise ValueError(f"Duplicate external question ID {question_id!r}.")

        seen_ids.add(question_id)
        questions.append(ExternalQuestion(question_id=question_id, question=question))

    if not questions:
        raise ValueError("External question file must not be empty.")

    return questions


def sha256_file(path: Path) -> str:
    """Return the content digest used to identify a frozen input."""

    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def _hit_record(hit: RerankedSearchHit) -> dict[str, Any]:
    """Keep all ranking and source fields needed for a later retrieval review."""

    return hit.model_dump(mode="json")


def run_external_questions(
    *,
    generator: GroundedAnswerGenerator,
    questions: Sequence[ExternalQuestion],
    reranker_model: str | None,
) -> list[dict[str, Any]]:
    """Run each question once and preserve its pre-generation retrieval evidence."""

    records: list[dict[str, Any]] = []

    for question in questions:
        retrieved = generator.retrieve_for_evaluation(question.question)
        answer = generator.generate(question.question, reranker_model=reranker_model)

        records.append(
            {
                "question_id": question.question_id,
                "question": question.question,
                "answer": answer.model_dump(mode="json"),
                "retrieved_passages": [_hit_record(hit) for hit in retrieved],
            }
        )

    return records


def write_external_run(
    *,
    output_dir: Path,
    records: Sequence[dict[str, Any]],
    system_version: str,
    git_commit: str,
    input_files: dict[str, Path],
) -> None:
    """Write one immutable run directory with a manifest and JSONL records."""

    output_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "system_version": system_version,
        "git_commit": git_commit,
        "input_sha256": {name: sha256_file(path) for name, path in sorted(input_files.items())},
        "question_count": len(records),
    }
    payload = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    output_path = output_dir / "system_outputs.jsonl"
    output_path.write_text(payload, encoding="utf-8")
    trace_rows = [
        {
            "question_id": record["question_id"],
            "retrieved_passages": record["retrieved_passages"],
        }
        for record in records
    ]
    trace_payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in trace_rows)
    trace_path = output_dir / "retrieval_traces.jsonl"
    trace_path.write_text(trace_payload, encoding="utf-8")
    manifest["output_sha256"] = {
        "system_outputs.jsonl": sha256(payload.encode("utf-8")).hexdigest(),
        "retrieval_traces.jsonl": sha256(trace_payload.encode("utf-8")).hexdigest(),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
