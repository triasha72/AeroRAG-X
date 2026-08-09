#!/usr/bin/env python3
"""Run a real local-Transformers AeroRAG-X smoke test."""

from __future__ import annotations

import argparse

from aeroragx.api.service import load_query_service
from aeroragx.api.settings import ApiRuntimeSettings

SUPPORTED_QUERY = "How can battery thermal runaway propagate in electric aircraft?"

UNSUPPORTED_QUERY = (
    "What was the exact cabin temperature recorded "
    "during NASA's 2047 hydrogen-electric aircraft "
    "certification flight?"
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run supported and unsupported queries through the real local Transformers runtime."
        )
    )

    parser.add_argument(
        "--dense-backend",
        choices=[
            "numpy",
            "pgvector",
        ],
        default="numpy",
        help=("Dense retrieval backend to use. Defaults to numpy."),
    )

    return parser.parse_args()


def main() -> None:
    """Run the real local-Transformers smoke test."""

    args = parse_args()

    settings = ApiRuntimeSettings(
        mode="transformers",
        dense_backend=args.dense_backend,
    )

    runtime_config = settings.to_runtime_config()

    print("=" * 80)
    print("AeroRAG-X local Transformers smoke test")
    print("=" * 80)
    print("Runtime mode:", settings.mode)
    print(
        "Dense backend:",
        settings.dense_backend,
    )
    print(
        "Generation config:",
        runtime_config.generation_config,
    )
    print(
        "Provider runtime:",
        runtime_config.provider_runtime_config,
    )
    print()

    print("Loading runtime once...")

    service = load_query_service(runtime_config)

    print("Runtime ready.")
    print()

    cases = [
        (
            "supported",
            SUPPORTED_QUERY,
            False,
        ),
        (
            "unsupported",
            UNSUPPORTED_QUERY,
            True,
        ),
    ]

    failures: list[str] = []

    for (
        label,
        query,
        expected_insufficient,
    ) in cases:
        print("=" * 80)
        print(label.upper())
        print("=" * 80)
        print("Query:", query)

        answer = service.query(query)

        print("Answer:", answer.answer)
        print(
            "Insufficient evidence:",
            answer.insufficient_evidence,
        )
        print(
            "Claims:",
            len(answer.claims),
        )
        print(
            "Citations:",
            len(answer.citations),
        )
        print(
            "Source documents:",
            len(answer.source_documents),
        )

        metadata = answer.retrieval_metadata

        if metadata is not None:
            print(
                "Generation provider:",
                metadata.generation_provider,
            )
            print(
                "Generation model:",
                metadata.generation_model,
            )
            print(
                "Returned evidence:",
                metadata.returned_evidence_count,
            )
            print(
                "Used evidence:",
                metadata.used_evidence_count,
            )

            telemetry = metadata.provider_telemetry

            print(
                "Provider called:",
                telemetry is not None,
            )

            if telemetry is not None:
                print(
                    "Provider succeeded:",
                    telemetry.succeeded,
                )
                print(
                    "Provider attempts:",
                    telemetry.attempts,
                )
                print(
                    "Provider latency (s):",
                    telemetry.latency_seconds,
                )

                if telemetry.usage is not None:
                    print(
                        "Input tokens:",
                        telemetry.usage.input_tokens,
                    )
                    print(
                        "Output tokens:",
                        telemetry.usage.output_tokens,
                    )
                    print(
                        "Total tokens:",
                        telemetry.usage.total_tokens,
                    )

                print(
                    "Estimated API cost:",
                    telemetry.estimated_cost_usd,
                )

        print(
            "Stage timings:",
            answer.stage_timings,
        )
        print()

        if answer.insufficient_evidence != expected_insufficient:
            failures.append(f"{label}: unexpected insufficient_evidence value")

        if label == "supported":
            if not answer.claims:
                failures.append("supported: expected at least one claim")

            if not answer.citations:
                failures.append("supported: expected at least one citation")

            if metadata is None or metadata.provider_telemetry is None:
                failures.append("supported: provider should have been called")

        if label == "unsupported":
            if answer.claims:
                failures.append("unsupported: expected zero claims")

            if answer.citations:
                failures.append("unsupported: expected zero citations")

            if metadata is not None and metadata.provider_telemetry is not None:
                failures.append("unsupported: provider should have been bypassed")

    if failures:
        print("=" * 80)
        print("SMOKE TEST FAILED")
        print("=" * 80)

        for failure in failures:
            print("-", failure)

        raise SystemExit(1)

    print("=" * 80)
    print("SMOKE TEST PASSED")
    print("=" * 80)
    print("Supported query invoked the local model and returned grounded citations.")
    print("Unsupported query was rejected before the local model was called.")


if __name__ == "__main__":
    main()
