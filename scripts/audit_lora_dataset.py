#!/usr/bin/env python3
"""Audit generated LoRA data against its frozen plan and evaluation boundary."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
)
from aeroragx.training.dataset import (
    TrainingExample,
    audit_training_leakage,
    load_training_examples,
    normalize_training_text,
)
from aeroragx.training.manifest import (
    load_dataset_build_config,
    load_dataset_generation_receipt,
)
from aeroragx.training.planning import (
    load_example_plan_manifest,
)
from aeroragx.training.protected import (
    load_protected_document_manifest,
)
from aeroragx.training.selection import (
    load_source_selection_manifest,
)


def parse_args() -> argparse.Namespace:
    """Parse dataset-audit options."""

    parser = argparse.ArgumentParser(
        description=("Audit generated AeroRAG-X LoRA examples against frozen provenance.")
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/training/dataset_v0_1.yaml"),
    )

    parser.add_argument(
        "--training-input",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--receipt-input",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--require-complete",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    """Run all deterministic dataset audits."""

    args = parse_args()

    config = load_dataset_build_config(args.config)

    training_path = (
        args.training_input if args.training_input is not None else Path(config.working.examples)
    )

    receipt_path = (
        args.receipt_input if args.receipt_input is not None else Path(config.working.receipt)
    )

    examples = load_training_examples(training_path)

    plan_manifest = load_example_plan_manifest(Path(config.inputs.example_plan))

    source_selection = load_source_selection_manifest(Path(config.inputs.source_selection))

    protected_manifest = load_protected_document_manifest(Path(config.inputs.protected_manifest))

    protected_queries = load_generation_evaluation_queries(Path(config.inputs.protected_queries))

    protected_query_lookup = {query.query_id: query.query for query in protected_queries}

    protected_answers = _load_supported_protected_answers(
        Path(config.inputs.protected_generation_report)
    )

    plan_lookup = {plan.plan_id: plan for plan in plan_manifest.examples}

    errors: list[str] = []

    observed_plan_ids: set[str] = set()

    for example in examples:
        plan_id = _plan_id_from_example_id(example.example_id)

        observed_plan_ids.add(plan_id)

        plan = plan_lookup.get(plan_id)

        if plan is None:
            errors.append(f"{example.example_id}: no matching frozen plan.")

            continue

        observed_chunks = [evidence.chunk_id for evidence in example.evidence]

        if observed_chunks != plan.chunk_ids:
            errors.append(f"{example.example_id}: evidence chunks do not match frozen plan.")

        if example.source_document_ids != (plan.document_id,):
            errors.append(f"{example.example_id}: source document does not match frozen plan.")

        if plan.document_id not in source_selection.selected_document_id_set:
            errors.append(
                f"{example.example_id}: source document is not in frozen source selection."
            )

        if plan.document_id in protected_manifest.protected_document_id_set:
            errors.append(f"{example.example_id}: source document is protected.")

    receipt = None

    if receipt_path.exists() and receipt_path.stat().st_size > 0:
        receipt = load_dataset_generation_receipt(receipt_path)

        accepted_receipt_ids = receipt.accepted_plan_ids

        if observed_plan_ids != accepted_receipt_ids:
            errors.append("Accepted receipt plan IDs do not exactly match training JSONL plan IDs.")

    elif args.require_complete:
        errors.append("A complete dataset audit requires a generation receipt.")

    if args.require_complete:
        if len(examples) != config.expected.total:
            errors.append(
                "Complete dataset example count "
                f"is {len(examples)}; "
                f"expected {config.expected.total}."
            )

        if receipt is None or not receipt.is_complete:
            errors.append("Generation receipt is not complete.")

    leakage = audit_training_leakage(
        examples,
        protected_queries=(protected_query_lookup),
        protected_answers=(protected_answers),
        protected_document_ids=(protected_manifest.protected_document_id_set),
    )

    exact_duplicates = _duplicate_questions(
        examples,
        normalize=False,
    )

    normalized_duplicates = _duplicate_questions(
        examples,
        normalize=True,
    )

    if exact_duplicates:
        errors.append("Exact duplicate generated questions were detected.")

    if normalized_duplicates:
        errors.append("Normalized duplicate generated questions were detected.")

    if leakage.has_leakage:
        errors.append("Protected evaluation leakage was detected.")

    report = {
        "training_examples": (len(examples)),
        "frozen_plans": (plan_manifest.planned_example_count),
        "selected_documents": (source_selection.selected_document_count),
        "protected_queries": (leakage.protected_query_count),
        "protected_answers": (leakage.protected_answer_count),
        "protected_documents": (leakage.protected_document_count),
        "leakage_findings": [finding.model_dump(mode="json") for finding in leakage.findings],
        "exact_duplicate_questions": (exact_duplicates),
        "normalized_duplicate_questions": (normalized_duplicates),
        "errors": errors,
    }

    report_output = (
        args.report_output if args.report_output is not None else Path(config.outputs.audit_report)
    )

    report_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    _print_report(report)

    print()
    print(
        "Report:",
        report_output,
    )

    return 1 if errors else 0


def _plan_id_from_example_id(
    example_id: str,
) -> str:
    """Recover frozen plan ID from canonical training example ID."""

    prefix = "train_"

    if not example_id.startswith(prefix):
        raise ValueError(
            f"Training example ID does not use the canonical train_ prefix: {example_id!r}."
        )

    plan_id = example_id[len(prefix) :]

    if not plan_id:
        raise ValueError("Training example ID contains no plan identifier.")

    return plan_id


def _duplicate_questions(
    examples: list[TrainingExample],
    *,
    normalize: bool,
) -> dict[
    str,
    list[str],
]:
    """Return exact or normalized duplicate-question groups."""

    lookup: defaultdict[
        str,
        list[str],
    ] = defaultdict(list)

    for example in examples:
        key = normalize_training_text(example.query) if normalize else example.query

        lookup[key].append(example.example_id)

    return {key: ids for key, ids in lookup.items() if len(ids) > 1}


def _load_supported_protected_answers(
    path: Path,
) -> dict[str, str]:
    """Load supported benchmark outputs for leakage checking."""

    raw_value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(
        raw_value,
        dict,
    ):
        raise ValueError("Protected generation report must contain a JSON object.")

    query_results = raw_value.get("query_results")

    if not isinstance(
        query_results,
        list,
    ):
        raise ValueError("Protected generation report must contain query_results.")

    answers: dict[
        str,
        str,
    ] = {}

    for row in query_results:
        if not isinstance(
            row,
            dict,
        ):
            raise ValueError("Protected query result must contain a JSON object.")

        if row.get("expected_answerable") is not True:
            continue

        if row.get("generation_failed") is True:
            continue

        query_id = row.get("query_id")

        answer = row.get("answer")

        if not isinstance(
            query_id,
            str,
        ):
            raise ValueError("Protected result has invalid query_id.")

        if not isinstance(
            answer,
            str,
        ):
            raise ValueError("Protected result has invalid answer.")

        normalized = answer.strip()

        if normalized:
            answers[query_id] = normalized

    return answers


def _print_report(
    report: dict[str, Any],
) -> None:
    """Print compact audit results."""

    print()
    print("=== LORA DATASET AUDIT ===")

    print(
        "Training examples:",
        report["training_examples"],
    )

    print(
        "Frozen plans:",
        report["frozen_plans"],
    )

    print(
        "Protected documents:",
        report["protected_documents"],
    )

    print(
        "Leakage findings:",
        len(report["leakage_findings"]),
    )

    print(
        "Exact duplicate groups:",
        len(report["exact_duplicate_questions"]),
    )

    print(
        "Normalized duplicate groups:",
        len(report["normalized_duplicate_questions"]),
    )

    print(
        "Errors:",
        len(report["errors"]),
    )

    for error in report["errors"]:
        print(
            "-",
            error,
        )


if __name__ == "__main__":
    raise SystemExit(main())
