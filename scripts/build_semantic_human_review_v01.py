"""Build the protected four-way semantic human-review queue."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from aeroragx.evaluation.semantic import (
    evaluate_alias_concept_coverage,
    load_semantic_annotations,
)

ROOT = Path(__file__).resolve().parents[1]

ANNOTATION_PATH = ROOT / "data" / "evaluation" / "generation_semantic_concepts_v0_1.jsonl"

OUTPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_queue_v0_1.jsonl"

PENDING_PATH = ROOT / "artifacts" / "evaluation" / "semantic_human_review_pending_v0_1.md"

SYSTEMS = {
    "base_closed_book": (
        ROOT / "artifacts" / "evaluation" / "generation_transformers_base_closed_book_v0_2.json"
    ),
    "lora_closed_book": (
        ROOT / "artifacts" / "evaluation" / "generation_transformers_lora_closed_book_v0_2.json"
    ),
    "base_rag": (ROOT / "artifacts" / "evaluation" / "generation_transformers_base_v0_3.json"),
    "lora_rag": (ROOT / "artifacts" / "evaluation" / "generation_transformers_lora_v0_3.json"),
}


def main() -> None:
    annotations = load_semantic_annotations(ANNOTATION_PATH)

    rows: list[dict[str, object]] = []

    for system_name, source_path in SYSTEMS.items():
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        report = json.loads(source_path.read_text(encoding="utf-8"))

        query_results = {str(row["query_id"]): row for row in report["query_results"]}

        for annotation in annotations:
            query_result = query_results.get(annotation.query_id)

            if query_result is None:
                raise RuntimeError(f"Missing query result for {system_name}:{annotation.query_id}")

            answer = str(query_result.get("answer") or "")

            deterministic = evaluate_alias_concept_coverage(
                answer=answer,
                annotation=annotation,
            )

            match_by_concept = {match.concept_id: match for match in deterministic.concept_matches}

            for concept in annotation.expected_concepts:
                match = match_by_concept[concept.concept_id]

                auto_supported = bool(match.matched)

                rows.append(
                    {
                        "review_id": (f"{system_name}:{annotation.query_id}:{concept.concept_id}"),
                        "system": system_name,
                        "source_file": str(source_path.relative_to(ROOT)),
                        "query_id": (annotation.query_id),
                        "query": str(query_result["query"]),
                        "answer": answer,
                        "concept_id": (concept.concept_id),
                        "canonical_text": (concept.canonical_text),
                        "accepted_phrases": (concept.accepted_phrases),
                        "deterministic_matched": (auto_supported),
                        "deterministic_match_method": (match.match_method),
                        "deterministic_matched_phrase": (match.matched_phrase),
                        "review_status": (
                            "AUTO_SUPPORTED" if auto_supported else "REVIEW_REQUIRED"
                        ),
                        "human_label": ("PRESENT" if auto_supported else None),
                        "reviewer_note": None,
                    }
                )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    sort_keys=True,
                )
                + "\n"
            )

    pending = [row for row in rows if row["review_status"] == "REVIEW_REQUIRED"]

    markdown: list[str] = [
        "# Semantic Human Review — v0.1",
        "",
        ("Use only PRESENT, ABSENT, or AMBIGUOUS for unresolved concept decisions."),
        "",
    ]

    current_group: tuple[str, str] | None = None

    for row in pending:
        group = (
            str(row["system"]),
            str(row["query_id"]),
        )

        if group != current_group:
            markdown.extend(
                [
                    "---",
                    "",
                    (f"## {row['system']} · {row['query_id']}"),
                    "",
                    f"**Question:** {row['query']}",
                    "",
                    f"**Answer:** {row['answer']}",
                    "",
                ]
            )
            current_group = group

        markdown.extend(
            [
                (f"### {row['concept_id']}"),
                "",
                (f"Expected: {row['canonical_text']}"),
                "",
                "Decision: `PRESENT / ABSENT / AMBIGUOUS`",
                "",
            ]
        )

    PENDING_PATH.write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )

    counts = Counter(str(row["review_status"]) for row in rows)

    by_system = Counter(str(row["system"]) for row in rows)

    print("systems:", len(SYSTEMS))
    print("rows:", len(rows))
    print("status counts:", dict(counts))
    print("rows per system:", dict(by_system))
    print("pending review:", len(pending))
    print("queue:", OUTPUT_PATH)
    print("pending:", PENDING_PATH)


if __name__ == "__main__":
    main()
