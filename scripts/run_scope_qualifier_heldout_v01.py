#!/usr/bin/env python3
"""Run the Phase 28 scope-qualifier held-out evaluation."""

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

QUERIES_INPUT = ROOT / "data/evaluation/scope_qualifier_heldout_v0_1.jsonl"
ADAPTIVE_CONFIG = ROOT / "configs/adaptive_retrieval_v0_1.yaml"

BASELINE_SUFFICIENCY_CONFIG = ROOT / "configs/sufficiency_v0_2_1.yaml"
SCOPE_GUARD_SUFFICIENCY_CONFIG = ROOT / "configs/sufficiency_v0_3_0.yaml"

BASELINE_OUTPUT_JSON = ROOT / "artifacts/evaluation/scope_qualifier_heldout_v0_1_baseline.json"
SCOPE_GUARD_OUTPUT_JSON = (
    ROOT / "artifacts/evaluation/scope_qualifier_heldout_v0_1_scope_guard.json"
)
OUTPUT_REPORT = ROOT / "reports/scope_qualifier_heldout_v0_1.md"


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
        description=(
            "Run the frozen Phase 28 held-out benchmark against the baseline "
            "and opt-in scope-qualifier safeguard."
        )
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permit replacing existing Phase 28 output artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    """Evaluate baseline and candidate policies on the frozen held-out data."""

    args = parse_args()
    output_paths = [
        BASELINE_OUTPUT_JSON,
        SCOPE_GUARD_OUTPUT_JSON,
        OUTPUT_REPORT,
    ]

    existing_outputs = [path for path in output_paths if path.exists()]
    if existing_outputs and not args.overwrite:
        formatted = ", ".join(str(path.relative_to(ROOT)) for path in existing_outputs)
        raise FileExistsError(
            "Phase 28 outputs already exist. Refusing to overwrite: "
            f"{formatted}. Use --overwrite only for an intentional rerun."
        )

    queries = load_generation_evaluation_queries(QUERIES_INPUT)
    validate_query_set(queries)

    baseline = evaluate_policy(
        policy_name="baseline_v0_2_1",
        sufficiency_config=BASELINE_SUFFICIENCY_CONFIG,
        queries=queries,
    )
    scope_guard = evaluate_policy(
        policy_name="scope_guard_v0_3_0",
        sufficiency_config=SCOPE_GUARD_SUFFICIENCY_CONFIG,
        queries=queries,
    )

    write_json(BASELINE_OUTPUT_JSON, baseline)
    write_json(SCOPE_GUARD_OUTPUT_JSON, scope_guard)
    write_text(OUTPUT_REPORT, render_markdown(baseline, scope_guard))

    print("Phase 28 scope-qualifier held-out evaluation")
    print("---------------------------------------------")
    print("Queries:", len(queries))
    print(
        "Baseline bounded-adaptive unsupported refusal:",
        percentage(baseline["bounded_adaptive"]["unsupported_refusal_rate"]),
    )
    print(
        "Scope-guard bounded-adaptive unsupported refusal:",
        percentage(scope_guard["bounded_adaptive"]["unsupported_refusal_rate"]),
    )
    print(
        "Baseline bounded-adaptive false refusals:",
        baseline["summary"]["bounded_adaptive_false_refusal_count"],
    )
    print(
        "Scope-guard bounded-adaptive false refusals:",
        scope_guard["summary"]["bounded_adaptive_false_refusal_count"],
    )
    print("Baseline JSON:", BASELINE_OUTPUT_JSON.relative_to(ROOT))
    print("Scope-guard JSON:", SCOPE_GUARD_OUTPUT_JSON.relative_to(ROOT))
    print("Report:", OUTPUT_REPORT.relative_to(ROOT))


def evaluate_policy(
    *,
    policy_name: str,
    sufficiency_config: Path,
    queries: list[GenerationEvaluationQuery],
) -> dict[str, Any]:
    """Run single-pass and bounded-adaptive conditions for one policy."""

    single_pass_runtime = load_grounded_runtime(
        RuntimeConfig(sufficiency_config=sufficiency_config)
    )
    adaptive_runtime = load_grounded_runtime(
        RuntimeConfig(
            sufficiency_config=sufficiency_config,
            adaptive_retrieval_config=ADAPTIVE_CONFIG,
        )
    )

    if single_pass_runtime.generation_settings != adaptive_runtime.generation_settings:
        raise RuntimeError("Conditions loaded different generation settings.")

    if single_pass_runtime.reranker_settings != adaptive_runtime.reranker_settings:
        raise RuntimeError("Conditions loaded different reranker settings.")

    adaptive_policy = adaptive_runtime.generator.adaptive_retrieval_config
    if adaptive_policy is None:
        raise RuntimeError("Bounded-adaptive condition did not enable recovery.")

    if adaptive_policy.maximum_retrieval_passes != 2:
        raise RuntimeError("Phase 28 requires at most two retrieval passes.")

    if adaptive_policy.maximum_query_rewrites != 1:
        raise RuntimeError("Phase 28 requires at most one query rewrite.")

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

    return {
        "phase": 28,
        "version": "0.1",
        "experiment": "scope_qualifier_heldout_evaluation",
        "policy_name": policy_name,
        "queries_input": str(QUERIES_INPUT.relative_to(ROOT)),
        "sufficiency_config": str(sufficiency_config.relative_to(ROOT)),
        "adaptive_retrieval_config": str(ADAPTIVE_CONFIG.relative_to(ROOT)),
        "query_count": len(queries),
        "constraints": [
            "The held-out benchmark was committed before this evaluation.",
            "Phase 26 protected data and artifacts are not inputs to this run.",
            "No sufficiency thresholds were tuned after observing this run.",
            "The scope safeguard remains opt-in.",
        ],
        "single_pass": single_report.model_dump(mode="json"),
        "bounded_adaptive": adaptive_report.model_dump(mode="json"),
        "adaptive_diagnostics": diagnostics,
        "summary": {
            "single_pass_false_refusal_count": false_refusal_count(single_report),
            "bounded_adaptive_false_refusal_count": false_refusal_count(adaptive_report),
            "single_pass_unsupported_generation_count": unsupported_generation_count(single_report),
            "bounded_adaptive_unsupported_generation_count": (
                unsupported_generation_count(adaptive_report)
            ),
            "adaptive_recovery_trigger_count": sum(
                row.get("recovery_triggered") is True for row in diagnostics
            ),
            "adaptive_successful_recovery_count": sum(
                row.get("recovery_succeeded") is True for row in diagnostics
            ),
            "adaptive_grounded_refusal_count": sum(
                row.get("recovery_grounded_refusal") is True for row in diagnostics
            ),
        },
    }


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
    """Extract bounded adaptive-retrieval facts from one answer."""

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


