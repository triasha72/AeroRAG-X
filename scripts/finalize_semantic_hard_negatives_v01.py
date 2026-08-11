"""Finalize the reviewed semantic hard-negative set."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DECISIONS_PATH = (
    ROOT / "artifacts" / "evaluation" / "semantic_hard_negative_review_decisions_v0_1.json"
)

CANDIDATES_PATH = (
    ROOT / "artifacts" / "evaluation" / "semantic_hard_negative_review_candidates_v0_1.json"
)

OUTPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_hard_negative_review_final_v0_1.json"

TARGET_ANCHOR = "takeoff_climb_heat_rejection"
TARGET_CANDIDATE = "thermal_management_mass_drag_penalties"


def pair_key(
    left: str,
    right: str,
) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def main() -> None:
    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))

    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))

    accepted = [dict(row) for row in decisions["accepted"]]

    rejected = decisions["rejected"]

    if len(accepted) != 44:
        raise RuntimeError("Expected exactly 44 accepted hard negatives.")

    if len(rejected) != 1:
        raise RuntimeError("Expected exactly one unresolved concept.")

    if rejected[0]["anchor_concept_id"] != TARGET_ANCHOR:
        raise RuntimeError("Unexpected unresolved anchor.")

    selection = next(
        row for row in candidates["selections"] if row["anchor_concept_id"] == TARGET_ANCHOR
    )

    possible = [
        {
            "anchor_concept_id": TARGET_ANCHOR,
            "reference_text": (selection["reference_text"]),
            **alternative,
        }
        for alternative in selection["alternatives"]
    ]

    final_choice = next(row for row in possible if row["candidate_concept_id"] == TARGET_CANDIDATE)

    final_choice = {
        "anchor_concept_id": (final_choice["anchor_concept_id"]),
        "reference_text": (final_choice["reference_text"]),
        "candidate_concept_id": (final_choice["candidate_concept_id"]),
        "candidate_text": (final_choice["candidate_text"]),
        "cosine_similarity": float(final_choice["cosine_similarity"]),
        "review_label": "HARD_NO_MATCH",
        "review_reason": (
            "Operating-condition heat-rejection "
            "difficulty and system-level thermal-"
            "management mass/drag penalties are "
            "distinct technical propositions."
        ),
    }

    final_rows = [
        *accepted,
        final_choice,
    ]

    final_rows.sort(key=lambda row: row["anchor_concept_id"])

    anchors = {row["anchor_concept_id"] for row in final_rows}

    pairs = {
        pair_key(
            row["anchor_concept_id"],
            row["candidate_concept_id"],
        )
        for row in final_rows
    }

    if len(final_rows) != 45:
        raise RuntimeError("Expected 45 final hard negatives.")

    if len(anchors) != 45:
        raise RuntimeError("Expected 45 unique anchors.")

    if len(pairs) != 45:
        raise RuntimeError("Expected 45 unique hard-negative pairs.")

    if not all(row["review_label"] == "HARD_NO_MATCH" for row in final_rows):
        raise RuntimeError("All final rows must be HARD_NO_MATCH.")

    output = {
        "version": "v0.1-final",
        "hard_negative_count": len(final_rows),
        "review_policy": (
            "Each semantic concept has one "
            "human-reviewed semantically adjacent "
            "but propositionally distinct hard negative."
        ),
        "selections": final_rows,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("hard negatives:", len(final_rows))
    print("unique anchors:", len(anchors))
    print("unique pairs:", len(pairs))
    print(
        "final replacement:",
        TARGET_ANCHOR,
        "->",
        TARGET_CANDIDATE,
    )
    print(
        "replacement similarity:",
        final_choice["cosine_similarity"],
    )
    print("output:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
