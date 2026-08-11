"""Select one adjacent-concept hard-negative candidate per concept."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_hard_negative_candidates_v0_1.json"

OUTPUT_PATH = (
    ROOT / "artifacts" / "evaluation" / "semantic_hard_negative_review_candidates_v0_1.json"
)


def pair_key(
    left: str,
    right: str,
) -> tuple[str, str]:
    return tuple(sorted((left, right)))


EXCLUDED_RELATIONSHIPS = {
    pair_key(
        "thermal_management_mass_drag_penalties",
        "thermal_management_system_penalties",
    ): "near-equivalent penalty concepts",
    pair_key(
        "active_component_temperature_control",
        "active_thermal_control_requirement",
    ): "near-equivalent active thermal-control concepts",
    pair_key(
        "active_component_temperature_control",
        "component_temperature_limit_control",
    ): "near-equivalent component temperature-control concepts",
    pair_key(
        "active_thermal_control_requirement",
        "component_temperature_limit_control",
    ): "near-equivalent temperature-control concepts",
    pair_key(
        "forced_air_heat_rejection",
        "passive_active_battery_cooling",
    ): "specific cooling method versus broader cooling category",
    pair_key(
        "coolant_loops_and_heat_exchangers",
        "passive_active_battery_cooling",
    ): "specific cooling method versus broader cooling category",
    pair_key(
        "battery_defect_precursor_detection",
        "ultrasonic_nde_detection",
    ): "general detection capability versus specific detection method",
    pair_key(
        "battery_defect_precursor_detection",
        "embedded_sensor_prognostics",
    ): "general detection capability versus specific monitoring method",
}


def orient_candidate(
    row: dict[str, object],
    anchor: str,
) -> dict[str, object]:
    left_id = str(row["left_concept_id"])
    right_id = str(row["right_concept_id"])

    left_text = str(row["left_text"])
    right_text = str(row["right_text"])

    if anchor == left_id:
        candidate_id = right_id
        reference_text = left_text
        candidate_text = right_text
    elif anchor == right_id:
        candidate_id = left_id
        reference_text = right_text
        candidate_text = left_text
    else:
        raise ValueError(f"{anchor!r} is not part of candidate pair.")

    return {
        "anchor_concept_id": anchor,
        "reference_text": reference_text,
        "candidate_concept_id": candidate_id,
        "candidate_text": candidate_text,
        "cosine_similarity": float(row["cosine_similarity"]),
        "_pair_key": pair_key(
            anchor,
            candidate_id,
        ),
    }


def public_row(
    row: dict[str, object],
) -> dict[str, object]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def main() -> None:
    report = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    candidates = report["candidates"]

    concept_ids = sorted(
        {str(row["left_concept_id"]) for row in candidates}
        | {str(row["right_concept_id"]) for row in candidates}
    )

    by_concept: dict[
        str,
        list[dict[str, object]],
    ] = {concept_id: [] for concept_id in concept_ids}

    for row in candidates:
        left_id = str(row["left_concept_id"])
        right_id = str(row["right_concept_id"])

        key = pair_key(
            left_id,
            right_id,
        )

        if key in EXCLUDED_RELATIONSHIPS:
            continue

        by_concept[left_id].append(
            orient_candidate(
                row,
                left_id,
            )
        )

        by_concept[right_id].append(
            orient_candidate(
                row,
                right_id,
            )
        )

    for choices in by_concept.values():
        choices.sort(
            key=lambda row: float(row["cosine_similarity"]),
            reverse=True,
        )

    used_pairs: set[tuple[str, str]] = set()

    selections = []

    for concept_id in concept_ids:
        eligible = [row for row in by_concept[concept_id] if row["_pair_key"] not in used_pairs]

        if not eligible:
            raise RuntimeError(f"No eligible hard-negative candidate for {concept_id!r}.")

        selected = eligible[0]

        pair = selected["_pair_key"]

        if not isinstance(pair, tuple):
            raise TypeError("Internal pair key must be a tuple.")

        used_pairs.add(pair)

        selections.append(
            {
                **public_row(selected),
                "review_label": None,
                "review_reason": None,
                "alternatives": [public_row(row) for row in eligible[1:6]],
            }
        )

    excluded = [
        {
            "left_concept_id": key[0],
            "right_concept_id": key[1],
            "reason": reason,
        }
        for key, reason in sorted(EXCLUDED_RELATIONSHIPS.items())
    ]

    output = {
        "version": "v0.1",
        "concept_count": len(concept_ids),
        "selected_candidate_count": len(selections),
        "excluded_overlap_count": len(excluded),
        "review_policy": (
            "Selected pairs are candidate hard "
            "negatives only. Human review is required "
            "before assigning NO_MATCH."
        ),
        "excluded_relationships": excluded,
        "selections": selections,
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

    print(
        "concepts:",
        len(concept_ids),
    )
    print(
        "selected:",
        len(selections),
    )
    print(
        "excluded overlap/hierarchy pairs:",
        len(excluded),
    )
    print()

    for index, row in enumerate(
        selections,
        start=1,
    ):
        print(f"{index:02d}. {row['cosine_similarity']:.4f}")
        print(
            "   anchor:",
            row["anchor_concept_id"],
        )
        print(
            "      ",
            row["reference_text"],
        )
        print(
            "   candidate:",
            row["candidate_concept_id"],
        )
        print(
            "      ",
            row["candidate_text"],
        )
        print()

    print(
        "report:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
