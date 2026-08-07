#!/usr/bin/env python3
"""Run the AeroRAG-X generation v0.3 benchmark with telemetry."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.cli import _load_grounded_answer_generator
from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
    write_generation_evaluation_report,
)
from aeroragx.generation.telemetry_evaluation import (
    evaluate_grounded_generation_with_telemetry,
    write_generation_telemetry_evaluation_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run grounded-generation evaluation once while capturing provider telemetry.")
    )
    parser.add_argument(
        "--queries-input",
        type=Path,
        default=Path("data/evaluation/generation_queries_v0_3.jsonl"),
    )
    parser.add_argument(
        "--generation-config",
        type=Path,
        default=Path("configs/generation_v0_1.yaml"),
    )
    parser.add_argument(
        "--sufficiency-config",
        type=Path,
        default=Path("configs/sufficiency_v0_1.yaml"),
    )
    parser.add_argument(
        "--provider-config",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--http-transport-config",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--provider-runtime-config",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--candidate-top-k",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--evidence-top-k",
        type=int,
        default=5,
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
    args = parse_args()

    queries = load_generation_evaluation_queries(args.queries_input)

    (
        generator,
        reranker_settings,
        generation_settings,
    ) = _load_grounded_answer_generator(
        chunks_input=Path("data/processed/ntrs/v0_1/chunks.jsonl"),
        bm25_config=Path("configs/bm25_v0_1.yaml"),
        dense_config=Path("configs/dense_v0_1.yaml"),
        hybrid_config=Path("configs/hybrid_v0_1.yaml"),
        reranker_config=Path("configs/reranker_v0_1.yaml"),
        generation_config=args.generation_config,
        sufficiency_config=args.sufficiency_config,
        provider_config=args.provider_config,
        http_transport_config=(args.http_transport_config),
        provider_runtime_config=(args.provider_runtime_config),
        embeddings_input=Path("artifacts/embeddings/ntrs_v0_1.npy"),
        metadata_input=Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
        manifest_input=Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
        candidate_top_k=args.candidate_top_k,
        evidence_top_k=args.evidence_top_k,
    )

    telemetry_report = evaluate_grounded_generation_with_telemetry(
        generator=generator,
        queries=queries,
        generation_provider=(generation_settings.provider),
        generation_model=(generation_settings.model_name),
        reranker_model=(reranker_settings.model_name),
    )

    write_generation_evaluation_report(
        args.report_output,
        telemetry_report.generation_report,
    )
    write_generation_telemetry_evaluation_report(
        args.telemetry_output,
        telemetry_report,
    )

    generation = telemetry_report.generation_report
    provider = telemetry_report.provider_summary

    print()
    print("Generation v0.3 benchmark")
    print("-------------------------")
    print("Queries:", generation.query_count)
    print(
        "Answerability accuracy:",
        f"{generation.answerability_accuracy:.4f}",
    )
    print(
        "Answerable completion:",
        f"{generation.answerable_completion_rate:.4f}",
    )
    print(
        "Unsupported refusal:",
        f"{generation.unsupported_refusal_rate:.4f}",
    )
    print(
        "Citation coverage:",
        f"{generation.claim_citation_coverage_rate:.4f}",
    )
    print(
        "Citation validity:",
        f"{generation.citation_reference_validity_rate:.4f}",
    )
    print(
        "Structural validity:",
        f"{generation.structural_validity_rate:.4f}",
    )

    if provider.remote_provider:
        print()
        print("Provider telemetry")
        print("------------------")
        print(
            "Provider calls:",
            provider.provider_call_count,
        )
        print(
            "Provider bypasses:",
            provider.provider_bypass_count,
        )
        print(
            "Call-policy accuracy:",
            provider.provider_call_policy_accuracy,
        )
        print(
            "Retry rate:",
            provider.provider_retry_rate,
        )
        print(
            "P50 latency (s):",
            provider.p50_latency_seconds,
        )
        print(
            "P95 latency (s):",
            provider.p95_latency_seconds,
        )
        print(
            "Total tokens:",
            provider.provider_total_tokens,
        )
        print(
            "Estimated cost (USD):",
            provider.provider_total_estimated_cost_usd,
        )

    print()
    print("Generation report:", args.report_output)
    print("Telemetry report:", args.telemetry_output)


if __name__ == "__main__":
    main()
