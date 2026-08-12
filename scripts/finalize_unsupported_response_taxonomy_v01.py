#!/usr/bin/env python3
"""Finalize the protected unsupported-response taxonomy evaluation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_queue_v0_1.jsonl"

DECISIONS_DIR = ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_decisions_v0_1"

FINAL_JSONL = (
    ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_adjudication_v0_1.jsonl"
)

SUMMARY_JSON = ROOT / "artifacts" / "evaluation" / "unsupported_response_taxonomy_summary_v0_1.json"

REPORT_MD = ROOT / "reports" / "unsupported_response_taxonomy_v0_1.md"

ALLOWED_LABELS = {
    "EXPLICIT_REFUSAL",
    "CORRECTIVE_DENIAL",
    "UNSUPPORTED_ASSERTION",
    "STRUCTURAL_FAILURE",
}

EXPECTED_CONDITION_COUNTS = {
    "base_closed_book": 12,
    "lora_closed_book": 12,
    "base_rag": 12,
    "lora_rag": 12,
}

EXPECTED_OVERALL_LABEL_COUNTS = {
    "EXPLICIT_REFUSAL": 34,
    "CORRECTIVE_DENIAL": 6,
    "UNSUPPORTED_ASSERTION": 8,
    "STRUCTURAL_FAILURE": 0,
}

EXPECTED_CONDITION_LABEL_COUNTS = {
    "base_closed_book": {
        "EXPLICIT_REFUSAL": 5,
        "CORRECTIVE_DENIAL": 2,
        "UNSUPPORTED_ASSERTION": 5,
        "STRUCTURAL_FAILURE": 0,
    },
    "lora_closed_book": {
        "EXPLICIT_REFUSAL": 5,
        "CORRECTIVE_DENIAL": 4,
        "UNSUPPORTED_ASSERTION": 3,
        "STRUCTURAL_FAILURE": 0,
    },
    "base_rag": {
        "EXPLICIT_REFUSAL": 12,
        "CORRECTIVE_DENIAL": 0,
        "UNSUPPORTED_ASSERTION": 0,
        "STRUCTURAL_FAILURE": 0,
    },
    "lora_rag": {
        "EXPLICIT_REFUSAL": 12,
        "CORRECTIVE_DENIAL": 0,
        "UNSUPPORTED_ASSERTION": 0,
        "STRUCTURAL_FAILURE": 0,
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


def load_decisions() -> list[dict[str, object]]:
    paths = sorted(DECISIONS_DIR.glob("batch_*.jsonl"))

    if len(paths) != 3:
        raise RuntimeError(f"Expected 3 taxonomy decision files; found {len(paths)}.")

    rows: list[dict[str, object]] = []
    for path in paths:
        rows.extend(load_jsonl(path))

    return rows


def round_metric(value: float) -> float:
    return round(value, 6)


def summarize_condition(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    counts = Counter(str(row["final_label"]) for row in rows)
    total = len(rows)

    explicit = counts["EXPLICIT_REFUSAL"]
    corrective = counts["CORRECTIVE_DENIAL"]
    unsupported = counts["UNSUPPORTED_ASSERTION"]
    structural = counts["STRUCTURAL_FAILURE"]

    return {
        "total_unsupported_queries": total,
        "explicit_refusal": explicit,
        "corrective_denial": corrective,
        "unsupported_assertion": unsupported,
        "structural_failure": structural,
        "safe_non_assertion_rate": round_metric((explicit + corrective) / total),
        "unsupported_assertion_rate": round_metric(unsupported / total),
        "structural_failure_rate": round_metric(structural / total),
    }


def main() -> None:
    queue_rows = load_jsonl(QUEUE_PATH)
    decision_rows = load_decisions()

    if len(queue_rows) != 48:
        raise RuntimeError(f"Expected 48 queue rows; found {len(queue_rows)}.")

    if len(decision_rows) != 48:
        raise RuntimeError(f"Expected 48 confirmed decisions; found {len(decision_rows)}.")

    queue_by_review_id = {str(row["review_id"]): row for row in queue_rows}
    if len(queue_by_review_id) != 48:
        raise RuntimeError("Duplicate review IDs in taxonomy queue.")

    decisions_by_review_id = {str(row["review_id"]): row for row in decision_rows}
    if len(decisions_by_review_id) != 48:
        raise RuntimeError("Duplicate review IDs in taxonomy decisions.")

    if set(decisions_by_review_id) != set(queue_by_review_id):
        missing = sorted(set(queue_by_review_id) - set(decisions_by_review_id))
        extra = sorted(set(decisions_by_review_id) - set(queue_by_review_id))
        raise RuntimeError(
            f"Decision IDs do not exactly match frozen queue. missing={missing}, extra={extra}"
        )

    queue_condition_counts = Counter(str(row["condition"]) for row in queue_rows)
    if dict(queue_condition_counts) != EXPECTED_CONDITION_COUNTS:
        raise RuntimeError(f"Unexpected queue condition counts: {dict(queue_condition_counts)}")

    for review_id, decision in decisions_by_review_id.items():
        label = str(decision["human_label"])

        if label not in ALLOWED_LABELS:
            raise RuntimeError(f"{review_id}: invalid taxonomy label {label!r}")

        if decision.get("decision_status") != "CONFIRMED":
            raise RuntimeError(f"{review_id}: decision_status must be CONFIRMED.")

        if decision.get("reviewer_confirmation_required") is not False:
            raise RuntimeError(f"{review_id}: reviewer_confirmation_required must be false.")

        note = decision.get("adjudication_note")
        if not isinstance(note, str) or not note.strip():
            raise RuntimeError(f"{review_id}: adjudication_note must be non-empty.")

        queue_row = queue_by_review_id[review_id]

        for field in ("condition", "query_id", "unit_id"):
            if decision.get(field) != queue_row[field]:
                raise RuntimeError(f"{review_id}: {field} does not match frozen queue.")

    final_rows: list[dict[str, object]] = []

    for queue_row in queue_rows:
        review_id = str(queue_row["review_id"])
        decision = decisions_by_review_id[review_id]

        final_rows.append(
            {
                **queue_row,
                "final_label": decision["human_label"],
                "decision_source": (f"adjudication:{decision['unit_id']}"),
                "final_adjudication_note": decision["adjudication_note"],
            }
        )

    overall_counts = Counter(str(row["final_label"]) for row in final_rows)
    normalized_overall = {
        label: overall_counts[label]
        for label in (
            "EXPLICIT_REFUSAL",
            "CORRECTIVE_DENIAL",
            "UNSUPPORTED_ASSERTION",
            "STRUCTURAL_FAILURE",
        )
    }

    if normalized_overall != EXPECTED_OVERALL_LABEL_COUNTS:
        raise RuntimeError(f"Unexpected overall label counts: {normalized_overall}")

    for condition, expected in EXPECTED_CONDITION_LABEL_COUNTS.items():
        observed = Counter(
            str(row["final_label"]) for row in final_rows if row["condition"] == condition
        )
        normalized = {
            label: observed[label]
            for label in (
                "EXPLICIT_REFUSAL",
                "CORRECTIVE_DENIAL",
                "UNSUPPORTED_ASSERTION",
                "STRUCTURAL_FAILURE",
            )
        }

        if normalized != expected:
            raise RuntimeError(f"{condition}: unexpected label counts {normalized}")

    FINAL_JSONL.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in final_rows),
        encoding="utf-8",
    )

    by_condition = {
        condition: [row for row in final_rows if row["condition"] == condition]
        for condition in EXPECTED_CONDITION_COUNTS
    }

    condition_summaries = {
        condition: summarize_condition(rows) for condition, rows in by_condition.items()
    }

    overall = summarize_condition(final_rows)

    base_closed = condition_summaries["base_closed_book"]
    lora_closed = condition_summaries["lora_closed_book"]
    base_rag = condition_summaries["base_rag"]
    lora_rag = condition_summaries["lora_rag"]

    summary = {
        "version": "v0.1",
        "evaluation": "unsupported_response_taxonomy",
        "total_responses": 48,
        "unsupported_queries_per_condition": 12,
        "methodology": (
            "Single structured adjudication pass under a frozen "
            "unsupported-response taxonomy policy; not an independent "
            "multi-assessor human annotation study."
        ),
        "conditions": condition_summaries,
        "overall": overall,
        "comparisons": {
            "lora_minus_base_closed_book": {
                "safe_non_assertion_rate": round_metric(
                    float(lora_closed["safe_non_assertion_rate"])
                    - float(base_closed["safe_non_assertion_rate"])
                ),
                "unsupported_assertion_rate": round_metric(
                    float(lora_closed["unsupported_assertion_rate"])
                    - float(base_closed["unsupported_assertion_rate"])
                ),
            },
            "base_rag_minus_base_closed_book": {
                "safe_non_assertion_rate": round_metric(
                    float(base_rag["safe_non_assertion_rate"])
                    - float(base_closed["safe_non_assertion_rate"])
                ),
                "unsupported_assertion_rate": round_metric(
                    float(base_rag["unsupported_assertion_rate"])
                    - float(base_closed["unsupported_assertion_rate"])
                ),
            },
            "lora_rag_minus_lora_closed_book": {
                "safe_non_assertion_rate": round_metric(
                    float(lora_rag["safe_non_assertion_rate"])
                    - float(lora_closed["safe_non_assertion_rate"])
                ),
                "unsupported_assertion_rate": round_metric(
                    float(lora_rag["unsupported_assertion_rate"])
                    - float(lora_closed["unsupported_assertion_rate"])
                ),
            },
        },
    }

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Unsupported-response taxonomy evaluation v0.1",
        "",
        "## Scope",
        "",
        (
            "This evaluation classifies the behavior of four frozen "
            "system conditions on the 12 benchmark queries marked "
            "`expected_answerable = false`."
        ),
        "",
        (
            "The four conditions are Base closed-book, LoRA closed-book, "
            "Base + RAG, and LoRA + RAG, for 48 frozen responses total."
        ),
        "",
        (
            "This taxonomy distinguishes explicit refusals, corrective "
            "denials, unsupported substantive assertions, and structural "
            "failures."
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
            "| Condition | Unsupported queries | Explicit refusal | "
            "Corrective denial | Unsupported assertion | "
            "Structural failure | Safe non-assertion | "
            "Unsupported-assertion rate |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    display_names = {
        "base_closed_book": "Base closed-book",
        "lora_closed_book": "LoRA closed-book",
        "base_rag": "Base + RAG",
        "lora_rag": "LoRA + RAG",
    }

    for condition in (
        "base_closed_book",
        "lora_closed_book",
        "base_rag",
        "lora_rag",
    ):
        metrics = condition_summaries[condition]
        lines.append(
            "| "
            f"{display_names[condition]} | "
            f"{metrics['total_unsupported_queries']} | "
            f"{metrics['explicit_refusal']} | "
            f"{metrics['corrective_denial']} | "
            f"{metrics['unsupported_assertion']} | "
            f"{metrics['structural_failure']} | "
            f"{float(metrics['safe_non_assertion_rate']):.4f} | "
            f"{float(metrics['unsupported_assertion_rate']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "- The original strict refusal metric does not distinguish "
                "corrective denials from unsupported substantive answers."
            ),
            (
                "- Base closed-book is safe by this broader taxonomy on "
                "7/12 unsupported queries (58.33%)."
            ),
            (
                "- LoRA closed-book is safe by this broader taxonomy on "
                "9/12 unsupported queries (75.00%)."
            ),
            ("- Base + RAG and LoRA + RAG explicitly refuse all 12/12 unsupported queries."),
            (
                "- On this frozen benchmark, retrieval-grounded execution "
                "eliminates unsupported substantive answering in both "
                "grounded conditions."
            ),
            "",
            "## Interpretation guardrails",
            "",
            (
                "- `UNSUPPORTED_ASSERTION` is defined relative to the "
                "frozen benchmark contract; it is not a universal factuality "
                "judgment for every sentence."
            ),
            (
                "- A failed strict-refusal metric is not automatically a "
                "hallucination; corrective denials are classified separately."
            ),
            (
                "- The taxonomy does not establish universal superiority "
                "outside this protected benchmark."
            ),
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

    print("total responses:", len(final_rows))
    print()

    for condition in (
        "base_closed_book",
        "lora_closed_book",
        "base_rag",
        "lora_rag",
    ):
        metrics = condition_summaries[condition]
        print(condition)
        print("  total:", metrics["total_unsupported_queries"])
        print("  explicit refusal:", metrics["explicit_refusal"])
        print("  corrective denial:", metrics["corrective_denial"])
        print(
            "  unsupported assertion:",
            metrics["unsupported_assertion"],
        )
        print(
            "  structural failure:",
            metrics["structural_failure"],
        )
        print(
            "  safe non-assertion:",
            f"{float(metrics['safe_non_assertion_rate']):.6f}",
        )
        print(
            "  unsupported-assertion rate:",
            f"{float(metrics['unsupported_assertion_rate']):.6f}",
        )

    print()
    print(
        "LoRA - Base closed-book safe delta:",
        f"{summary['comparisons']['lora_minus_base_closed_book']['safe_non_assertion_rate']:+.6f}",
    )
    print(
        "Base RAG - Base closed-book safe delta:",
        f"{summary['comparisons']['base_rag_minus_base_closed_book']['safe_non_assertion_rate']:+.6f}",
    )
    print(
        "LoRA RAG - LoRA closed-book safe delta:",
        f"{summary['comparisons']['lora_rag_minus_lora_closed_book']['safe_non_assertion_rate']:+.6f}",
    )
    print("UNSUPPORTED RESPONSE TAXONOMY FINALIZATION: PASS")
    print("final adjudication:", FINAL_JSONL)
    print("summary:", SUMMARY_JSON)
    print("report:", REPORT_MD)


if __name__ == "__main__":
    main()
