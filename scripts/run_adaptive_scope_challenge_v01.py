#!/usr/bin/env python3
"""Run the Phase 27 development-only unsupported-scope baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
    GenerationEvaluationReport,
    GroundedGenerationSystem,
    evaluate_grounded_generation,
    load_generation_evaluation_queries,
)
from aeroragx.generation.grounded import GroundedAnswer
from aeroragx.runtime import RuntimeConfig, load_grounded_runtime

ROOT = Path(__file__).resolve().parents[1]
QUERIES_INPUT = ROOT / "data/evaluation/adaptive_scope_challenge_v0_1.jsonl"
ADAPTIVE_CONFIG = ROOT / "configs/adaptive_retrieval_v0_1.yaml"
OUTPUT_JSON = ROOT / "artifacts/evaluation/adaptive_scope_challenge_v0_1_baseline.json"
OUTPUT_MARKDOWN = ROOT / "reports/adaptive_scope_challenge_v0_1_baseline.md"


class CapturingGenerator:
    """Wrap a generator and retain answers for adaptive-trace diagnostics."""

    def __init__(self, generator: GroundedGenerationSystem) -> None:
        self._generator = generator
        self.answers: list[GroundedAnswer] = []

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        """Generate and retain one answer."""

        answer = self._generator.generate(
            query,
            reranker_model=reranker_model,
        )
        self.answers.append(answer)
        return answer


def parse_args() -> argparse.Namespace:
    """Parse execution controls."""

    parser = argparse.ArgumentParser(
        description=("Run the Phase 27 development-only unsupported-scope baseline.")
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permit replacing existing Phase 27 baseline outputs.",
    )
    return parser.parse_args()


def main() -> None:
    """Run unchanged single-pass and bounded-adaptive conditions."""

    args = parse_args()

    existing_outputs = [path for path in [OUTPUT_JSON, OUTPUT_MARKDOWN] if path.exists()]
    if existing_outputs and not args.overwrite:
        formatted = ", ".join(str(path.relative_to(ROOT)) for path in existing_outputs)
        raise FileExistsError(
            "Phase 27 outputs already exist. Refusing to overwrite: "
            f"{formatted}. Use --overwrite only for an intentional rerun."
        )

    queries = load_generation_evaluation_queries(QUERIES_INPUT)

    single_pass_runtime = load_grounded_runtime(RuntimeConfig())

    adaptive_runtime = load_grounded_runtime(
        RuntimeConfig(adaptive_retrieval_config=ADAPTIVE_CONFIG)
    )

    if single_pass_runtime.generation_settings != adaptive_runtime.generation_settings:
        raise RuntimeError("Conditions loaded different generation settings.")

    if single_pass_runtime.reranker_settings != adaptive_runtime.reranker_settings:
        raise RuntimeError("Conditions loaded different reranker settings.")

    adaptive_policy = adaptive_runtime.generator.adaptive_retrieval_config
    if adaptive_policy is None:
        raise RuntimeError("Bounded-adaptive condition did not enable recovery.")

    if adaptive_policy.maximum_retrieval_passes != 2:
        raise RuntimeError("Phase 27 requires at most two retrieval passes.")

    if adaptive_policy.maximum_query_rewrites != 1:
        raise RuntimeError("Phase 27 requires at most one query rewrite.")

    single_report, _ = evaluate_condition(
        generator=single_pass_runtime.generator,
        queries=queries,
        provider=single_pass_runtime.generation_settings.provider,
        model=single_pass_runtime.generation_settings.model_name,
        reranker_model=single_pass_runtime.reranker_settings.model_name,
    )

    adaptive_report, adaptive_answers = evaluate_condition(
        generator=adaptive_runtime.generator,
        queries=queries,
        provider=adaptive_runtime.generation_settings.provider,
        model=adaptive_runtime.generation_settings.model_name,
        reranker_model=adaptive_runtime.reranker_settings.model_name,
    )

    if len(adaptive_answers) != len(queries):
        raise RuntimeError("Adaptive answer count does not match query count.")

    diagnostics = [
        adaptive_diagnostic(query.query_id, answer)
        for query, answer in zip(queries, adaptive_answers, strict=True)
    ]

    validate_diagnostics(diagnostics)

    adaptive_unanswerable_results = [
        result for result in adaptive_report.query_results if not result.expected_answerable
    ]

    summary = {
        "single_pass_answerability_accuracy": single_report.answerability_accuracy,
        "bounded_adaptive_answerability_accuracy": adaptive_report.answerability_accuracy,
        "single_pass_unsupported_refusal_rate": (single_report.unsupported_refusal_rate),
        "bounded_adaptive_unsupported_refusal_rate": (adaptive_report.unsupported_refusal_rate),
        "adaptive_recovery_trigger_count": sum(
            row.get("recovery_triggered") is True for row in diagnostics
        ),
        "adaptive_successful_recovery_count": sum(
            row.get("recovery_succeeded") is True for row in diagnostics
        ),
        "adaptive_grounded_refusal_count": sum(
            row.get("recovery_grounded_refusal") is True for row in diagnostics
        ),
        "adaptive_unsupported_generation_count": sum(
            result.predicted_answerable is True for result in adaptive_unanswerable_results
        ),
        "adaptive_unanswerable_query_count": len(adaptive_unanswerable_results),
    }

    result: dict[str, Any] = {
        "phase": 27,
        "version": "0.1",
        "experiment": "development_only_unsupported_scope_baseline",
        "queries_input": str(QUERIES_INPUT.relative_to(ROOT)),
        "query_count": len(queries),
        "constraints": [
            "This is a development-only experiment.",
            "Phase 26 held-out queries and artifacts are not inputs to this run.",
            "The Phase 25 bounded adaptive policy is evaluated unchanged.",
        ],
        "single_pass": single_report.model_dump(mode="json"),
        "bounded_adaptive": adaptive_report.model_dump(mode="json"),
        "adaptive_diagnostics": diagnostics,
        "summary": summary,
    }

    write_json(OUTPUT_JSON, result)
    write_text(OUTPUT_MARKDOWN, render_markdown(result))

    print("Phase 27 development-only unsupported-scope baseline")
    print("-----------------------------------------------------")
    print("Queries:", len(queries))
    print(
        "Single-pass unsupported refusal:",
        percentage(single_report.unsupported_refusal_rate),
    )
    print(
        "Bounded-adaptive unsupported refusal:",
        percentage(adaptive_report.unsupported_refusal_rate),
    )
    print("Adaptive recovery triggers:", summary["adaptive_recovery_trigger_count"])
    print(
        "Unsupported queries answered after adaptive retrieval:",
        summary["adaptive_unsupported_generation_count"],
    )
    print("Comparison artifact:", OUTPUT_JSON.relative_to(ROOT))
    print("Markdown report:", OUTPUT_MARKDOWN.relative_to(ROOT))


def evaluate_condition(
    *,
    generator: GroundedGenerationSystem,
    queries: list[GenerationEvaluationQuery],
    provider: str,
    model: str,
    reranker_model: str | None,
) -> tuple[GenerationEvaluationReport, list[GroundedAnswer]]:
    """Evaluate one condition and retain generated answers."""

    capturing_generator = CapturingGenerator(generator)

    report = evaluate_grounded_generation(
        generator=capturing_generator,
        queries=queries,
        generation_provider=provider,
        generation_model=model,
        reranker_model=reranker_model,
        continue_on_error=False,
    )

    return report, capturing_generator.answers


def adaptive_diagnostic(
    query_id: str,
    answer: GroundedAnswer,
) -> dict[str, Any]:
    """Extract development-only facts from one adaptive answer."""

    metadata = answer.retrieval_metadata
    trace = metadata.adaptive_retrieval if metadata is not None else None

    if trace is None:
        return {
            "query_id": query_id,
            "missing_trace": True,
            "insufficient_evidence": answer.insufficient_evidence,
        }

    recovery_triggered = len(trace.attempts) == 2

    return {
        "query_id": query_id,
        "missing_trace": False,
        "insufficient_evidence": answer.insufficient_evidence,
        "retrieval_terminal_state": trace.retrieval_terminal_state,
        "original_query": trace.original_query,
        "rewritten_query": trace.rewritten_query,
        "retrieval_attempt_count": len(trace.attempts),
        "query_rewrite_count": int(trace.rewritten_query is not None),
        "recovery_triggered": recovery_triggered,
        "recovery_succeeded": (recovery_triggered and trace.retrieval_terminal_state == "generate"),
        "recovery_grounded_refusal": (
            recovery_triggered and trace.retrieval_terminal_state == "grounded_refusal"
        ),
        "attempts": [
            {
                "attempt_number": attempt.attempt_number,
                "retrieval_query": attempt.retrieval_query,
                "assessment_sufficient": attempt.assessment.sufficient,
                "assessment_reasons": attempt.assessment.reasons,
                "returned_evidence_count": attempt.returned_evidence_count,
                "provenance_count": len(attempt.evidence_provenance),
            }
            for attempt in trace.attempts
        ],
    }


def validate_diagnostics(diagnostics: list[dict[str, Any]]) -> None:
    """Verify unchanged adaptive bounds and provenance accounting."""

    for diagnostic in diagnostics:
        query_id = diagnostic["query_id"]

        if diagnostic["missing_trace"]:
            raise RuntimeError(f"Adaptive trace is missing for {query_id}.")

        if diagnostic["retrieval_attempt_count"] not in {1, 2}:
            raise RuntimeError(f"Retrieval bound failed for {query_id}.")

        if diagnostic["query_rewrite_count"] not in {0, 1}:
            raise RuntimeError(f"Rewrite bound failed for {query_id}.")

        for attempt in diagnostic["attempts"]:
            if attempt["returned_evidence_count"] != attempt["provenance_count"]:
                raise RuntimeError(f"Provenance accounting failed for {query_id}.")


def render_markdown(result: dict[str, Any]) -> str:
    """Render the concise Phase 27 baseline report."""

    single_pass = result["single_pass"]
    adaptive = result["bounded_adaptive"]
    summary = result["summary"]

    return "\n".join(
        [
            "# Phase 27 unsupported-scope development baseline v0.1",
            "",
            "## Scope",
            "",
            "This is a development-only evaluation of the unchanged Phase 25 "
            "bounded adaptive-retrieval policy. It does not reuse or modify "
            "the protected Phase 26 held-out benchmark.",
            "",
            "## Results",
            "",
            "| Metric | Single pass | Bounded adaptive |",
            "|---|---:|---:|",
            (
                "| Answerability accuracy | "
                f"{percentage(single_pass['answerability_accuracy'])} | "
                f"{percentage(adaptive['answerability_accuracy'])} |"
            ),
            (
                "| Unsupported refusal | "
                f"{percentage(single_pass['unsupported_refusal_rate'])} | "
                f"{percentage(adaptive['unsupported_refusal_rate'])} |"
            ),
            "",
            "## Adaptive behavior",
            "",
            f"- Recovery triggers: {summary['adaptive_recovery_trigger_count']}",
            f"- Successful recoveries: {summary['adaptive_successful_recovery_count']}",
            f"- Recovery grounded refusals: {summary['adaptive_grounded_refusal_count']}",
            (
                "- Unsupported queries answered after adaptive retrieval: "
                f"{summary['adaptive_unsupported_generation_count']} "
                f"of {summary['adaptive_unanswerable_query_count']}"
            ),
            "",
            "## Interpretation",
            "",
            "This baseline records current behavior before any scope-protection "
            "policy is designed or enabled.",
            "",
        ]
    )


def percentage(value: object) -> str:
    """Format a proportion as a percentage."""

    if not isinstance(value, int | float):
        raise TypeError(f"Expected numeric metric, received {value!r}.")

    return f"{value * 100:.2f}%"


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    """Write one UTF-8 report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


if __name__ == "__main__":
    main()
