#!/usr/bin/env python3
"""Generate resumable grounded LoRA examples from the frozen example plan."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.generation.grounded import (
    load_generation_config,
)
from aeroragx.generation.provider_factory import (
    create_configured_generation_provider,
)
from aeroragx.generation.structured_provider import (
    ProviderResponseValidationError,
    ProviderTransportError,
)
from aeroragx.retrieval.bm25 import (
    load_chunk_records,
)
from aeroragx.training.builder import (
    ExampleBuildError,
    TrainingExampleBuilder,
)
from aeroragx.training.dataset import (
    TrainingExample,
    load_training_examples,
    write_training_examples,
)
from aeroragx.training.manifest import (
    DatasetGenerationReceipt,
    PlanGenerationReceipt,
    load_dataset_build_config,
    load_dataset_generation_receipt,
    make_dataset_generation_receipt,
    receipt_from_build_result,
    unsuccessful_plan_receipt,
    write_dataset_generation_receipt,
)
from aeroragx.training.planning import (
    PlannedExample,
    load_example_plan_manifest,
)
from aeroragx.training.protected import (
    load_protected_document_manifest,
)
from aeroragx.training.selection import (
    load_source_selection_manifest,
    sha256_file,
)
from aeroragx.training.teacher import (
    TeacherError,
    create_openai_teacher_client,
    load_teacher_config,
)


def parse_args() -> argparse.Namespace:
    """Parse generation options."""

    parser = argparse.ArgumentParser(
        description=("Generate validated AeroRAG-X LoRA training examples from frozen plans.")
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/training/dataset_v0_1.yaml"),
    )

    selection = parser.add_mutually_exclusive_group(required=True)

    selection.add_argument(
        "--plan-ids",
        nargs="+",
    )

    selection.add_argument(
        "--limit",
        type=int,
    )

    selection.add_argument(
        "--all",
        action="store_true",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
    )

    parser.add_argument(
        "--examples-output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--receipt-output",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def main() -> int:
    """Generate the explicitly requested subset of frozen plans."""

    args = parse_args()

    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1.")

    dataset_config = load_dataset_build_config(args.config)

    teacher_config_path = Path(dataset_config.teacher.config)

    teacher_config = load_teacher_config(teacher_config_path)

    plan_path = Path(dataset_config.inputs.example_plan)

    plan_manifest = load_example_plan_manifest(plan_path)

    if plan_manifest.planned_example_count != dataset_config.expected.total:
        raise RuntimeError("Frozen plan count does not match dataset configuration.")

    source_selection = load_source_selection_manifest(Path(dataset_config.inputs.source_selection))

    protected_manifest = load_protected_document_manifest(
        Path(dataset_config.inputs.protected_manifest)
    )

    chunks = load_chunk_records(Path(dataset_config.inputs.chunks))

    examples_output = (
        args.examples_output
        if args.examples_output is not None
        else Path(dataset_config.working.examples)
    )

    receipt_output = (
        args.receipt_output
        if args.receipt_output is not None
        else Path(dataset_config.working.receipt)
    )

    existing_examples: dict[
        str,
        TrainingExample,
    ] = {}

    existing_records: dict[
        str,
        PlanGenerationReceipt,
    ] = {}

    if args.resume:
        if examples_output.exists() and examples_output.stat().st_size > 0:
            for example in load_training_examples(examples_output):
                existing_examples[example.example_id] = example

        if receipt_output.exists() and receipt_output.stat().st_size > 0:
            receipt = load_dataset_generation_receipt(receipt_output)

            _assert_resume_compatible(
                receipt=receipt,
                dataset_config_path=(args.config),
                teacher_config_path=(teacher_config_path),
                plan_path=(plan_path),
            )

            existing_records = {record.plan_id: record for record in receipt.records}

    else:
        existing_nonempty = [
            path
            for path in [
                examples_output,
                receipt_output,
            ]
            if (path.exists() and path.stat().st_size > 0)
        ]

        if existing_nonempty:
            raise RuntimeError(
                "Working generation artifacts already "
                "exist. Use --resume or choose "
                "different output paths."
            )

    plan_lookup = {plan.plan_id: plan for plan in plan_manifest.examples}

    selected_plans = _select_plans(
        all_plans=(plan_manifest.examples),
        plan_lookup=(plan_lookup),
        accepted_plan_ids={
            plan_id for plan_id, record in existing_records.items() if record.status == "accepted"
        },
        requested_plan_ids=(args.plan_ids),
        limit=args.limit,
        select_all=args.all,
    )

    question_client = create_openai_teacher_client(teacher_config)

    generation_config = load_generation_config(Path(teacher_config.provider.generation_config))

    answer_provider = create_configured_generation_provider(
        generation_config=(generation_config),
        provider_config=Path(teacher_config.provider.provider_config),
        http_transport_config=Path(teacher_config.provider.http_transport_config),
        provider_runtime_config=Path(teacher_config.provider.provider_runtime_config),
    )

    builder = TrainingExampleBuilder(
        chunks=chunks,
        selected_document_ids=(source_selection.selected_document_id_set),
        protected_document_ids=(protected_manifest.protected_document_id_set),
        teacher_config=(teacher_config),
        question_client=(question_client),
        answer_provider=(answer_provider),
    )

    requested_plan_ids = {plan.plan_id for plan in selected_plans}

    for plan in selected_plans:
        previous = existing_records.get(plan.plan_id)

        if args.resume and previous is not None and previous.status == "accepted":
            print(
                plan.plan_id,
                "already accepted; skipping.",
            )

            continue

        print()
        print(
            "Generating",
            plan.plan_id,
            f"({plan.example_type})",
        )

        try:
            result = builder.build(plan)

        except ExampleBuildError as error:
            record = unsuccessful_plan_receipt(
                plan,
                status="rejected",
                reason=str(error),
            )

            existing_records[plan.plan_id] = record

            print(
                "REJECTED:",
                error,
            )

        except (
            ProviderTransportError,
            ProviderResponseValidationError,
            TeacherError,
        ) as error:
            record = unsuccessful_plan_receipt(
                plan,
                status="failed",
                reason=str(error),
            )

            existing_records[plan.plan_id] = record

            print(
                "FAILED:",
                error,
            )

        else:
            record = receipt_from_build_result(result)

            existing_records[plan.plan_id] = record

            existing_examples[result.example.example_id] = result.example

            print(
                "ACCEPTED:",
                result.example.example_id,
            )

        _persist_state(
            dataset_config_path=(args.config),
            teacher_config_path=(teacher_config_path),
            plan_path=(plan_path),
            planned_example_count=(plan_manifest.planned_example_count),
            version=(dataset_config.version),
            examples_output=(examples_output),
            receipt_output=(receipt_output),
            examples=(existing_examples),
            records=(existing_records),
        )

    final_receipt = _build_receipt(
        dataset_config_path=(args.config),
        teacher_config_path=(teacher_config_path),
        plan_path=(plan_path),
        planned_example_count=(plan_manifest.planned_example_count),
        version=(dataset_config.version),
        records=(existing_records),
    )

    _print_summary(final_receipt)

    status_by_plan = {record.plan_id: record.status for record in final_receipt.records}

    requested_failures = [
        plan_id for plan_id in requested_plan_ids if (status_by_plan.get(plan_id) != "accepted")
    ]

    if requested_failures:
        print()
        print("REQUESTED GENERATION INCOMPLETE")

        print(
            "Unaccepted plans:",
            ", ".join(sorted(requested_failures)),
        )

        return 1

    if args.all and not final_receipt.is_complete:
        print()
        print("DATASET INCOMPLETE")

        return 1

    print()
    print("Requested generation completed successfully.")

    return 0


def _select_plans(
    *,
    all_plans: list[PlannedExample],
    plan_lookup: dict[str, PlannedExample],
    accepted_plan_ids: set[str],
    requested_plan_ids: (list[str] | None),
    limit: int | None,
    select_all: bool,
) -> list[PlannedExample]:
    """Resolve explicit command-line plan selection."""

    if requested_plan_ids is not None:
        unknown = [plan_id for plan_id in requested_plan_ids if plan_id not in plan_lookup]

        if unknown:
            raise ValueError("Unknown plan IDs: " + ", ".join(unknown))

        if len(requested_plan_ids) != len(set(requested_plan_ids)):
            raise ValueError("--plan-ids must not contain duplicates.")

        return [plan_lookup[plan_id] for plan_id in requested_plan_ids]

    remaining = [plan for plan in all_plans if plan.plan_id not in accepted_plan_ids]

    if limit is not None:
        return remaining[:limit]

    if select_all:
        return list(all_plans)

    raise AssertionError("Plan selection was not resolved.")


def _build_receipt(
    *,
    dataset_config_path: Path,
    teacher_config_path: Path,
    plan_path: Path,
    planned_example_count: int,
    version: str,
    records: dict[str, PlanGenerationReceipt],
) -> DatasetGenerationReceipt:
    """Build aggregate receipt from the current checkpoint state."""

    return make_dataset_generation_receipt(
        version=version,
        example_plan_path=str(plan_path),
        example_plan_sha256=(sha256_file(plan_path)),
        teacher_config_path=str(teacher_config_path),
        teacher_config_sha256=(sha256_file(teacher_config_path)),
        dataset_config_path=str(dataset_config_path),
        dataset_config_sha256=(sha256_file(dataset_config_path)),
        planned_example_count=(planned_example_count),
        records=list(records.values()),
    )


def _persist_state(
    *,
    dataset_config_path: Path,
    teacher_config_path: Path,
    plan_path: Path,
    planned_example_count: int,
    version: str,
    examples_output: Path,
    receipt_output: Path,
    examples: dict[str, TrainingExample],
    records: dict[str, PlanGenerationReceipt],
) -> None:
    """Checkpoint accepted examples and generation receipt."""

    if examples:
        ordered_examples = sorted(
            examples.values(),
            key=lambda example: example.example_id,
        )

        write_training_examples(
            examples_output,
            ordered_examples,
        )

    receipt = _build_receipt(
        dataset_config_path=(dataset_config_path),
        teacher_config_path=(teacher_config_path),
        plan_path=(plan_path),
        planned_example_count=(planned_example_count),
        version=version,
        records=records,
    )

    write_dataset_generation_receipt(
        receipt_output,
        receipt,
    )


def _assert_resume_compatible(
    *,
    receipt: DatasetGenerationReceipt,
    dataset_config_path: Path,
    teacher_config_path: Path,
    plan_path: Path,
) -> None:
    """Reject resume when frozen generation provenance has changed."""

    if receipt.example_plan_sha256 != sha256_file(plan_path):
        raise RuntimeError("Cannot resume: example-plan hash changed.")

    if receipt.teacher_config_sha256 != sha256_file(teacher_config_path):
        raise RuntimeError("Cannot resume: teacher-config hash changed.")

    if receipt.dataset_config_sha256 != sha256_file(dataset_config_path):
        raise RuntimeError("Cannot resume: dataset-config hash changed.")


def _print_summary(
    receipt: DatasetGenerationReceipt,
) -> None:
    """Print compact generation progress."""

    summary = receipt.summary

    print()
    print("=== LORA DATASET GENERATION ===")

    print(
        "Frozen plans:",
        receipt.planned_example_count,
    )

    print(
        "Recorded:",
        summary.record_count,
    )

    print(
        "Accepted:",
        summary.accepted_count,
    )

    print(
        "Rejected:",
        summary.rejected_count,
    )

    print(
        "Failed:",
        summary.failed_count,
    )

    print(
        "Ordinary accepted:",
        summary.ordinary_accepted_count,
    )

    print(
        "Synthesis accepted:",
        summary.synthesis_accepted_count,
    )

    print(
        "Refusal accepted:",
        summary.refusal_accepted_count,
    )

    print(
        "Input tokens:",
        summary.total_input_tokens,
    )

    print(
        "Output tokens:",
        summary.total_output_tokens,
    )

    print(f"Estimated external API cost: ${summary.total_estimated_cost_usd:.6f}")

    print(
        "Telemetry complete:",
        summary.telemetry_complete,
    )


if __name__ == "__main__":
    raise SystemExit(main())
