#!/usr/bin/env python3
"""Build the frozen unsupported-response taxonomy review queue."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "base_closed_book": (
        ROOT / "artifacts" / "evaluation" / "generation_transformers_base_closed_book_v0_2.json"
    ),
    "lora_closed_book": (
        ROOT / "artifacts" / "evaluation" / "generation_transformers_lora_closed_book_v0_2.json"
    ),
    "base_rag": (ROOT / "artifacts" / "evaluation" / "generation_transformers_base_v0_3.json"),
    "lora_rag": (ROOT / "artifacts" / "evaluation" / "generation_transformers_lora_v0_3.json"),
}

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_units_v0_1.jsonl"

PENDING_PATH = (
    ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_review_pending_v0_1.md"
)

BATCH_DIR = ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_review_batches_v0_1"

EXPECTED_UNSUPPORTED_PER_CONDITION = 12
EXPECTED_TOTAL_ROWS = 48

ALLOWED_LABELS = {
    "EXPLICIT_REFUSAL",
    "CORRECTIVE_DENIAL",
    "UNSUPPORTED_ASSERTION",
    "STRUCTURAL_FAILURE",
}

BATCH_SIZE = 4


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected JSON object.")
    return value


def append_unit(
    target: list[str],
    unit: dict[str, object],
) -> None:
    target.extend(
        [
            "---",
            "",
            f"## {unit['unit_id']}",
            "",
            f"**Query ID:** {unit['query_id']}",
            "",
            f"**Unsupported benchmark query:** {unit['query']}",
            "",
        ]
    )

    responses = unit["responses"]
    if not isinstance(responses, list):
        raise TypeError("responses must be a list.")

    for response in responses:
        if not isinstance(response, dict):
            raise TypeError("response must be a mapping.")

        target.extend(
            [
                f"### {response['condition']}",
                "",
                (
                    "**Existing metadata:** "
                    f"predicted_answerable={response['predicted_answerable']}; "
                    f"generation_failed={response['generation_failed']}; "
                    f"structurally_valid={response['structurally_valid']}; "
                    f"insufficient_evidence={response['insufficient_evidence']}"
                ),
                "",
                "**Frozen response:**",
                "",
                str(response["answer"]),
                "",
                (
                    "**Decision:** `EXPLICIT_REFUSAL / "
                    "CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / "
                    "STRUCTURAL_FAILURE`"
                ),
                "",
                "**Note:**",
                "",
            ]
        )


def main() -> None:
    source_rows: dict[str, list[dict[str, object]]] = {}
    source_summaries: dict[str, dict[str, object]] = {}

    canonical_query_order: list[str] | None = None
    canonical_queries: dict[str, str] = {}

    for condition, path in SOURCES.items():
        payload = load_json(path)

        query_results = payload.get("query_results")
        if not isinstance(query_results, list):
            raise TypeError(f"{condition}: query_results must be a list.")

        if len(query_results) != 32:
            raise RuntimeError(
                f"{condition}: expected 32 query results; found {len(query_results)}."
            )

        unsupported: list[dict[str, object]] = []

        for row in query_results:
            if not isinstance(row, dict):
                raise TypeError(f"{condition}: query result must be a mapping.")

            if row.get("expected_answerable") is False:
                unsupported.append(row)

        if len(unsupported) != EXPECTED_UNSUPPORTED_PER_CONDITION:
            raise RuntimeError(
                f"{condition}: expected "
                f"{EXPECTED_UNSUPPORTED_PER_CONDITION} unsupported "
                f"queries; found {len(unsupported)}."
            )

        ids = [str(row["query_id"]) for row in unsupported]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{condition}: duplicate unsupported query IDs.")

        if canonical_query_order is None:
            canonical_query_order = ids
            canonical_queries = {str(row["query_id"]): str(row["query"]) for row in unsupported}
        else:
            if ids != canonical_query_order:
                raise RuntimeError(
                    f"{condition}: unsupported query order/IDs do not match the canonical source."
                )

            for row in unsupported:
                query_id = str(row["query_id"])
                if str(row["query"]) != canonical_queries[query_id]:
                    raise RuntimeError(
                        f"{condition}:{query_id}: query text differs across frozen conditions."
                    )

        source_rows[condition] = unsupported
        source_summaries[condition] = {
            "query_count": payload.get("query_count"),
            "completed_query_count": payload.get("completed_query_count"),
            "generation_failure_count": payload.get("generation_failure_count"),
            "unanswerable_query_count": payload.get("unanswerable_query_count"),
            "refusal_count": payload.get("refusal_count"),
            "correctly_refused_unanswerable_count": payload.get(
                "correctly_refused_unanswerable_count"
            ),
            "unsupported_refusal_rate": payload.get("unsupported_refusal_rate"),
            "structural_validity_rate": payload.get("structural_validity_rate"),
        }

    if canonical_query_order is None:
        raise RuntimeError("No canonical unsupported query order.")

    queue_rows: list[dict[str, object]] = []
    units: list[dict[str, object]] = []

    by_condition_and_id = {
        condition: {str(row["query_id"]): row for row in rows}
        for condition, rows in source_rows.items()
    }

    for index, query_id in enumerate(
        canonical_query_order,
        start=1,
    ):
        responses: list[dict[str, object]] = []

        for condition in SOURCES:
            row = by_condition_and_id[condition][query_id]

            response = {
                "condition": condition,
                "query_id": query_id,
                "query": canonical_queries[query_id],
                "expected_answerable": False,
                "predicted_answerable": row.get("predicted_answerable"),
                "answerability_correct": row.get("answerability_correct"),
                "answer": str(row.get("answer", "")),
                "generation_failed": bool(row.get("generation_failed", False)),
                "failure_type": row.get("failure_type"),
                "structurally_valid": bool(row.get("structurally_valid", False)),
                "insufficient_evidence": row.get("insufficient_evidence"),
                "claim_count": row.get("claim_count"),
            }

            responses.append(response)

            queue_rows.append(
                {
                    "review_id": f"{condition}:{query_id}",
                    "unit_id": f"unsuprev_{index:03d}",
                    **response,
                    "review_status": "REVIEW_REQUIRED",
                    "human_label": None,
                    "adjudication_note": None,
                }
            )

        units.append(
            {
                "unit_id": f"unsuprev_{index:03d}",
                "query_id": query_id,
                "query": canonical_queries[query_id],
                "responses": responses,
            }
        )

    if len(queue_rows) != EXPECTED_TOTAL_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_ROWS} taxonomy rows; found {len(queue_rows)}."
        )

    review_ids = [str(row["review_id"]) for row in queue_rows]
    if len(review_ids) != len(set(review_ids)):
        raise RuntimeError("Duplicate taxonomy review IDs.")

    condition_counts = Counter(str(row["condition"]) for row in queue_rows)
    expected_condition_counts = {
        condition: EXPECTED_UNSUPPORTED_PER_CONDITION for condition in SOURCES
    }
    if dict(condition_counts) != expected_condition_counts:
        raise RuntimeError(f"Unexpected condition counts: {dict(condition_counts)}")

    QUEUE_PATH.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in queue_rows),
        encoding="utf-8",
    )

    UNITS_PATH.write_text(
        "".join(json.dumps(unit, sort_keys=True) + "\n" for unit in units),
        encoding="utf-8",
    )

    pending_lines = [
        "# Unsupported-response taxonomy review v0.1",
        "",
        (
            "Allowed labels: `EXPLICIT_REFUSAL`, "
            "`CORRECTIVE_DENIAL`, `UNSUPPORTED_ASSERTION`, "
            "`STRUCTURAL_FAILURE`."
        ),
        "",
        (
            "Classify frozen response behavior only. Existing "
            "answerability metadata is context, not the taxonomy label."
        ),
        "",
    ]

    for unit in units:
        append_unit(pending_lines, unit)

    PENDING_PATH.write_text(
        "\n".join(pending_lines) + "\n",
        encoding="utf-8",
    )

    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    for old_path in BATCH_DIR.glob("batch_*.md"):
        old_path.unlink()

    for batch_start in range(
        0,
        len(units),
        BATCH_SIZE,
    ):
        batch_number = batch_start // BATCH_SIZE + 1
        batch_units = units[batch_start : batch_start + BATCH_SIZE]

        batch_lines = [
            (f"# Unsupported-response taxonomy review batch {batch_number:02d}"),
            "",
            (
                "Allowed labels: `EXPLICIT_REFUSAL`, "
                "`CORRECTIVE_DENIAL`, `UNSUPPORTED_ASSERTION`, "
                "`STRUCTURAL_FAILURE`."
            ),
            "",
            (
                "Classify the frozen response behavior; do not "
                "rerun models or use outside web knowledge."
            ),
            "",
        ]

        for unit in batch_units:
            append_unit(batch_lines, unit)

        output_path = BATCH_DIR / f"batch_{batch_number:02d}.md"
        output_path.write_text(
            "\n".join(batch_lines) + "\n",
            encoding="utf-8",
        )

    print("unsupported query units:", len(units))
    print("taxonomy response rows:", len(queue_rows))
    print("condition counts:", dict(condition_counts))
    print("review batches:", (len(units) + BATCH_SIZE - 1) // BATCH_SIZE)
    print("allowed labels:", sorted(ALLOWED_LABELS))
    print()
    print("frozen source summaries:")
    for condition, summary in source_summaries.items():
        print(f"  {condition}: {summary}")
    print()
    print("UNSUPPORTED RESPONSE TAXONOMY QUEUE: PASS")


if __name__ == "__main__":
    main()
