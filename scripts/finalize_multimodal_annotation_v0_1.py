#!/usr/bin/env python3
"""Finalize the Phase 35 multimodal independent-review evidence."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from aeroragx.evaluation.multimodal_annotation import (
    MultimodalAnnotationEvidenceSummary,
    MultimodalAnnotationResponse,
    load_multimodal_annotation_responses,
    load_multimodal_annotation_tasks,
    validate_complete_multimodal_annotation_review,
)

ROOT = Path(__file__).resolve().parents[1]

TASKS_PATH = ROOT / "data" / "evaluation" / "multimodal_annotation_tasks_v0_1.jsonl"
RESPONSES_DIR = ROOT / "artifacts" / "evaluation" / "multimodal_annotation_responses_v0_1"
REVIEWER_A_PATH = RESPONSES_DIR / "reviewer_a.jsonl"
REVIEWER_B_PATH = RESPONSES_DIR / "reviewer_b.jsonl"
SUMMARY_PATH = ROOT / "artifacts" / "evaluation" / "multimodal_annotation_agreement_v0_1.json"
REPORT_PATH = ROOT / "reports" / "multimodal_annotation_agreement_v0_1.md"

FIRST_ANNOTATOR_ID = "reviewer_a"
SECOND_ANNOTATOR_ID = "reviewer_b"


def require_expected_annotator(
    responses: Sequence[MultimodalAnnotationResponse],
    expected_annotator_id: str,
    source_path: Path,
) -> None:
    """Ensure a reviewer response file contains only its assigned reviewer."""

    unexpected_annotator_ids = sorted(
        {
            response.annotator_id
            for response in responses
            if response.annotator_id != expected_annotator_id
        }
    )

    if unexpected_annotator_ids:
        raise RuntimeError(
            f"{source_path}: expected only annotator_id={expected_annotator_id!r}; "
            f"found {unexpected_annotator_ids}."
        )


def render_report(
    summary: MultimodalAnnotationEvidenceSummary,
) -> str:
    """Render the strict raw-agreement evidence summary as Markdown."""

    first_annotator_id, second_annotator_id = summary.annotator_ids
    first_counts = summary.decision_counts_by_annotator[first_annotator_id]
    second_counts = summary.decision_counts_by_annotator[second_annotator_id]

    lines = [
        "# Multimodal annotation agreement v0.1",
        "",
        "## Scope",
        "",
        (
            "This report summarizes two independently completed review passes over "
            "the frozen Phase 35 multimodal asset-record verification tasks."
        ),
        "",
        (
            "The finalizer refuses to generate this report unless both selected "
            "reviewers have exactly one response for every frozen task."
        ),
        "",
        "## Review completeness",
        "",
        "| Property | Value |",
        "|---|---:|",
        f"| Frozen tasks | {summary.task_count} |",
        f"| Total responses | {summary.response_count} |",
        f"| Comparable tasks | {summary.comparable_task_count} |",
        "| Complete review | yes |",
        "",
        "## Reviewer decision counts",
        "",
        "| Reviewer | Confirmed | Rejected | Uncertain |",
        "|---|---:|---:|---:|",
        (
            f"| `{first_annotator_id}` | "
            f"{first_counts['confirmed']} | "
            f"{first_counts['rejected']} | "
            f"{first_counts['uncertain']} |"
        ),
        (
            f"| `{second_annotator_id}` | "
            f"{second_counts['confirmed']} | "
            f"{second_counts['rejected']} | "
            f"{second_counts['uncertain']} |"
        ),
        "",
        "## Raw exact agreement",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Exact matches | {summary.exact_match_count} / {summary.task_count} |",
        f"| Raw exact-match rate | {summary.exact_match_rate:.6f} |",
        f"| Disagreements | {len(summary.disagreement_task_ids)} |",
        (f"| Adjudication required | {'yes' if summary.adjudication_required else 'no'} |"),
        "",
        "## Disagreements",
        "",
    ]

    if summary.disagreement_task_ids:
        lines.extend(f"- `{task_id}`" for task_id in summary.disagreement_task_ids)
    else:
        lines.append("No raw decision disagreements were recorded.")

    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            (
                "- This is raw exact-decision agreement on a small, frozen multimodal "
                "verification slice."
            ),
            "- It is not a chance-corrected inter-annotator reliability statistic.",
            (
                "- Agreement on this slice does not establish general figure/table "
                "detection or retrieval quality."
            ),
            (
                "- Any disagreement must be adjudicated separately; the original "
                "independent responses remain unchanged."
            ),
            "",
            "## Provenance boundary",
            "",
            (
                "The review tasks retain the source document ID, page ID, source URL, "
                "NASA citation URL, and source PDF SHA-256 checksum recorded by the "
                "Phase 35 multimodal provenance contract."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """Validate complete review and write deterministic evidence outputs."""

    required_paths = [
        TASKS_PATH,
        REVIEWER_A_PATH,
        REVIEWER_B_PATH,
    ]
    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        formatted_paths = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(
            "Multimodal annotation finalization requires all frozen review inputs. "
            f"Missing: {formatted_paths}"
        )

    tasks = load_multimodal_annotation_tasks(TASKS_PATH)
    reviewer_a_responses = load_multimodal_annotation_responses(REVIEWER_A_PATH)
    reviewer_b_responses = load_multimodal_annotation_responses(REVIEWER_B_PATH)

    require_expected_annotator(
        reviewer_a_responses,
        FIRST_ANNOTATOR_ID,
        REVIEWER_A_PATH,
    )
    require_expected_annotator(
        reviewer_b_responses,
        SECOND_ANNOTATOR_ID,
        REVIEWER_B_PATH,
    )

    responses = [
        *reviewer_a_responses,
        *reviewer_b_responses,
    ]
    summary = validate_complete_multimodal_annotation_review(
        tasks,
        responses,
        FIRST_ANNOTATOR_ID,
        SECOND_ANNOTATOR_ID,
    )

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            summary.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        render_report(summary),
        encoding="utf-8",
    )

    print(f"Wrote multimodal agreement summary: {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Wrote multimodal agreement report: {REPORT_PATH.relative_to(ROOT)}")
    print(
        "Raw exact agreement: "
        f"{summary.exact_match_count}/{summary.task_count} "
        f"({summary.exact_match_rate:.6f})"
    )
    print(f"Disagreements: {len(summary.disagreement_task_ids)}")


if __name__ == "__main__":
    main()
