#!/usr/bin/env python3
"""Run the AeroRAG-X closed-book Base or LoRA benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from aeroragx.generation.closed_book import (
    ClosedBookCondition,
    ClosedBookGenerator,
    evaluate_closed_book,
    write_closed_book_evaluation_report,
    write_closed_book_telemetry_report,
)
from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
)
from aeroragx.generation.transformers_transport import (
    TransformersStructuredModelTransport,
    load_transformers_runtime_config,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Run closed-book Base or LoRA evaluation on the frozen query set.")
    )

    parser.add_argument(
        "--queries-input",
        type=Path,
        default=Path("data/evaluation/generation_queries_v0_3.jsonl"),
    )

    parser.add_argument(
        "--runtime-config",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--condition",
        choices=[
            "base",
            "lora",
        ],
        required=True,
    )

    parser.add_argument(
        "--model-name",
        default="Qwen/Qwen3-0.6B",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--telemetry-output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    """Run one closed-book evaluation condition."""

    args = parse_args()

    condition = cast(
        ClosedBookCondition,
        args.condition,
    )

    config = load_transformers_runtime_config(args.runtime_config)

    adapter_enabled = config.adapter_path is not None

    if condition == "base" and adapter_enabled:
        raise ValueError("Base condition must not configure an adapter.")

    if condition == "lora" and not adapter_enabled:
        raise ValueError("LoRA condition must configure an adapter.")

    queries = load_generation_evaluation_queries(args.queries_input)

    transport = TransformersStructuredModelTransport(
        model_name=args.model_name,
        config=config,
    )

    generator = ClosedBookGenerator(
        model_name=args.model_name,
        transport=transport,
        timeout_seconds=(args.timeout_seconds),
    )

    (
        report,
        telemetry,
    ) = evaluate_closed_book(
        generator=generator,
        queries=queries,
        condition=condition,
        adapter_enabled=(adapter_enabled),
    )

    write_closed_book_evaluation_report(
        args.report_output,
        report,
    )

    write_closed_book_telemetry_report(
        args.telemetry_output,
        telemetry,
    )

    print()
    print("Closed-book evaluation v0.1")
    print("---------------------------")

    print(
        "Condition:",
        report.condition,
    )

    print(
        "Model:",
        report.generation_model,
    )

    print(
        "Adapter enabled:",
        report.adapter_enabled,
    )

    print(
        "Queries:",
        report.query_count,
    )

    print(
        "Completed:",
        report.completed_query_count,
    )

    print(
        "Generation failures:",
        report.generation_failure_count,
    )

    print(
        "Answerability accuracy:",
        f"{report.answerability_accuracy:.4f}",
    )

    print(
        "Answerable completion:",
        f"{report.answerable_completion_rate:.4f}",
    )

    print(
        "Unsupported refusal:",
        f"{report.unsupported_refusal_rate:.4f}",
    )

    print(
        "Expected-term recall:",
        f"{report.expected_term_recall:.4f}",
    )

    print(
        "Structural validity:",
        f"{report.structural_validity_rate:.4f}",
    )

    print(
        "Answerable claims:",
        report.answerable_claim_count,
    )

    print(
        "Claims / answerable query:",
        (f"{report.claims_per_answerable_query:.4f}"),
    )

    print(
        "Claims on unsupported queries:",
        report.unanswerable_claim_count,
    )

    print()
    print("Provider telemetry")
    print("------------------")

    print(
        "Input tokens:",
        telemetry.total_input_tokens,
    )

    print(
        "Output tokens:",
        telemetry.total_output_tokens,
    )

    print(
        "Total tokens:",
        telemetry.total_tokens,
    )

    print(
        "Mean latency (s):",
        telemetry.mean_latency_seconds,
    )

    print(
        "P50 latency (s):",
        telemetry.p50_latency_seconds,
    )

    print(
        "P95 latency (s):",
        telemetry.p95_latency_seconds,
    )

    if report.generation_failure_count > 0:
        print()
        print("Failures by query")
        print("-----------------")

        for result in report.query_results:
            if not result.generation_failed:
                continue

            print(
                result.query_id,
                "->",
                result.failure_type,
            )

    print()
    print(
        "Evaluation report:",
        args.report_output,
    )

    print(
        "Telemetry report:",
        args.telemetry_output,
    )


if __name__ == "__main__":
    main()
