#!/usr/bin/env python3
"""Build the frozen answer-to-claim completeness review queue."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CAPTURES = {
    "base_rag": (ROOT / "artifacts" / "evaluation" / "claim_support_base_capture_v0_1.json"),
    "lora_rag": (ROOT / "artifacts" / "evaluation" / "claim_support_lora_capture_v0_1.json"),
}

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_units_v0_1.jsonl"

PENDING_PATH = (
    ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_review_pending_v0_1.md"
)

BATCH_DIR = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_review_batches_v0_1"

EXPECTED_SYSTEM_COUNTS = {
    "base_rag": 20,
    "lora_rag": 20,
}

ALLOWED_LABELS = {
    "FULLY_CAPTURED",
    "PARTIALLY_CAPTURED",
    "MATERIAL_OMISSION",
}

BATCH_SIZE = 10


def load_capture(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected JSON object.")
    return value


def completeness_fingerprint(
    *,
    query: str,
    answer: str,
    claim_texts: list[str],
) -> str:
    payload = {
        "query": query.strip(),
        "answer": answer.strip(),
        "claim_texts": [text.strip() for text in claim_texts],
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> None:
    queue_rows: list[dict[str, object]] = []

    for system, path in CAPTURES.items():
        capture = load_capture(path)

        summary = capture.get("summary")
        if not isinstance(summary, dict):
            raise TypeError(f"{system}: capture summary must be a mapping.")

        if summary.get("reference_alignment_pass") is not True:
            raise RuntimeError(f"{system}: capture did not pass reference alignment.")

        query_results = capture.get("query_results")
        if not isinstance(query_results, list):
            raise TypeError(f"{system}: query_results must be a list.")

        if len(query_results) != 20:
            raise RuntimeError(
                f"{system}: expected 20 answerable query results; found {len(query_results)}."
            )

        seen_query_ids: set[str] = set()

        for row in query_results:
            if not isinstance(row, dict):
                raise TypeError(f"{system}: query result must be a mapping.")

            query_id = str(row["query_id"])
            if query_id in seen_query_ids:
                raise RuntimeError(f"{system}: duplicate query ID {query_id}.")
            seen_query_ids.add(query_id)

            query = str(row["query"])
            answer = str(row["answer"])

            claims = row.get("claims")
            if not isinstance(claims, list) or not claims:
                raise RuntimeError(f"{system}:{query_id}: claims must be non-empty.")

            claim_payloads: list[dict[str, str]] = []

            for claim in claims:
                if not isinstance(claim, dict):
                    raise TypeError(f"{system}:{query_id}: claim must be a mapping.")

                claim_id = str(claim["claim_id"])
                claim_text = str(claim["text"]).strip()
                if not claim_text:
                    raise RuntimeError(f"{system}:{query_id}:{claim_id}: claim text is blank.")

                claim_payloads.append(
                    {
                        "claim_id": claim_id,
                        "text": claim_text,
                    }
                )

            queue_rows.append(
                {
                    "review_id": f"{system}:{query_id}",
                    "system": system,
                    "query_id": query_id,
                    "query": query,
                    "answer": answer,
                    "claim_count": len(claim_payloads),
                    "claims": claim_payloads,
                    "review_status": "REVIEW_REQUIRED",
                    "human_label": None,
                    "adjudication_note": None,
                }
            )

    if len(queue_rows) != 40:
        raise RuntimeError(f"Expected 40 answer-level rows; found {len(queue_rows)}.")

    system_counts = Counter(str(row["system"]) for row in queue_rows)
    if dict(system_counts) != EXPECTED_SYSTEM_COUNTS:
        raise RuntimeError(f"Unexpected system counts: {dict(system_counts)}")

    review_ids = [str(row["review_id"]) for row in queue_rows]
    if len(review_ids) != len(set(review_ids)):
        raise RuntimeError("Duplicate answer-completeness review IDs.")

    QUEUE_PATH.write_text(
        "".join(
            json.dumps(
                row,
                sort_keys=True,
            )
            + "\n"
            for row in queue_rows
        ),
        encoding="utf-8",
    )

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in queue_rows:
        claims = row["claims"]
        if not isinstance(claims, list):
            raise TypeError("claims must be a list.")

        claim_texts = [str(claim["text"]) for claim in claims if isinstance(claim, dict)]

        fingerprint = completeness_fingerprint(
            query=str(row["query"]),
            answer=str(row["answer"]),
            claim_texts=claim_texts,
        )
        grouped[fingerprint].append(row)

    units: list[dict[str, object]] = []

    for index, (
        fingerprint,
        members,
    ) in enumerate(
        sorted(grouped.items()),
        start=1,
    ):
        first = members[0]
        units.append(
            {
                "unit_id": f"comprev_{index:03d}",
                "fingerprint": fingerprint,
                "query": first["query"],
                "answer": first["answer"],
                "claims": first["claims"],
                "claim_count": first["claim_count"],
                "member_count": len(members),
                "member_review_ids": [member["review_id"] for member in members],
                "member_systems": sorted({str(member["system"]) for member in members}),
                "human_label": None,
                "adjudication_note": None,
            }
        )

    UNITS_PATH.write_text(
        "".join(
            json.dumps(
                unit,
                sort_keys=True,
            )
            + "\n"
            for unit in units
        ),
        encoding="utf-8",
    )

    lines = [
        "# Answer-to-claim completeness review v0.1",
        "",
        ("Allowed labels: `FULLY_CAPTURED`, `PARTIALLY_CAPTURED`, `MATERIAL_OMISSION`."),
        "",
        (
            "Evaluate representation of the prose answer by the formal "
            "claims. Do not re-evaluate factual correctness or evidence "
            "support in this stage."
        ),
        "",
    ]

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
                ("**Systems:** " + ", ".join(str(value) for value in unit["member_systems"])),
                "",
                f"**Query:** {unit['query']}",
                "",
                "**Answer:**",
                "",
                str(unit["answer"]),
                "",
                "**Formal claims:**",
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
                ("**Decision:** `FULLY_CAPTURED / PARTIALLY_CAPTURED / MATERIAL_OMISSION`"),
                "",
                "**Note:**",
                "",
            ]
        )

    for unit in units:
        append_unit(lines, unit)

    PENDING_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    BATCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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
            (f"# Answer-to-claim completeness review batch {batch_number:02d}"),
            "",
            ("Allowed labels: `FULLY_CAPTURED`, `PARTIALLY_CAPTURED`, `MATERIAL_OMISSION`."),
            "",
            (
                "Evaluate answer-to-claim representation only; "
                "claim-evidence support was evaluated separately."
            ),
            "",
        ]

        for unit in batch_units:
            append_unit(batch_lines, unit)

        output = BATCH_DIR / f"batch_{batch_number:02d}.md"
        output.write_text(
            "\n".join(batch_lines) + "\n",
            encoding="utf-8",
        )

    print("total answer instances:", len(queue_rows))
    print("base answers:", system_counts["base_rag"])
    print("LoRA answers:", system_counts["lora_rag"])
    print("unique review units:", len(units))
    print(
        "exact duplicate tasks removed:",
        len(queue_rows) - len(units),
    )
    print(
        "review batches:",
        ((len(units) + BATCH_SIZE - 1) // BATCH_SIZE),
    )
    print(
        "allowed labels:",
        sorted(ALLOWED_LABELS),
    )
    print("PASS")


if __name__ == "__main__":
    main()
