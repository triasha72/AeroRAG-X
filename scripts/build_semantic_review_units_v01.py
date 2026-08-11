"""Collapse exact duplicate semantic review tasks into unique review units."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_queue_v0_1.jsonl"

OUTPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_units_v0_1.jsonl"


def fingerprint(
    *,
    concept_id: str,
    answer: str,
) -> str:
    payload = (concept_id + "\n" + answer.strip()).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    rows = [
        json.loads(line)
        for line in QUEUE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    pending = [row for row in rows if row["review_status"] == "REVIEW_REQUIRED"]

    grouped: dict[
        str,
        list[dict[str, object]],
    ] = defaultdict(list)

    for row in pending:
        key = fingerprint(
            concept_id=str(row["concept_id"]),
            answer=str(row["answer"]),
        )

        grouped[key].append(row)

    units: list[dict[str, object]] = []

    for index, (
        fingerprint_value,
        members,
    ) in enumerate(
        sorted(grouped.items()),
        start=1,
    ):
        first = members[0]

        units.append(
            {
                "unit_id": (f"semrev_{index:03d}"),
                "fingerprint": (fingerprint_value),
                "concept_id": (first["concept_id"]),
                "canonical_text": (first["canonical_text"]),
                "accepted_phrases": (first["accepted_phrases"]),
                "answer": first["answer"],
                "member_count": len(members),
                "member_review_ids": [member["review_id"] for member in members],
                "member_systems": sorted({str(member["system"]) for member in members}),
                "human_label": None,
                "reviewer_note": None,
            }
        )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for unit in units:
            handle.write(
                json.dumps(
                    unit,
                    sort_keys=True,
                )
                + "\n"
            )

    multiplicity = Counter(int(unit["member_count"]) for unit in units)

    print(
        "pending instances:",
        len(pending),
    )

    print(
        "unique review units:",
        len(units),
    )

    print(
        "deduplicated instances:",
        len(pending) - len(units),
    )

    print(
        "multiplicity:",
        dict(sorted(multiplicity.items())),
    )

    print(
        "output:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
