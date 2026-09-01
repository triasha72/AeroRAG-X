#!/usr/bin/env python3
"""Run the AeroRAG-X generation v0.3 benchmark with telemetry."""

from __future__ import annotations

import argparse
import gc
from pathlib import Path
from typing import Sequence

from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
    write_generation_evaluation_report,
)
from aeroragx.generation.telemetry_evaluation import (
    evaluate_grounded_generation_with_telemetry,
    write_generation_telemetry_evaluation_report,
)
from aeroragx.runtime import (
    AeroRAGRuntime,
    RuntimeConfig,
    load_reranker_index,
    load_grounded_runtime,
)
from aeroragx.generation.facet_retrieval import (
    FacetAwareEvidenceIndex,
    load_facet_retrieval_config,
)
from aeroragx.generation.grounded import (
    GroundedAnswerGenerator,
    load_generation_config,
    with_evidence_top_k,
)
from aeroragx.generation.provider_factory import create_configured_generation_provider
from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    load_sufficiency_config,
)
from aeroragx.retrieval.reranker import RerankedSearchHit


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
        "--facet-retrieval-config",
        type=Path,
        default=None,
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

    parser.add_argument(
        "--memory-bounded",
        action="store_true",
        help=(
            "Precompute the complete evaluation query hit set, release retrieval "
            "models, and then load the generation model. This preserves the "
            "benchmark protocol while reducing peak unified-memory use."
        ),
    )

    return parser.parse_args()


class _FrozenQueryIndex:
    """Serve exact precomputed reranked hits for a closed evaluation query set."""

    def __init__(self, hits_by_query: dict[str, list[RerankedSearchHit]]) -> None:
        self._hits_by_query = hits_by_query

    def search(self, query: str, top_k: int = 10) -> Sequence[RerankedSearchHit]:
        try:
            hits = self._hits_by_query[query]
        except KeyError as exc:
            raise KeyError(f"Query was not included in the frozen retrieval pass: {query!r}") from exc
        return hits[:top_k]


def _release_retrieval_models() -> None:
    """Return Python and MPS caches before the generation model is constructed."""

    gc.collect()
    try:
        import torch

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except (ImportError, RuntimeError):
        pass


def _load_memory_bounded_runtime(
    config: RuntimeConfig,
    query_texts: Sequence[str],
) -> AeroRAGRuntime:
    """Build an equivalent closed-set runtime without overlapping model families."""

    reranker_index, reranker_settings = load_reranker_index(config)
    retrieval_index = reranker_index
    if config.facet_retrieval_config is not None:
        retrieval_index = FacetAwareEvidenceIndex(
            reranker_index,
            load_facet_retrieval_config(config.facet_retrieval_config),
        )

    evidence_top_k = config.evidence_top_k or 5
    hits_by_query: dict[str, list[RerankedSearchHit]] = {}
    for position, query in enumerate(query_texts, start=1):
        print(f"Retrieval prepass {position}/{len(query_texts)}", flush=True)
        hits_by_query[query] = list(retrieval_index.search(query=query, top_k=evidence_top_k))

    frozen_index = _FrozenQueryIndex(hits_by_query)
    del retrieval_index
    del reranker_index
    _release_retrieval_models()
    print("Retrieval models released; loading generation model.", flush=True)

    generation_settings = with_evidence_top_k(
        load_generation_config(config.generation_config),
        config.evidence_top_k,
    )
    provider = create_configured_generation_provider(
        generation_config=generation_settings,
        provider_config=config.provider_config,
        http_transport_config=config.http_transport_config,
        provider_runtime_config=config.provider_runtime_config,
    )
    generator = GroundedAnswerGenerator(
        index=frozen_index,
        provider=provider,
        config=generation_settings,
        sufficiency_assessor=EvidenceSufficiencyAssessor(
            load_sufficiency_config(config.sufficiency_config)
        ),
    )
    return AeroRAGRuntime(
        generator=generator,
        reranker_settings=reranker_settings,
        generation_settings=generation_settings,
    )


