#!/usr/bin/env python3
"""Finalize the protected within-answer claim-redundancy evaluation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "claim_redundancy_queue_v0_1.jsonl"

DECISIONS_DIR = ROOT / "artifacts" / "evaluation" / "claim_redundancy_decisions_v0_1"

FINAL_JSONL = ROOT / "artifacts" / "evaluation" / "claim_redundancy_adjudication_v0_1.jsonl"

SUMMARY_JSON = ROOT / "artifacts" / "evaluation" / "claim_redundancy_summary_v0_1.json"

REPORT_MD = ROOT / "reports" / "claim_redundancy_v0_1.md"

ALLOWED_LABELS = {
    "DISTINCT",
    "OVERLAPPING",
    "REDUNDANT",
}

EXPECTED_SYSTEM_COUNTS = {
    "base_rag": 32,
    "lora_rag": 53,
}

EXPECTED_MANUAL_COUNTS = {
    "DISTINCT": 43,
    "OVERLAPPING": 25,
    "REDUNDANT": 1,
}

EXPECTED_FINAL_SYSTEM_LABEL_COUNTS = {
    "base_rag": {
        "DISTINCT": 28,
        "OVERLAPPING": 4,
        "REDUNDANT": 0,
    },
    "lora_rag": {
        "DISTINCT": 31,
        "OVERLAPPING": 21,
        "REDUNDANT": 1,
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
    if len(paths) != 3:
        raise RuntimeError(f"Expected 3 redundancy decision files; found {len(paths)}.")

    rows: list[dict[str, object]] = []
    for path in paths:
        rows.extend(load_jsonl(path))
    return rows


def round_metric(value: float) -> float:
    return round(value, 6)


def summarize_system(rows: list[dict[str, object]]) -> dict[str, object]:
    counts = Counter(str(row["final_label"]) for row in rows)
    total = len(rows)

    distinct = counts["DISTINCT"]
    overlapping = counts["OVERLAPPING"]
    redundant = counts["REDUNDANT"]

    return {
        "total_claims": total,
        "distinct": distinct,
        "overlapping": overlapping,
        "redundant": redundant,
        "redundancy_rate": round_metric(redundant / total),
        "overlap_rate": round_metric(overlapping / total),
        "nonredundant_rate": round_metric((distinct + overlapping) / total),
    }


def main() -> None:
    queue_rows = load_jsonl(QUEUE_PATH)
    decision_rows = load_manual_decisions()

    if len(queue_rows) != 85:
        raise RuntimeError(f"Expected 85 redundancy queue rows; found {len(queue_rows)}.")

    queue_by_review_id = {str(row["review_id"]): row for row in queue_rows}
    if len(queue_by_review_id) != len(queue_rows):
        raise RuntimeError("Duplicate review IDs in redundancy queue.")

    system_counts = Counter(str(row["system"]) for row in queue_rows)
    if dict(system_counts) != EXPECTED_SYSTEM_COUNTS:
        raise RuntimeError(f"Unexpected system claim counts: {dict(system_counts)}")

    status_counts = Counter(str(row["review_status"]) for row in queue_rows)
    if status_counts != {
        "AUTO_DISTINCT_SINGLETON": 16,
        "REVIEW_REQUIRED": 69,
    }:
        raise RuntimeError(f"Unexpected queue status counts: {dict(status_counts)}")

    if len(decision_rows) != 69:
        raise RuntimeError(f"Expected 69 manual redundancy decisions; found {len(decision_rows)}.")

    decisions_by_review_id = {str(row["review_id"]): row for row in decision_rows}
    if len(decisions_by_review_id) != len(decision_rows):
        raise RuntimeError("Duplicate review IDs in redundancy decisions.")

    manual_queue_ids = {
        str(row["review_id"]) for row in queue_rows if row["review_status"] == "REVIEW_REQUIRED"
    }

    if set(decisions_by_review_id) != manual_queue_ids:
        missing = sorted(manual_queue_ids - set(decisions_by_review_id))
        extra = sorted(set(decisions_by_review_id) - manual_queue_ids)
        raise RuntimeError(
            "Manual decision IDs do not exactly match review-required "
            f"queue rows. missing={missing}, extra={extra}"
        )

    manual_counts: Counter[str] = Counter()

    for review_id, decision in decisions_by_review_id.items():
        label = str(decision["human_label"])

        if label not in ALLOWED_LABELS:
            raise RuntimeError(f"{review_id}: invalid human label {label!r}")

        if decision.get("decision_status") != "CONFIRMED":
            raise RuntimeError(f"{review_id}: decision_status must be CONFIRMED.")

        if decision.get("reviewer_confirmation_required") is not False:
            raise RuntimeError(f"{review_id}: reviewer_confirmation_required must be false.")

        note = decision.get("adjudication_note")
        if not isinstance(note, str) or not note.strip():
            raise RuntimeError(f"{review_id}: adjudication_note must be non-empty.")

        related = decision.get("related_claim_ids")
        if not isinstance(related, list):
            raise RuntimeError(f"{review_id}: related_claim_ids must be a list.")

        if label == "DISTINCT" and related:
            raise RuntimeError(f"{review_id}: DISTINCT must not list related claims.")

        if label in {"OVERLAPPING", "REDUNDANT"} and not related:
            raise RuntimeError(f"{review_id}: {label} must list related claims.")

        queue_row = queue_by_review_id[review_id]

        if decision.get("system") != queue_row["system"]:
            raise RuntimeError(f"{review_id}: system does not match frozen queue.")

        if decision.get("query_id") != queue_row["query_id"]:
            raise RuntimeError(f"{review_id}: query_id does not match frozen queue.")

        if decision.get("claim_id") != queue_row["claim_id"]:
            raise RuntimeError(f"{review_id}: claim_id does not match frozen queue.")

        sibling_claims = queue_row.get("sibling_claims")
        if not isinstance(sibling_claims, list):
            raise RuntimeError(f"{review_id}: sibling_claims missing from queue.")

        sibling_ids = {
            str(claim["claim_id"]) for claim in sibling_claims if isinstance(claim, dict)
        }

        own_claim_id = str(queue_row["claim_id"])

        for related_id_value in related:
            related_id = str(related_id_value)
            if related_id == own_claim_id:
                raise RuntimeError(f"{review_id}: claim cannot relate to itself.")
            if related_id not in sibling_ids:
                raise RuntimeError(
                    f"{review_id}: related claim {related_id!r} is not a sibling claim."
                )

        manual_counts[label] += 1

    if dict(manual_counts) != EXPECTED_MANUAL_COUNTS:
        raise RuntimeError(f"Unexpected manual label counts: {dict(manual_counts)}")

    final_rows: list[dict[str, object]] = []
    automatic_count = 0
    adjudicated_count = 0

    for queue_row in queue_rows:
        review_id = str(queue_row["review_id"])
        status = str(queue_row["review_status"])
        row = dict(queue_row)

        if status == "AUTO_DISTINCT_SINGLETON":
            if queue_row.get("automatic_label") != "DISTINCT":
                raise RuntimeError(f"{review_id}: singleton automatic label must be DISTINCT.")

            method = queue_row.get("automatic_method")
            if not isinstance(method, str) or not method:
                raise RuntimeError(f"{review_id}: automatic method is missing.")

            row["final_label"] = "DISTINCT"
            row["related_claim_ids"] = []
            row["decision_source"] = f"automatic:{method}"
            row["final_adjudication_note"] = (
                "Single-claim answer; no sibling formal claim exists "
                "with which this claim could be redundant."
            )
            automatic_count += 1

        elif status == "REVIEW_REQUIRED":
            decision = decisions_by_review_id[review_id]
            row["final_label"] = decision["human_label"]
            row["related_claim_ids"] = decision["related_claim_ids"]
            row["decision_source"] = f"adjudication:{decision['unit_id']}"
            row["final_adjudication_note"] = decision["adjudication_note"]
            adjudicated_count += 1

        else:
            raise RuntimeError(f"{review_id}: unexpected review status {status!r}")

        final_rows.append(row)

    if automatic_count != 16:
        raise RuntimeError(f"Expected 16 automatic rows; found {automatic_count}.")

    if adjudicated_count != 69:
        raise RuntimeError(f"Expected 69 adjudicated rows; found {adjudicated_count}.")

    if len(final_rows) != 85:
        raise RuntimeError(f"Expected 85 finalized rows; found {len(final_rows)}.")

    for system, expected in EXPECTED_FINAL_SYSTEM_LABEL_COUNTS.items():
        observed = Counter(str(row["final_label"]) for row in final_rows if row["system"] == system)
        normalized = {label: observed[label] for label in ("DISTINCT", "OVERLAPPING", "REDUNDANT")}
        if normalized != expected:
            raise RuntimeError(f"{system}: unexpected final label counts {normalized}")

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

    redundancy_delta = round_metric(float(lora["redundancy_rate"]) - float(base["redundancy_rate"]))
    overlap_delta = round_metric(float(lora["overlap_rate"]) - float(base["overlap_rate"]))
    nonredundant_delta = round_metric(
        float(lora["nonredundant_rate"]) - float(base["nonredundant_rate"])
    )

    summary = {
        "version": "v0.1",
        "evaluation": "within_answer_claim_redundancy",
        "total_claims": 85,
        "automatic_singleton_distinct_count": automatic_count,
        "adjudicated_count": adjudicated_count,
        "methodology": (
            "Single structured adjudication pass under a frozen "
            "within-answer claim-redundancy policy; not an independent "
            "multi-assessor human annotation study."
        ),
        "systems": system_summaries,
        "overall": overall,
        "lora_minus_base": {
            "redundancy_rate": redundancy_delta,
            "overlap_rate": overlap_delta,
            "nonredundant_rate": nonredundant_delta,
        },
    }

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Within-answer claim redundancy evaluation v0.1",
        "",
        "## Scope",
        "",
        (
            "This evaluation measures semantic redundancy among formal "
            "claims generated within the same grounded answer."
        ),
        "",
        ("The benchmark contains 85 frozen formal claims: 32 Base + RAG and 53 LoRA + RAG."),
        "",
        (
            "Sixteen singleton-answer claims were deterministically "
            "classified as DISTINCT. The remaining 69 claims were "
            "adjudicated under the frozen redundancy policy."
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
            "| System | Claims | Distinct | Overlapping | Redundant | "
            "Redundancy rate | Overlap rate | Nonredundant rate |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for system, display in [
        ("base_rag", "Base + RAG"),
        ("lora_rag", "LoRA + RAG"),
    ]:
        metrics = system_summaries[system]
        lines.append(
            "| "
            f"{display} | "
            f"{metrics['total_claims']} | "
            f"{metrics['distinct']} | "
            f"{metrics['overlapping']} | "
            f"{metrics['redundant']} | "
            f"{float(metrics['redundancy_rate']):.4f} | "
            f"{float(metrics['overlap_rate']):.4f} | "
            f"{float(metrics['nonredundant_rate']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Comparison",
            "",
            (f"LoRA - Base redundancy-rate difference: {redundancy_delta:+.4f}"),
            "",
            (f"LoRA - Base overlap-rate difference: {overlap_delta:+.4f}"),
            "",
            (f"LoRA - Base nonredundant-rate difference: {nonredundant_delta:+.4f}"),
            "",
            "## Interpretation guardrails",
            "",
            (
                "- `OVERLAPPING` claims share material content but still "
                "contribute additional information."
            ),
            (
                "- `REDUNDANT` is reserved for claims whose material "
                "content is already fully captured by sibling claims."
            ),
            ("- Low redundancy does not imply factual correctness or evidence support."),
            ("- Higher raw claim count is not treated as higher quality by itself."),
            (
                "- No generation, retrieval, or training run was repeated "
                "for this adjudication stage."
            ),
            "",
        ]
    )

    REPORT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("total claims:", len(final_rows))
    print("automatic singleton-distinct:", automatic_count)
    print("adjudicated:", adjudicated_count)
    print()

    for system in ("base_rag", "lora_rag"):
        metrics = system_summaries[system]
        print(system)
        print("  total:", metrics["total_claims"])
        print("  distinct:", metrics["distinct"])
        print("  overlapping:", metrics["overlapping"])
        print("  redundant:", metrics["redundant"])
        print(
            "  redundancy rate:",
            f"{float(metrics['redundancy_rate']):.6f}",
        )
        print(
            "  overlap rate:",
            f"{float(metrics['overlap_rate']):.6f}",
        )
        print(
            "  nonredundant rate:",
            f"{float(metrics['nonredundant_rate']):.6f}",
        )

    print()
    print(
        "LoRA - Base redundancy delta:",
        f"{redundancy_delta:+.6f}",
    )
    print(
        "LoRA - Base overlap delta:",
        f"{overlap_delta:+.6f}",
    )
    print(
        "LoRA - Base nonredundant delta:",
        f"{nonredundant_delta:+.6f}",
    )
    print("CLAIM REDUNDANCY FINALIZATION: PASS")
    print("final adjudication:", FINAL_JSONL)
    print("summary:", SUMMARY_JSON)
    print("report:", REPORT_MD)


if __name__ == "__main__":
    main()
