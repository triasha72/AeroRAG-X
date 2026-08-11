"""Split semantic review units into compact human-review batches."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_units_v0_1.jsonl"

OUTPUT_DIR = ROOT / "artifacts" / "evaluation" / "semantic_review_batches_v0_1"

BATCH_SIZE = 25


def main() -> None:
    units = [
        json.loads(line)
        for line in INPUT_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_batches = math.ceil(len(units) / BATCH_SIZE)

    for batch_number in range(total_batches):
        start = batch_number * BATCH_SIZE

        end = start + BATCH_SIZE

        batch = units[start:end]

        path = OUTPUT_DIR / (f"batch_{batch_number + 1:02d}.md")

        lines = [
            (f"# Semantic concept review batch {batch_number + 1}"),
            "",
            ("Allowed decisions: `PRESENT`, `ABSENT`, or `AMBIGUOUS`."),
            "",
        ]

        for unit in batch:
            lines.extend(
                [
                    "---",
                    "",
                    (f"## {unit['unit_id']}"),
                    "",
                    (f"**Concept:** {unit['concept_id']}"),
                    "",
                    (f"**Expected proposition:** {unit['canonical_text']}"),
                    "",
                    (f"**Answer:** {unit['answer']}"),
                    "",
                    (f"**Applies to:** {unit['member_count']} instance(s)"),
                    "",
                    ("**Decision:** `PRESENT / ABSENT / AMBIGUOUS`"),
                    "",
                    "**Note:**",
                    "",
                ]
            )

        path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    print("units:", len(units))
    print("batch size:", BATCH_SIZE)
    print(
        "batches:",
        total_batches,
    )
    print(
        "directory:",
        OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()