def main() -> None:
    args = parse_args()

    queries = load_generation_evaluation_queries(args.queries_input)

    runtime_config = RuntimeConfig(
            generation_config=(args.generation_config),
            sufficiency_config=(args.sufficiency_config),
            facet_retrieval_config=(args.facet_retrieval_config),
            provider_config=(args.provider_config),
            http_transport_config=(args.http_transport_config),
            provider_runtime_config=(args.provider_runtime_config),
            candidate_top_k=(args.candidate_top_k),
            evidence_top_k=(args.evidence_top_k),
        )
    runtime = (
        _load_memory_bounded_runtime(
            runtime_config,
            [query.query for query in queries],
        )
        if args.memory_bounded
        else load_grounded_runtime(runtime_config)
    )

    generator = runtime.generator

    reranker_settings = runtime.reranker_settings

    generation_settings = runtime.generation_settings

    telemetry_report = evaluate_grounded_generation_with_telemetry(
        generator=generator,
        queries=queries,
        generation_provider=(generation_settings.provider),
        generation_model=(generation_settings.model_name),
        reranker_model=(reranker_settings.model_name),
        continue_on_error=True,
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

    print(
        "Queries:",
        generation.query_count,
    )

    print(
        "Completed queries:",
        generation.completed_query_count,
    )

    print(
        "Generation failures:",
        generation.generation_failure_count,
    )

    print(
        "Generation failure rate:",
        (f"{generation.generation_failure_rate:.4f}"),
    )

    print()

    print(
        "Answerability accuracy:",
        (f"{generation.answerability_accuracy:.4f}"),
    )

    print(
        "Answerable completion:",
        (f"{generation.answerable_completion_rate:.4f}"),
    )

    print(
        "Unsupported refusal:",
        (f"{generation.unsupported_refusal_rate:.4f}"),
    )

    print(
        "Citation coverage:",
        (f"{generation.claim_citation_coverage_rate:.4f}"),
    )

    print(
        "Citation validity:",
        (f"{generation.citation_reference_validity_rate:.4f}"),
    )

    print(
        "Source-document coverage:",
        (f"{generation.source_document_coverage_rate:.4f}"),
    )

    print(
        "Expected-term recall:",
        (f"{generation.expected_term_recall:.4f}"),
    )

    print(
        "Structural validity:",
        (f"{generation.structural_validity_rate:.4f}"),
    )

    if provider.telemetry_expected:
        print()

        print("Provider telemetry")

        print("------------------")

        print(
            "Provider kind:",
            provider.provider_kind,
        )

        print(
            "Provider calls:",
            provider.provider_call_count,
        )

        print(
            "Provider bypasses:",
            provider.provider_bypass_count,
        )

        print(
            "Provider call state unknown:",
            provider.provider_call_unknown_count,
        )

        print(
            "Call-policy evaluated:",
            (provider.provider_call_policy_evaluated_count),
        )

        print(
            "Call-policy accuracy:",
            (provider.provider_call_policy_accuracy),
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
            "Input tokens:",
            (provider.provider_total_input_tokens),
        )

        print(
            "Output tokens:",
            (provider.provider_total_output_tokens),
        )

        print(
            "Total tokens:",
            provider.provider_total_tokens,
        )

        print(
            "Estimated cost (USD):",
            (provider.provider_total_estimated_cost_usd),
        )

    print()

    if generation.generation_failure_count > 0:
        print("Generation failures by query")

        print("----------------------------")

        for result in generation.query_results:
            if not result.generation_failed:
                continue

            print(
                result.query_id,
                "->",
                result.failure_type,
            )

        print()

    print(
        "Generation report:",
        args.report_output,
    )

    print(
        "Telemetry report:",
        args.telemetry_output,
    )


if __name__ == "__main__":
    main()
