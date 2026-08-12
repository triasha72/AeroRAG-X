#!/usr/bin/env python3
"""Finalize the protected claim-evidence support evaluation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "claim_support_review_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "claim_support_review_units_v0_1.jsonl"

DECISIONS_DIR = ROOT / "artifacts" / "evaluation" / "claim_support_decisions_v0_1"

FINAL_JSONL = ROOT / "artifacts" / "evaluation" / "claim_support_adjudication_v0_1.jsonl"

SUMMARY_JSON = ROOT / "artifacts" / "evaluation" / "claim_support_summary_v0_1.json"

REPORT_MD = ROOT / "reports" / "claim_support_v0_1.md"

ALLOWED_LABELS = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "UNSUPPORTED",
    "CONTRADICTED",
}

EXPECTED_SYSTEM_COUNTS = {
    "base_rag": 32,
    "lora_rag": 53,
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
    if len(paths) != 5:
        raise RuntimeError(f"Expected 5 manual decision files; found {len(paths)}.")

    rows: list[dict[str, object]] = []
    for path in paths:
        rows.extend(load_jsonl(path))
    return rows


def round_metric(value: float) -> float:
    return round(value, 6)


def summarize_system(rows: list[dict[str, object]]) -> dict[str, object]:
    counts = Counter(str(row["final_label"]) for row in rows)
    total = len(rows)

    supported = counts["SUPPORTED"]
    partial = counts["PARTIALLY_SUPPORTED"]
    unsupported = counts["UNSUPPORTED"]
    contradicted = counts["CONTRADICTED"]

    return {
        "total_claims": total,
        "supported": supported,
        "partially_supported": partial,
        "unsupported": unsupported,
        "contradicted": contradicted,
        "strict_support_rate": round_metric(supported / total),
        "support_or_partial_rate": round_metric((supported + partial) / total),
    }


def main() -> None:
    queue_rows = load_jsonl(QUEUE_PATH)
    unit_rows = load_jsonl(UNITS_PATH)
    decision_rows = load_manual_decisions()

    if len(queue_rows) != 85:
        raise RuntimeError(f"Expected 85 claim-review rows; found {len(queue_rows)}.")

    system_counts = Counter(str(row["system"]) for row in queue_rows)
    if dict(system_counts) != EXPECTED_SYSTEM_COUNTS:
        raise RuntimeError(f"Unexpected system counts: {dict(system_counts)}")

    queue_by_review_id = {str(row["review_id"]): row for row in queue_rows}
    if len(queue_by_review_id) != len(queue_rows):
        raise RuntimeError("Duplicate review IDs in queue.")

    if len(unit_rows) != 75:
        raise RuntimeError(f"Expected 75 manual review units; found {len(unit_rows)}.")

    units_by_id = {str(row["unit_id"]): row for row in unit_rows}
    if len(units_by_id) != len(unit_rows):
        raise RuntimeError("Duplicate unit IDs in review units.")

    if len(decision_rows) != 75:
        raise RuntimeError(f"Expected 75 manual decisions; found {len(decision_rows)}.")

    decisions_by_unit = {str(row["unit_id"]): row for row in decision_rows}
    if len(decisions_by_unit) != len(decision_rows):
        raise RuntimeError("Duplicate unit IDs in manual decisions.")

    if set(decisions_by_unit) != set(units_by_id):
        missing = sorted(set(units_by_id) - set(decisions_by_unit))
        extra = sorted(set(decisions_by_unit) - set(units_by_id))
        raise RuntimeError(
            "Manual decision IDs do not match frozen review units. "
            f"missing={missing}, extra={extra}"
        )

    for unit_id, decision in decisions_by_unit.items():
        label = str(decision["human_label"])
        if label not in ALLOWED_LABELS:
            raise RuntimeError(f"{unit_id}: unsupported manual label {label!r}")

        if decision.get("decision_status") != "CONFIRMED":
            raise RuntimeError(f"{unit_id}: decision_status must be CONFIRMED.")

        if decision.get("reviewer_confirmation_required") is not False:
            raise RuntimeError(f"{unit_id}: reviewer_confirmation_required must be false.")

        note = decision.get("adjudication_note")
        if not isinstance(note, str) or not note.strip():
            raise RuntimeError(f"{unit_id}: adjudication_note must be non-empty.")

    manual_by_review_id: dict[str, dict[str, object]] = {}

    for unit_id, unit in units_by_id.items():
        decision = decisions_by_unit[unit_id]

        member_review_ids = unit.get("member_review_ids")
        if not isinstance(member_review_ids, list) or not member_review_ids:
            raise RuntimeError(f"{unit_id}: member_review_ids must be a non-empty list.")

        for review_id_value in member_review_ids:
            review_id = str(review_id_value)

            if review_id in manual_by_review_id:
                raise RuntimeError(f"Manual review ID mapped more than once: {review_id}")

            if review_id not in queue_by_review_id:
                raise RuntimeError(f"Manual review ID not found in queue: {review_id}")

            queue_row = queue_by_review_id[review_id]
            if queue_row["review_status"] != "REVIEW_REQUIRED":
                raise RuntimeError(f"{review_id}: manual mapping points to a non-manual queue row.")

            manual_by_review_id[review_id] = {
                "final_label": decision["human_label"],
                "decision_source": f"adjudication:{unit_id}",
                "adjudication_note": decision["adjudication_note"],
            }

    manual_queue_ids = {
        str(row["review_id"]) for row in queue_rows if row["review_status"] == "REVIEW_REQUIRED"
    }

    if set(manual_by_review_id) != manual_queue_ids:
        missing = sorted(manual_queue_ids - set(manual_by_review_id))
        extra = sorted(set(manual_by_review_id) - manual_queue_ids)
        raise RuntimeError(
            "Manual review mapping does not cover the queue exactly. "
            f"missing={missing}, extra={extra}"
        )

    final_rows: list[dict[str, object]] = []
    automatic_count = 0
    adjudicated_count = 0

    for queue_row in queue_rows:
        review_id = str(queue_row["review_id"])
        status = str(queue_row["review_status"])

        row = dict(queue_row)

        if status == "AUTO_SUPPORTED_EXACT":
            automatic_label = queue_row.get("automatic_label")
            if automatic_label != "SUPPORTED":
                raise RuntimeError(
                    f"{review_id}: AUTO_SUPPORTED_EXACT must have automatic_label=SUPPORTED."
                )

            automatic_method = queue_row.get("automatic_method")
            if not isinstance(automatic_method, str) or not automatic_method:
                raise RuntimeError(f"{review_id}: automatic method is missing.")

            row["final_label"] = "SUPPORTED"
            row["decision_source"] = f"automatic:{automatic_method}"
            row["final_adjudication_note"] = (
                "Accepted by frozen normalized exact claim-containment rule."
            )
            automatic_count += 1

        elif status == "REVIEW_REQUIRED":
            manual = manual_by_review_id[review_id]
            row["final_label"] = manual["final_label"]
            row["decision_source"] = manual["decision_source"]
            row["final_adjudication_note"] = manual["adjudication_note"]
            adjudicated_count += 1

        else:
            raise RuntimeError(f"{review_id}: unexpected review_status {status!r}")

        if row["final_label"] not in ALLOWED_LABELS:
            raise RuntimeError(f"{review_id}: invalid final label {row['final_label']!r}")

        final_rows.append(row)

    if automatic_count != 10:
        raise RuntimeError(f"Expected 10 automatic rows; found {automatic_count}.")

    if adjudicated_count != 75:
        raise RuntimeError(f"Expected 75 adjudicated rows; found {adjudicated_count}.")

    if len(final_rows) != 85:
        raise RuntimeError(f"Expected 85 final rows; found {len(final_rows)}.")

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

    strict_delta = round_metric(
        float(lora["strict_support_rate"]) - float(base["strict_support_rate"])
    )
    broad_delta = round_metric(
        float(lora["support_or_partial_rate"]) - float(base["support_or_partial_rate"])
    )

    summary = {
        "version": "v0.1",
        "evaluation": "claim_evidence_support",
        "total_claims": 85,
        "automatic_exact_supported_count": automatic_count,
        "adjudicated_count": adjudicated_count,
        "methodology": (
            "Single structured adjudication pass under a frozen "
            "claim-support policy; not an independent multi-assessor "
            "human annotation study."
        ),
        "systems": system_summaries,
        "overall": overall,
        "lora_minus_base": {
            "strict_support_rate": strict_delta,
            "support_or_partial_rate": broad_delta,
        },
    }

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Claim-evidence support evaluation v0.1",
        "",
        "## Scope",
        "",
        (
            "This evaluation measures whether each formal grounded claim "
            "is supported by the evidence cited by that claim."
        ),
        "",
        (
            "The 85-claim benchmark contains 32 Base + RAG claims and "
            "53 LoRA + RAG claims from the frozen grounded recapture."
        ),
        "",
        (
            "Ten exact-containment cases were accepted automatically. "
            "The remaining 75 were adjudicated under the frozen "
            "claim-support policy."
        ),
        "",
        (
            "This is a single structured adjudication pass, not an "
            "independent multi-assessor human annotation study."
        ),
        "",
        "## Results",
        "",
        (
            "| System | Claims | Supported | Partial | Unsupported | "
            "Contradicted | Strict support | Support-or-partial |"
        ),
        ("|---|---:|---:|---:|---:|---:|---:|---:|"),
    ]

    for system, display in [
        ("base_rag", "Base + RAG"),
        ("lora_rag", "LoRA + RAG"),
    ]:
        metrics = system_summaries[system]
        report_lines.append(
            "| "
            f"{display} | "
            f"{metrics['total_claims']} | "
            f"{metrics['supported']} | "
            f"{metrics['partially_supported']} | "
            f"{metrics['unsupported']} | "
            f"{metrics['contradicted']} | "
            f"{float(metrics['strict_support_rate']):.4f} | "
            f"{float(metrics['support_or_partial_rate']):.4f} |"
        )

    report_lines.extend(
        [
            "",
            "## Comparison",
            "",
            (f"LoRA - Base strict-support-rate difference: {strict_delta:+.4f}"),
            "",
            (f"LoRA - Base support-or-partial-rate difference: {broad_delta:+.4f}"),
            "",
            "## Interpretation guardrails",
            "",
            (
                "- These metrics evaluate claim-to-cited-evidence support, "
                "not universal factual correctness."
            ),
            ("- `PARTIALLY_SUPPORTED` remains distinct from fully supported claims."),
            ("- `CONTRADICTED` is reserved for material conflict with the cited evidence."),
            ("- Higher claim count is not treated as higher quality by itself."),
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

    print("total claims:", len(final_rows))
    print("automatic exact-supported:", automatic_count)
    print("adjudicated:", adjudicated_count)
    print()

    for system in ("base_rag", "lora_rag"):
        metrics = system_summaries[system]
        print(system)
        print("  total:", metrics["total_claims"])
        print("  supported:", metrics["supported"])
        print(
            "  partially supported:",
            metrics["partially_supported"],
        )
        print("  unsupported:", metrics["unsupported"])
        print("  contradicted:", metrics["contradicted"])
        print(
            "  strict support:",
            f"{float(metrics['strict_support_rate']):.6f}",
        )
        print(
            "  support-or-partial:",
            f"{float(metrics['support_or_partial_rate']):.6f}",
        )

    print()
    print("LoRA - Base strict delta:", f"{strict_delta:+.6f}")
    print("LoRA - Base broad delta:", f"{broad_delta:+.6f}")
    print("CLAIM-SUPPORT FINALIZATION: PASS")
    print("final adjudication:", FINAL_JSONL)
    print("summary:", SUMMARY_JSON)
    print("report:", REPORT_MD)


if __name__ == "__main__":
    main()
