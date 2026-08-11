#!/usr/bin/env python3
"""Human-readable inspection of generated LoRA examples."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.training.dataset import (
    TrainingExample,
    load_training_examples,
)
from aeroragx.training.manifest import (
    PlanGenerationReceipt,
    load_dataset_build_config,
    load_dataset_generation_receipt,
)
from aeroragx.training.planning import (
    PlannedExample,
    load_example_plan_manifest,
)


def parse_args() -> argparse.Namespace:
    """Parse dataset-inspection options."""

    parser = argparse.ArgumentParser(
        description=("Inspect generated AeroRAG-X LoRA examples and provenance.")
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/training/dataset_v0_1.yaml"),
    )

    parser.add_argument(
        "--examples-input",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--receipt-input",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--plan-id",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--type",
        choices=[
            "ordinary",
            "synthesis",
            "refusal",
        ],
        default=None,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    return parser.parse_args()


def main() -> int:
    """Print selected training examples."""

    args = parse_args()

    if args.limit < 1:
        raise ValueError("--limit must be at least 1.")

    config = load_dataset_build_config(args.config)

    examples_path = (
        args.examples_input if args.examples_input is not None else Path(config.working.examples)
    )

    receipt_path = (
        args.receipt_input if args.receipt_input is not None else Path(config.working.receipt)
    )

    examples = load_training_examples(examples_path)

    plan_manifest = load_example_plan_manifest(Path(config.inputs.example_plan))

    plan_lookup = {plan.plan_id: plan for plan in plan_manifest.examples}

    receipt_lookup: dict[
        str,
        PlanGenerationReceipt,
    ] = {}

    if receipt_path.exists() and receipt_path.stat().st_size > 0:
        generation_receipt = load_dataset_generation_receipt(receipt_path)

        receipt_lookup = {record.plan_id: record for record in generation_receipt.records}

    selected: list[
        tuple[
            TrainingExample,
            PlannedExample,
            PlanGenerationReceipt | None,
        ]
    ] = []

    for example in examples:
        plan_id = _plan_id_from_example_id(example.example_id)

        plan = plan_lookup.get(plan_id)

        if plan is None:
            continue

        if args.plan_id is not None and plan_id != args.plan_id:
            continue

        if args.type is not None and plan.example_type != args.type:
            continue

        selected.append(
            (
                example,
                plan,
                receipt_lookup.get(plan_id),
            )
        )

    if not selected:
        print("No matching generated examples were found.")

        return 1

    for (
        example,
        plan,
        receipt,
    ) in selected[: args.limit]:
        _print_example(
            example=example,
            plan=plan,
            receipt=receipt,
        )

    return 0


def _plan_id_from_example_id(
    example_id: str,
) -> str:
    """Recover one plan ID from canonical training example ID."""

    prefix = "train_"

    if not example_id.startswith(prefix):
        raise ValueError(f"Unexpected training example ID {example_id!r}.")

    return example_id[len(prefix) :]


def _print_example(
    *,
    example: TrainingExample,
    plan: PlannedExample,
    receipt: (PlanGenerationReceipt | None),
) -> None:
    """Print one example in a manual-review friendly layout."""

    print()
    print("=" * 80)

    print(
        plan.plan_id,
        "|",
        plan.example_type.upper(),
        "| document",
        plan.document_id,
    )

    print()
    print("QUESTION")

    print(example.query)

    print()
    print("EVIDENCE")

    for evidence in example.evidence:
        print()
        print(
            evidence.evidence_id,
            "| chunk",
            evidence.chunk_id,
        )

        print(evidence.text)

    print()
    print("ANSWER")

    print(example.response.answer)

    print()
    print("CLAIMS")

    if not (example.response.claims):
        print("(none)")

    for index, claim in enumerate(
        example.response.claims,
        start=1,
    ):
        print()
        print(
            f"Claim {index}:",
            claim.text,
        )

        print(
            "Evidence:",
            ", ".join(claim.evidence_ids),
        )

    print()
    print(
        "INSUFFICIENT EVIDENCE:",
        example.response.insufficient_evidence,
    )

    if receipt is not None:
        print()
        print("TEACHER TELEMETRY")

        print(
            "Question attempts:",
            receipt.question_attempts,
        )

        print(
            "Verification attempts:",
            receipt.verification_attempts,
        )

        print(
            "Answer attempts:",
            receipt.answer_attempts,
        )

        print(
            "Input tokens:",
            receipt.input_tokens,
        )

        print(
            "Output tokens:",
            receipt.output_tokens,
        )

        print(
            "Estimated cost:",
            f"${receipt.estimated_cost_usd:.6f}",
        )

        print(
            "Telemetry complete:",
            receipt.telemetry_complete,
        )


if __name__ == "__main__":
    raise SystemExit(main())
