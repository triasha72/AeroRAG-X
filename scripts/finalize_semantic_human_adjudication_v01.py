"""Finalize protected semantic adjudication and four-way coverage."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_units_v0_1.jsonl"

DECISION_DIR = ROOT / "artifacts" / "evaluation" / "semantic_review_decisions_v0_1"

ADJUDICATION_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_adjudication_v0_1.jsonl"

SUMMARY_PATH = ROOT / "artifacts" / "evaluation" / "semantic_four_way_coverage_v0_1.json"

REPORT_PATH = ROOT / "reports" / "semantic_quality_v0_1.md"

SYSTEMS = [
    "base_closed_book",
    "lora_closed_book",
    "base_rag",
    "lora_rag",
]


def load_jsonl(
    path: Path,
) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def ratio(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def main() -> None:
    queue = load_jsonl(QUEUE_PATH)

    units = load_jsonl(UNITS_PATH)

    batch_paths = sorted(DECISION_DIR.glob("batch_*.jsonl"))

    if len(batch_paths) != 12:
        raise RuntimeError(f"Expected 12 decision batches, found {len(batch_paths)}.")

    decisions: dict[
        str,
        dict[str, object],
    ] = {}

    for path in batch_paths:
        for row in load_jsonl(path):
            unit_id = str(row["unit_id"])

            if unit_id in decisions:
                raise RuntimeError(f"Duplicate decision for {unit_id}.")

            decisions[unit_id] = row

    if len(decisions) != 294:
        raise RuntimeError(f"Expected 294 manual decisions, found {len(decisions)}.")

    review_to_unit: dict[
        str,
        str,
    ] = {}

    for unit in units:
        unit_id = str(unit["unit_id"])

        member_ids = unit["member_review_ids"]

        if not isinstance(
            member_ids,
            list,
        ):
            raise TypeError("member_review_ids must be a list.")

        for review_id_value in member_ids:
            review_id = str(review_id_value)

            if review_id in review_to_unit:
                raise RuntimeError("Duplicate review ID.")

            review_to_unit[review_id] = unit_id

    if len(review_to_unit) != 294:
        raise RuntimeError(f"Expected 294 review mappings, found {len(review_to_unit)}.")

    final_rows = []

    auto_count = 0
    manual_count = 0

    for queue_row in queue:
        row = dict(queue_row)

        review_id = str(row["review_id"])

        status = str(row["review_status"])

        if status == "AUTO_SUPPORTED":
            label = "PRESENT"

            source = "deterministic:" + str(row["deterministic_match_method"])

            note = "Accepted by frozen deterministic canonical/alias matching."

            auto_count += 1

        elif status == "REVIEW_REQUIRED":
            unit_id = review_to_unit[review_id]

            decision = decisions[unit_id]

            label = str(decision["human_label"])

            source = "human_review:" + unit_id

            note = str(decision["reviewer_note"])

            manual_count += 1

        else:
            raise RuntimeError(f"Unexpected review status: {status!r}")

        if label not in {
            "PRESENT",
            "ABSENT",
            "AMBIGUOUS",
        }:
            raise RuntimeError(f"Unexpected final label: {label!r}")

        row["final_label"] = label
        row["decision_source"] = source
        row["final_reviewer_note"] = note

        final_rows.append(row)

    if len(final_rows) != 304:
        raise RuntimeError(f"Expected 304 concept instances, found {len(final_rows)}.")

    if auto_count != 10:
        raise RuntimeError(f"Expected 10 auto-supported rows, found {auto_count}.")

    if manual_count != 294:
        raise RuntimeError(f"Expected 294 manual rows, found {manual_count}.")

    ADJUDICATION_PATH.write_text(
        "".join(
            json.dumps(
                row,
                sort_keys=True,
            )
            + "\n"
            for row in final_rows
        ),
        encoding="utf-8",
    )

    global_counts = Counter(str(row["final_label"]) for row in final_rows)

    by_system = defaultdict(list)

    for row in final_rows:
        by_system[str(row["system"])].append(row)

    system_results = {}

    for system in SYSTEMS:
        rows = by_system[system]

        if len(rows) != 76:
            raise RuntimeError(f"{system}: expected 76, found {len(rows)}.")

        counts = Counter(str(row["final_label"]) for row in rows)

        present = counts["PRESENT"]

        absent = counts["ABSENT"]

        ambiguous = counts["AMBIGUOUS"]

        query_groups = defaultdict(list)

        for row in rows:
            query_groups[str(row["query_id"])].append(row)

        query_metrics = []

        for query_id in sorted(query_groups):
            query_rows = query_groups[query_id]

            query_counts = Counter(str(row["final_label"]) for row in query_rows)

            total = len(query_rows)

            query_present = query_counts["PRESENT"]

            query_ambiguous = query_counts["AMBIGUOUS"]

            query_metrics.append(
                {
                    "query_id": query_id,
                    "concept_count": total,
                    "present_count": (query_present),
                    "absent_count": (query_counts["ABSENT"]),
                    "ambiguous_count": (query_ambiguous),
                    "coverage_lower_bound": ratio(
                        query_present,
                        total,
                    ),
                    "coverage_upper_bound": ratio(
                        query_present + query_ambiguous,
                        total,
                    ),
                }
            )

        macro_lower = sum(float(row["coverage_lower_bound"]) for row in query_metrics) / len(
            query_metrics
        )

        macro_upper = sum(float(row["coverage_upper_bound"]) for row in query_metrics) / len(
            query_metrics
        )

        system_results[system] = {
            "concept_count": len(rows),
            "present_count": present,
            "absent_count": absent,
            "ambiguous_count": ambiguous,
            "micro_coverage_lower_bound": ratio(
                present,
                len(rows),
            ),
            "micro_coverage_upper_bound": ratio(
                present + ambiguous,
                len(rows),
            ),
            "macro_query_coverage_lower_bound": (macro_lower),
            "macro_query_coverage_upper_bound": (macro_upper),
            "query_metrics": query_metrics,
        }

    summary = {
        "version": "v0.1",
        "system_count": 4,
        "query_count_per_system": 20,
        "concept_instances_per_system": 76,
        "total_concept_instances": 304,
        "auto_supported_count": auto_count,
        "human_reviewed_count": manual_count,
        "global_label_counts": dict(global_counts),
        "ambiguity_policy": (
            "Conservative lower-bound coverage "
            "counts PRESENT only. Upper-bound "
            "coverage additionally includes "
            "AMBIGUOUS."
        ),
        "systems": system_results,
    }

    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = [
        "# Semantic Quality Evaluation v0.1",
        "",
        "## Method",
        "",
        (
            "Four frozen systems were evaluated "
            "over 20 answerable queries and "
            "76 expected concept instances per "
            "system."
        ),
        "",
        (
            "Ten concept instances were accepted "
            "through deterministic canonical/alias "
            "matching. The remaining 294 were "
            "human-reviewed."
        ),
        "",
        (
            "PRESENT counts toward conservative "
            "coverage. AMBIGUOUS is retained and "
            "included only in the upper bound."
        ),
        "",
        "## Four-way semantic coverage",
        "",
        (
            "| System | Present | Absent | Ambiguous "
            "| Micro lower | Micro upper "
            "| Macro lower | Macro upper |"
        ),
        ("|---|---:|---:|---:|---:|---:|---:|---:|"),
    ]

    for system in SYSTEMS:
        metrics = system_results[system]

        lines.append(
            "| "
            + system
            + " | "
            + str(metrics["present_count"])
            + " | "
            + str(metrics["absent_count"])
            + " | "
            + str(metrics["ambiguous_count"])
            + " | "
            + f"{float(metrics['micro_coverage_lower_bound']):.4f}"
            + " | "
            + f"{float(metrics['micro_coverage_upper_bound']):.4f}"
            + " | "
            + f"{float(metrics['macro_query_coverage_lower_bound']):.4f}"
            + " | "
            + f"{float(metrics['macro_query_coverage_upper_bound']):.4f}"
            + " |"
        )

    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            ("- No generation or retrieval was rerun for this evaluation."),
            ("- No cosine or NLI threshold was frozen after failed calibration."),
            ("- AMBIGUOUS labels remain explicit instead of being forced binary."),
            (
                "- These metrics measure expected-"
                "concept coverage, not universal "
                "factual correctness."
            ),
            "",
        ]
    )

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        "GLOBAL:",
        dict(global_counts),
    )

    print(
        "auto-supported:",
        auto_count,
    )

    print(
        "human-reviewed:",
        manual_count,
    )

    print()

    for system in SYSTEMS:
        metrics = system_results[system]

        print(
            system,
            "present=",
            metrics["present_count"],
            "absent=",
            metrics["absent_count"],
            "ambiguous=",
            metrics["ambiguous_count"],
            "micro_lower=",
            f"{float(metrics['micro_coverage_lower_bound']):.6f}",
            "micro_upper=",
            f"{float(metrics['micro_coverage_upper_bound']):.6f}",
            "macro_lower=",
            f"{float(metrics['macro_query_coverage_lower_bound']):.6f}",
            "macro_upper=",
            f"{float(metrics['macro_query_coverage_upper_bound']):.6f}",
        )

    print()
    print(
        "adjudication:",
        ADJUDICATION_PATH,
    )
    print(
        "summary:",
        SUMMARY_PATH,
    )
    print(
        "report:",
        REPORT_PATH,
    )


if __name__ == "__main__":
    main()