def validate_query_set(queries: list[GenerationEvaluationQuery]) -> None:
    """Verify the frozen Phase 28 class balance before running expensive work."""

    if len(queries) != 14:
        raise RuntimeError("Phase 28 requires exactly 14 frozen held-out queries.")

    if sum(query.expected_answerable for query in queries) != 4:
        raise RuntimeError("Phase 28 requires exactly four answerable controls.")

    if sum(not query.expected_answerable for query in queries) != 10:
        raise RuntimeError("Phase 28 requires exactly ten refusal challenges.")


def validate_diagnostics(diagnostics: list[dict[str, Any]]) -> None:
    """Verify adaptive bounds and provenance accounting."""

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


def false_refusal_count(report: GenerationEvaluationReport) -> int:
    """Count answerable queries that the system refused."""

    return sum(
        1
        for result in report.query_results
        if result.expected_answerable and result.predicted_answerable is False
    )


def unsupported_generation_count(report: GenerationEvaluationReport) -> int:
    """Count unsupported queries that the system answered."""

    return sum(
        1
        for result in report.query_results
        if not result.expected_answerable and result.predicted_answerable is True
    )


def render_markdown(
    baseline: dict[str, Any],
    scope_guard: dict[str, Any],
) -> str:
    """Render the Phase 28 comparison report."""

    rows = [
        ("Baseline v0.2.1", "Single pass", baseline["single_pass"]),
        ("Baseline v0.2.1", "Bounded adaptive", baseline["bounded_adaptive"]),
        ("Scope guard v0.3.0", "Single pass", scope_guard["single_pass"]),
        (
            "Scope guard v0.3.0",
            "Bounded adaptive",
            scope_guard["bounded_adaptive"],
        ),
    ]

    table_rows = [
        "| Policy | Mode | Answerability accuracy | Unsupported refusal |",
        "|---|---|---:|---:|",
    ]
    table_rows.extend(
        (
            f"| {policy} | {mode} | "
            f"{percentage(report['answerability_accuracy'])} | "
            f"{percentage(report['unsupported_refusal_rate'])} |"
        )
        for policy, mode, report in rows
    )

    return "\n".join(
        [
            "# Phase 28 scope-qualifier held-out evaluation v0.1",
            "",
            "## Scope",
            "",
            "This evaluation compares the existing v0.2.1 sufficiency policy "
            "with the opt-in v0.3.0 scope-qualifier safeguard on a separately "
            "authored, frozen held-out benchmark.",
            "",
            "Phase 26 protected held-out data was not used or modified. "
            "Phase 27 development questions were not reused.",
            "",
            "## Results",
            "",
            *table_rows,
            "",
            "## Safety diagnostics",
            "",
            (
                f"- Baseline bounded-adaptive false refusals: "
                f"{baseline['summary']['bounded_adaptive_false_refusal_count']}"
            ),
            (
                f"- Scope-guard bounded-adaptive false refusals: "
                f"{scope_guard['summary']['bounded_adaptive_false_refusal_count']}"
            ),
            (
                f"- Baseline bounded-adaptive unsupported answers: "
                f"{baseline['summary']['bounded_adaptive_unsupported_generation_count']}"
            ),
            (
                f"- Scope-guard bounded-adaptive unsupported answers: "
                f"{scope_guard['summary']['bounded_adaptive_unsupported_generation_count']}"
            ),
            (
                f"- Scope-guard adaptive recovery triggers: "
                f"{scope_guard['summary']['adaptive_recovery_trigger_count']}"
            ),
            "",
            "## Decision rule",
            "",
            "The v0.3.0 safeguard is acceptable on this held-out benchmark only "
            "if it improves or preserves unsupported-query refusal without "
            "reducing answerability accuracy or increasing false refusals. "
            "Regardless of this result, it remains opt-in until a later policy "
            "decision is separately reviewed.",
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
