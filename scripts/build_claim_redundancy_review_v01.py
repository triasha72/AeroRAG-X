#!/usr/bin/env python3
"""Build the frozen within-answer claim-redundancy review queue."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_queue_v0_1.jsonl"

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "claim_redundancy_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "claim_redundancy_review_units_v0_1.jsonl"

PENDING_PATH = ROOT / "artifacts" / "evaluation" / "claim_redundancy_review_pending_v0_1.md"

BATCH_DIR = ROOT / "artifacts" / "evaluation" / "claim_redundancy_review_batches_v0_1"

EXPECTED_SYSTEM_CLAIMS = {
    "base_rag": 32,
    "lora_rag": 53,
}

ALLOWED_LABELS = {
    "DISTINCT",
    "OVERLAPPING",
    "REDUNDANT",
}

BATCH_SIZE = 8


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number}: expected a JSON object.")
        rows.append(value)
    return rows


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
            f"**System:** {unit['system']}",
            "",
            f"**Query ID:** {unit['query_id']}",
            "",
            f"**Query:** {unit['query']}",
            "",
            "**Answer:**",
            "",
            str(unit["answer"]),
            "",
            "**Sibling formal claims:**",
            "",
        ]
    )

    claims = unit["claims"]
    if not isinstance(claims, list):
        raise TypeError("unit claims must be a list.")

    for claim in claims:
        if not isinstance(claim, dict):
            raise TypeError("unit claim must be a mapping.")
        target.append(f"- `{claim['claim_id']}`: {claim['text']}")

    target.extend(
        [
            "",
            "**Decide each claim:**",
            "",
        ]
    )

    for claim in claims:
        if not isinstance(claim, dict):
            raise TypeError("unit claim must be a mapping.")
        target.extend(
            [
                f"### {claim['claim_id']}",
                "",
                ("Decision: `DISTINCT / OVERLAPPING / REDUNDANT`"),
                "",
                "Related sibling claim IDs:",
                "",
                "Note:",
                "",
            ]
        )


def main() -> None:
    answer_rows = load_jsonl(SOURCE_PATH)

    if len(answer_rows) != 40:
        raise RuntimeError(f"Expected 40 grounded answers; found {len(answer_rows)}.")

    queue_rows: list[dict[str, object]] = []
    review_units: list[dict[str, object]] = []

    system_claim_counts: Counter[str] = Counter()
    answer_system_counts: Counter[str] = Counter()

    for answer_index, answer_row in enumerate(
        answer_rows,
        start=1,
    ):
        system = str(answer_row["system"])
        query_id = str(answer_row["query_id"])
        query = str(answer_row["query"])
        answer = str(answer_row["answer"])

        answer_system_counts[system] += 1

        claims = answer_row.get("claims")
        if not isinstance(claims, list) or not claims:
            raise RuntimeError(f"{system}:{query_id}: claims must be non-empty.")

        claim_count = len(claims)
        unit_id = f"redrev_{answer_index:03d}"

        normalized_claims: list[dict[str, str]] = []

        for claim in claims:
            if not isinstance(claim, dict):
                raise TypeError(f"{system}:{query_id}: claim must be a mapping.")

            claim_id = str(claim["claim_id"])
            text = str(claim["text"]).strip()
            if not text:
                raise RuntimeError(f"{system}:{query_id}:{claim_id}: blank claim.")

            normalized_claims.append(
                {
                    "claim_id": claim_id,
                    "text": text,
                }
            )

        if claim_count > 1:
            review_units.append(
                {
                    "unit_id": unit_id,
                    "system": system,
                    "query_id": query_id,
                    "query": query,
                    "answer": answer,
                    "claim_count": claim_count,
                    "claims": normalized_claims,
                }
            )

        for claim in normalized_claims:
            review_id = f"{system}:{query_id}:{claim['claim_id']}"
            system_claim_counts[system] += 1

            if claim_count == 1:
                review_status = "AUTO_DISTINCT_SINGLETON"
                automatic_label: str | None = "DISTINCT"
                automatic_method: str | None = "single_claim_answer"
            else:
                review_status = "REVIEW_REQUIRED"
                automatic_label = None
                automatic_method = None

            queue_rows.append(
                {
                    "review_id": review_id,
                    "unit_id": unit_id,
                    "system": system,
                    "query_id": query_id,
                    "query": query,
                    "answer": answer,
                    "claim_count": claim_count,
                    "claim_id": claim["claim_id"],
                    "claim_text": claim["text"],
                    "sibling_claims": normalized_claims,
                    "review_status": review_status,
                    "automatic_label": automatic_label,
                    "automatic_method": automatic_method,
                    "human_label": None,
                    "related_claim_ids": [],
                    "adjudication_note": None,
                }
            )

    if len(queue_rows) != 85:
        raise RuntimeError(f"Expected 85 formal claims; found {len(queue_rows)}.")

    if dict(system_claim_counts) != EXPECTED_SYSTEM_CLAIMS:
        raise RuntimeError(f"Unexpected system claim counts: {dict(system_claim_counts)}")

    if dict(answer_system_counts) != {
        "base_rag": 20,
        "lora_rag": 20,
    }:
        raise RuntimeError(f"Unexpected answer counts: {dict(answer_system_counts)}")

    review_ids = [str(row["review_id"]) for row in queue_rows]
    if len(review_ids) != len(set(review_ids)):
        raise RuntimeError("Duplicate claim-redundancy review IDs.")

    unit_ids = [str(unit["unit_id"]) for unit in review_units]
    if len(unit_ids) != len(set(unit_ids)):
        raise RuntimeError("Duplicate redundancy review-unit IDs.")

    QUEUE_PATH.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in queue_rows),
        encoding="utf-8",
    )

    UNITS_PATH.write_text(
        "".join(json.dumps(unit, sort_keys=True) + "\n" for unit in review_units),
        encoding="utf-8",
    )

    pending_lines = [
        "# Claim redundancy review v0.1",
        "",
        ("Allowed labels: `DISTINCT`, `OVERLAPPING`, `REDUNDANT`."),
        "",
        ("Compare formal claims only with sibling claims from the same answer."),
        "",
    ]

    for unit in review_units:
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
        len(review_units),
        BATCH_SIZE,
    ):
        batch_number = batch_start // BATCH_SIZE + 1
        batch_units = review_units[batch_start : batch_start + BATCH_SIZE]

        batch_lines = [
            f"# Claim redundancy review batch {batch_number:02d}",
            "",
            ("Allowed labels: `DISTINCT`, `OVERLAPPING`, `REDUNDANT`."),
            "",
            (
                "Compare claims only within the same answer. "
                "Do not evaluate correctness or evidence support."
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

    status_counts = Counter(str(row["review_status"]) for row in queue_rows)

    review_claims_by_system = Counter(
        str(row["system"]) for row in queue_rows if row["review_status"] == "REVIEW_REQUIRED"
    )

    auto_claims_by_system = Counter(
        str(row["system"])
        for row in queue_rows
        if row["review_status"] == "AUTO_DISTINCT_SINGLETON"
    )

    print("total answers:", len(answer_rows))
    print("total claims:", len(queue_rows))
    print(
        "system claims:",
        dict(system_claim_counts),
    )
    print(
        "automatic singleton-distinct:",
        status_counts["AUTO_DISTINCT_SINGLETON"],
    )
    print(
        "manual review claims:",
        status_counts["REVIEW_REQUIRED"],
    )
    print(
        "manual review answer units:",
        len(review_units),
    )
    print(
        "manual claims by system:",
        dict(review_claims_by_system),
    )
    print(
        "automatic claims by system:",
        dict(auto_claims_by_system),
    )
    print(
        "review batches:",
        ((len(review_units) + BATCH_SIZE - 1) // BATCH_SIZE),
    )
    print("allowed labels:", sorted(ALLOWED_LABELS))
    print("CLAIM REDUNDANCY QUEUE: PASS")


if __name__ == "__main__":
    main()
