#!/usr/bin/env python3
"""Finalize the protected answer-to-claim completeness evaluation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_units_v0_1.jsonl"

DECISIONS_DIR = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_decisions_v0_1"

FINAL_JSONL = (
    ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_adjudication_v0_1.jsonl"
)

SUMMARY_JSON = ROOT / "artifacts" / "evaluation" / "answer_claim_completeness_summary_v0_1.json"

REPORT_MD = ROOT / "reports" / "answer_claim_completeness_v0_1.md"

ALLOWED_LABELS = {
    "FULLY_CAPTURED",
    "PARTIALLY_CAPTURED",
    "MATERIAL_OMISSION",
}

EXPECTED_SYSTEM_COUNTS = {
    "base_rag": 20,
    "lora_rag": 20,
}

EXPECTED_LABEL_COUNTS = {
    "FULLY_CAPTURED": 11,
    "PARTIALLY_CAPTURED": 20,
    "MATERIAL_OMISSION": 9,
}

EXPECTED_SYSTEM_LABEL_COUNTS = {
    "base_rag": {
        "FULLY_CAPTURED": 2,
        "PARTIALLY_CAPTURED": 10,
        "MATERIAL_OMISSION": 8,
    },
    "lora_rag": {
        "FULLY_CAPTURED": 9,
        "PARTIALLY_CAPTURED": 10,
        "MATERIAL_OMISSION": 1,
    },
}


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


def load_manual_decisions() -> list[dict[str, object]]:
    paths = sorted(DECISIONS_DIR.glob("batch_*.jsonl"))
    if len(paths) != 4:
        raise RuntimeError(f"Expected 4 decision files; found {len(paths)}.")

    rows: list[dict[str, object]] = []
    for path in paths:
        rows.extend(load_jsonl(path))
    return rows


def round_metric(value: float) -> float:
    return round(value, 6)


def summarize_system(rows: list[dict[str, object]]) -> dict[str, object]:
    counts = Counter(str(row["final_label"]) for row in rows)
    total = len(rows)

    fully = counts["FULLY_CAPTURED"]
    partial = counts["PARTIALLY_CAPTURED"]
    omission = counts["MATERIAL_OMISSION"]

    return {
        "total_answers": total,
        "fully_captured": fully,
        "partially_captured": partial,
        "material_omission": omission,
        "full_capture_rate": round_metric(fully / total),
        "full_or_partial_capture_rate": round_metric((fully + partial) / total),
    }


def main() -> None:
    queue_rows = load_jsonl(QUEUE_PATH)
    unit_rows = load_jsonl(UNITS_PATH)
    decision_rows = load_manual_decisions()

    if len(queue_rows) != 40:
        raise RuntimeError(f"Expected 40 answer rows; found {len(queue_rows)}.")

    if len(unit_rows) != 40:
        raise RuntimeError(f"Expected 40 review units; found {len(unit_rows)}.")

    if len(decision_rows) != 40:
        raise RuntimeError(f"Expected 40 confirmed decisions; found {len(decision_rows)}.")

    queue_by_review_id = {str(row["review_id"]): row for row in queue_rows}
    if len(queue_by_review_id) != len(queue_rows):
        raise RuntimeError("Duplicate review IDs in queue.")

    units_by_id = {str(row["unit_id"]): row for row in unit_rows}
    if len(units_by_id) != len(unit_rows):
        raise RuntimeError("Duplicate unit IDs in review units.")

    decisions_by_unit = {str(row["unit_id"]): row for row in decision_rows}
    if len(decisions_by_unit) != len(decision_rows):
        raise RuntimeError("Duplicate unit IDs in decisions.")

    if set(decisions_by_unit) != set(units_by_id):
        missing = sorted(set(units_by_id) - set(decisions_by_unit))
        extra = sorted(set(decisions_by_unit) - set(units_by_id))
        raise RuntimeError(
            f"Decision IDs do not match frozen review units. missing={missing}, extra={extra}"
        )

    for unit_id, decision in decisions_by_unit.items():
        label = str(decision["human_label"])

        if label not in ALLOWED_LABELS:
            raise RuntimeError(f"{unit_id}: unsupported label {label!r}")

        if decision.get("decision_status") != "CONFIRMED":
            raise RuntimeError(f"{unit_id}: decision_status must be CONFIRMED.")

        if decision.get("reviewer_confirmation_required") is not False:
            raise RuntimeError(f"{unit_id}: reviewer_confirmation_required must be false.")

        note = decision.get("adjudication_note")
        if not isinstance(note, str) or not note.strip():
            raise RuntimeError(f"{unit_id}: adjudication_note must be non-empty.")

    final_by_review_id: dict[str, dict[str, object]] = {}

    for unit_id, unit in units_by_id.items():
        decision = decisions_by_unit[unit_id]

        member_review_ids = unit.get("member_review_ids")
        if not isinstance(member_review_ids, list) or not member_review_ids:
            raise RuntimeError(f"{unit_id}: member_review_ids must be non-empty.")

        for review_id_value in member_review_ids:
            review_id = str(review_id_value)

            if review_id in final_by_review_id:
                raise RuntimeError(f"Review ID mapped more than once: {review_id}")

            queue_row = queue_by_review_id.get(review_id)
            if queue_row is None:
                raise RuntimeError(f"{unit_id}: queue row missing for {review_id}.")

            final_by_review_id[review_id] = {
                **queue_row,
                "unit_id": unit_id,
                "final_label": decision["human_label"],
                "decision_source": f"adjudication:{unit_id}",
                "final_adjudication_note": decision["adjudication_note"],
            }

    if set(final_by_review_id) != set(queue_by_review_id):
        missing = sorted(set(queue_by_review_id) - set(final_by_review_id))
        extra = sorted(set(final_by_review_id) - set(queue_by_review_id))
        raise RuntimeError(
            f"Final mapping does not cover frozen queue exactly. missing={missing}, extra={extra}"
        )

    final_rows = [final_by_review_id[str(row["review_id"])] for row in queue_rows]

    system_counts = Counter(str(row["system"]) for row in final_rows)
    if dict(system_counts) != EXPECTED_SYSTEM_COUNTS:
        raise RuntimeError(f"Unexpected system counts: {dict(system_counts)}")

    overall_label_counts = Counter(str(row["final_label"]) for row in final_rows)
    if dict(overall_label_counts) != EXPECTED_LABEL_COUNTS:
        raise RuntimeError(f"Unexpected overall label counts: {dict(overall_label_counts)}")

    for system, expected in EXPECTED_SYSTEM_LABEL_COUNTS.items():
        observed = Counter(str(row["final_label"]) for row in final_rows if row["system"] == system)
        if dict(observed) != expected:
            raise RuntimeError(f"{system}: unexpected label counts {dict(observed)}")

    FINAL_JSONL.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in final_rows),
        encoding="utf-8",
    )

    by_system = {
        system: [row for row in final_rows if row["system"] == system]
        for system in EXPECTED_SYSTEM_COUNTS
    }

    system_summaries = {system: summarize_system(rows) for system, rows in by_system.items()}

    overall = summarize_system(final_rows)

    base = system_summaries["base_rag"]
    lora = system_summaries["lora_rag"]

    full_delta = round_metric(float(lora["full_capture_rate"]) - float(base["full_capture_rate"]))
    broad_delta = round_metric(
        float(lora["full_or_partial_capture_rate"]) - float(base["full_or_partial_capture_rate"])
    )

    summary = {
        "version": "v0.1",
        "evaluation": "answer_to_claim_completeness",
        "total_answers": 40,
        "methodology": (
            "Single structured adjudication pass under a frozen "
            "answer-to-claim completeness policy; not an independent "
            "multi-assessor human annotation study."
        ),
        "systems": system_summaries,
        "overall": overall,
        "lora_minus_base": {
            "full_capture_rate": full_delta,
            "full_or_partial_capture_rate": broad_delta,
        },
    }

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Answer-to-claim completeness evaluation v0.1",
        "",
        "## Scope",
        "",
        (
            "This evaluation measures whether the formal claim structure "
            "captures the material factual and technical propositions "
            "expressed in each grounded prose answer."
        ),
        "",
        (
            "The benchmark contains 40 frozen grounded answer instances: "
            "20 Base + RAG and 20 LoRA + RAG."
        ),
        "",
        (
            "This stage evaluates representation/completeness only. "
            "Claim-evidence support was evaluated separately."
        ),
        "",
        (
            "This is a single structured adjudication pass under a "
            "frozen policy, not an independent multi-assessor human "
            "annotation study."
        ),
        "",
        "## Results",
        "",
        (
            "| System | Answers | Fully captured | Partial | "
            "Material omission | Full capture | Full-or-partial |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for system, display in [
        ("base_rag", "Base + RAG"),
        ("lora_rag", "LoRA + RAG"),
    ]:
        metrics = system_summaries[system]
        report_lines.append(
            "| "
            f"{display} | "
            f"{metrics['total_answers']} | "
            f"{metrics['fully_captured']} | "
            f"{metrics['partially_captured']} | "
            f"{metrics['material_omission']} | "
            f"{float(metrics['full_capture_rate']):.4f} | "
            f"{float(metrics['full_or_partial_capture_rate']):.4f} |"
        )

    report_lines.extend(
        [
            "",
            "## Comparison",
            "",
            (f"LoRA - Base full-capture-rate difference: {full_delta:+.4f}"),
            "",
            (f"LoRA - Base full-or-partial-capture-rate difference: {broad_delta:+.4f}"),
            "",
            "## Interpretation guardrails",
            "",
            (
                "- These metrics measure how completely formal claims "
                "represent the prose answer, not factual correctness."
            ),
            (
                "- Claim-evidence support is reported separately and "
                "must not be inferred from completeness."
            ),
            (
                "- Extra claims are not automatically beneficial; "
                "redundancy is evaluated separately."
            ),
            (
                "- Higher completeness on this protected benchmark does "
                "not establish universal model superiority."
            ),
            (
                "- No generation, retrieval, or training run was repeated "
                "for this adjudication stage."
            ),
            "",
        ]
    )

    REPORT_MD.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("total answers:", len(final_rows))
    print()

    for system in ("base_rag", "lora_rag"):
        metrics = system_summaries[system]
        print(system)
        print("  total:", metrics["total_answers"])
        print("  fully captured:", metrics["fully_captured"])
        print(
            "  partially captured:",
            metrics["partially_captured"],
        )
        print(
            "  material omission:",
            metrics["material_omission"],
        )
        print(
            "  full capture:",
            f"{float(metrics['full_capture_rate']):.6f}",
        )
        print(
            "  full-or-partial:",
            f"{float(metrics['full_or_partial_capture_rate']):.6f}",
        )

    print()
    print(
        "LoRA - Base full-capture delta:",
        f"{full_delta:+.6f}",
    )
    print(
        "LoRA - Base broad delta:",
        f"{broad_delta:+.6f}",
    )
    print("ANSWER-CLAIM COMPLETENESS FINALIZATION: PASS")
    print("final adjudication:", FINAL_JSONL)
    print("summary:", SUMMARY_JSON)
    print("report:", REPORT_MD)


if __name__ == "__main__":
    main()
