"""Tests for the Phase 26 bounded adaptive-retrieval comparison."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aeroragx.generation.adaptive_evaluation import (
    AdaptiveRetrievalEvaluationConfig,
    compare_protected_baseline,
    evaluate_adaptive_retrieval,
    render_adaptive_retrieval_evaluation_markdown,
    write_adaptive_retrieval_evaluation_report,
)
from aeroragx.generation.adaptive_retrieval import (
    AdaptiveEvidenceAssessment,
    AdaptiveEvidenceProvenance,
    AdaptiveRetrievalAttempt,
    AdaptiveRetrievalState,
    AdaptiveRetrievalTrace,
)
from aeroragx.generation.evaluation import (
    GenerationEvaluationQuery,
    evaluate_grounded_generation,
)
from aeroragx.generation.grounded import (
    AnswerCitation,
    GroundedAnswer,
    GroundedClaim,
    RAGStageTimings,
    RetrievalMetadata,
    SourceDocument,
)


class FakeGenerator:
    """Return preconfigured answers for evaluator-focused tests."""

    def __init__(
        self,
        answers: dict[str, GroundedAnswer],
    ) -> None:
        self._answers = answers

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        """Return a deep copy so each evaluation sees an isolated answer."""

        del reranker_model
        return self._answers[query].model_copy(deep=True)


def make_config(
    **overrides: object,
) -> AdaptiveRetrievalEvaluationConfig:
    """Create a complete, isolated Phase 26 protocol."""

    queries_input = Path("data/evaluation/heldout.jsonl")
    protected_baseline_report = Path("artifacts/evaluation/baseline.json")
    phase25_baseline_manifest = Path("artifacts/evaluation/phase25_manifest.json")
    chunks_input = Path("data/processed/chunks.jsonl")
    bm25_config = Path("configs/bm25.yaml")
    dense_config = Path("configs/dense.yaml")
    hybrid_config = Path("configs/hybrid.yaml")
    reranker_config = Path("configs/reranker.yaml")
    generation_config = Path("configs/generation.yaml")
    sufficiency_config = Path("configs/sufficiency.yaml")
    facet_retrieval_config = Path("configs/facet.yaml")
    adaptive_retrieval_config = Path("configs/adaptive.yaml")
    embeddings_input = Path("artifacts/embeddings.npy")
    metadata_input = Path("artifacts/metadata.jsonl")
    manifest_input = Path("artifacts/manifest.json")

    frozen_inputs = [
        queries_input,
        protected_baseline_report,
        phase25_baseline_manifest,
        chunks_input,
        bm25_config,
        dense_config,
        hybrid_config,
        reranker_config,
        generation_config,
        sufficiency_config,
        facet_retrieval_config,
        adaptive_retrieval_config,
        embeddings_input,
        metadata_input,
        manifest_input,
    ]
    pinned_input_sha256 = {
        queries_input: "a" * 64,
        protected_baseline_report: "b" * 64,
        phase25_baseline_manifest: "c" * 64,
        bm25_config: "d" * 64,
        dense_config: "e" * 64,
        hybrid_config: "f" * 64,
        reranker_config: "1" * 64,
        generation_config: "2" * 64,
        sufficiency_config: "3" * 64,
        facet_retrieval_config: "4" * 64,
        adaptive_retrieval_config: "5" * 64,
        manifest_input: "6" * 64,
    }

    values: dict[str, object] = {
        "version": "0.1",
        "phase": 26,
        "queries_input": queries_input,
        "protected_baseline_report": protected_baseline_report,
        "phase25_baseline_manifest": phase25_baseline_manifest,
        "chunks_input": chunks_input,
        "bm25_config": bm25_config,
        "dense_config": dense_config,
        "hybrid_config": hybrid_config,
        "reranker_config": reranker_config,
        "generation_config": generation_config,
        "sufficiency_config": sufficiency_config,
        "facet_retrieval_config": facet_retrieval_config,
        "adaptive_retrieval_config": adaptive_retrieval_config,
        "embeddings_input": embeddings_input,
        "metadata_input": metadata_input,
        "manifest_input": manifest_input,
        "candidate_top_k": 20,
        "evidence_top_k": 5,
        "maximum_retrieval_passes": 2,
        "maximum_query_rewrites": 1,
        "minimum_successful_recoveries": 1,
        "frozen_inputs": frozen_inputs,
        "pinned_input_sha256": pinned_input_sha256,
        "inputs_output": Path("artifacts/evaluation/inputs.sha256"),
        "baseline_output": Path("artifacts/evaluation/baseline_result.json"),
        "adaptive_output": Path("artifacts/evaluation/adaptive_result.json"),
        "comparison_output": Path("artifacts/evaluation/comparison.json"),
        "report_output": Path("reports/adaptive.md"),
        "protected_constraints": ["Do not tune from the held-out result."],
    }
    values.update(overrides)

    return AdaptiveRetrievalEvaluationConfig.model_validate(values)


def make_provenance(
    attempt_number: int,
) -> AdaptiveEvidenceProvenance:
    """Create one complete adaptive provenance row."""

    return AdaptiveEvidenceProvenance(
        attempt_number=attempt_number,
        reranker_rank=1,
        chunk_id=f"1001:chunk:{attempt_number:05d}",
        document_id=1001,
        page_start=4,
        page_end=5,
        citation_url="https://ntrs.nasa.gov/citations/1001",
        source_url="https://ntrs.nasa.gov/documents/1001.pdf",
        document_sha256="a" * 64,
        reranker_score=8.0,
        hybrid_rank=1,
        hybrid_score=0.02,
        retrieved_by=["bm25", "dense"],
        bm25_rank=1,
        bm25_score=10.0,
        dense_rank=1,
        dense_score=0.8,
    )


def one_pass_trace(
    query: str,
    *,
    terminal_state: str,
) -> AdaptiveRetrievalTrace:
    """Create one valid no-recovery adaptive trace."""

    sufficient = terminal_state == "generate"
    terminal = (
        AdaptiveRetrievalState.GENERATE if sufficient else AdaptiveRetrievalState.GROUNDED_REFUSAL
    )

    return AdaptiveRetrievalTrace(
        original_query=query,
        states=[
            AdaptiveRetrievalState.RETRIEVE_INITIAL,
            AdaptiveRetrievalState.ASSESS_INITIAL,
            terminal,
        ],
        attempts=[
            AdaptiveRetrievalAttempt(
                attempt_number=1,
                retrieval_query=query,
                returned_evidence_count=1,
                used_evidence_count=1,
                assessment=AdaptiveEvidenceAssessment(
                    sufficient=sufficient,
                    reasons=[] if sufficient else ["low_query_term_coverage"],
                ),
                evidence_provenance=[make_provenance(1)],
            )
        ],
        retrieval_terminal_state=terminal_state,
    )


def successful_recovery_trace(
    query: str,
) -> AdaptiveRetrievalTrace:
    """Create a valid two-pass trace that recovers on attempt two."""

    rewritten_query = f"{query} NASA aerospace technical report"

    return AdaptiveRetrievalTrace(
        original_query=query,
        rewritten_query=rewritten_query,
        states=[
            AdaptiveRetrievalState.RETRIEVE_INITIAL,
            AdaptiveRetrievalState.ASSESS_INITIAL,
            AdaptiveRetrievalState.REWRITE_QUERY,
            AdaptiveRetrievalState.RETRIEVE_RECOVERY,
            AdaptiveRetrievalState.ASSESS_RECOVERY,
            AdaptiveRetrievalState.GENERATE,
        ],
        attempts=[
            AdaptiveRetrievalAttempt(
                attempt_number=1,
                retrieval_query=query,
                returned_evidence_count=1,
                used_evidence_count=1,
                assessment=AdaptiveEvidenceAssessment(
                    sufficient=False,
                    reasons=["low_query_term_coverage"],
                ),
                evidence_provenance=[make_provenance(1)],
            ),
            AdaptiveRetrievalAttempt(
                attempt_number=2,
                retrieval_query=rewritten_query,
                returned_evidence_count=1,
                used_evidence_count=1,
                assessment=AdaptiveEvidenceAssessment(sufficient=True),
                evidence_provenance=[make_provenance(2)],
            ),
        ],
        retrieval_terminal_state="generate",
    )


def supported_answer(
    query: str,
    *,
    answer_text: str,
    trace: AdaptiveRetrievalTrace | None,
) -> GroundedAnswer:
    """Create a structurally valid supported answer with optional adaptive trace."""

    citation = AnswerCitation(
        citation_id="C1",
        evidence_id="E1",
        chunk_id="1001:chunk:00001",
        document_id=1001,
        page_start=4,
        page_end=5,
        citation_url="https://ntrs.nasa.gov/citations/1001",
        source_url="https://ntrs.nasa.gov/documents/1001.pdf",
        document_sha256="a" * 64,
        reranker_rank=1,
    )
    answer = GroundedAnswer(
        query=query,
        answer=answer_text,
        claims=[
            GroundedClaim(
                claim_id="CL1",
                text=answer_text,
                citation_ids=[citation.citation_id],
            )
        ],
        citations=[citation],
        source_documents=[
            SourceDocument(
                document_id=1001,
                citation_url=citation.citation_url,
                source_url=citation.source_url,
                page_ranges=["4-5"],
                chunk_ids=[citation.chunk_id],
            )
        ],
        insufficient_evidence=False,
        retrieval_metadata=_retrieval_metadata(trace),
    )
    _attach_timings(answer, trace)
    return answer


def refusal_answer(
    query: str,
    *,
    trace: AdaptiveRetrievalTrace | None,
) -> GroundedAnswer:
    """Create a structurally valid grounded refusal with optional adaptive trace."""

    answer = GroundedAnswer(
        query=query,
        answer="The retrieved evidence is insufficient to answer this question reliably.",
        claims=[],
        citations=[],
        source_documents=[],
        insufficient_evidence=True,
        retrieval_metadata=_retrieval_metadata(trace),
    )
    _attach_timings(answer, trace)
    return answer


def _retrieval_metadata(
    trace: AdaptiveRetrievalTrace | None,
) -> RetrievalMetadata:
    """Create retrieval facts compatible with the answer fixtures."""

    return RetrievalMetadata(
        retriever="hybrid-reranked",
        requested_evidence_top_k=5,
        returned_evidence_count=1,
        used_evidence_count=1,
        reranker_model="test-reranker",
        generation_provider="fake",
        generation_model="deterministic-test",
        adaptive_retrieval=trace,
    )


def _attach_timings(
    answer: GroundedAnswer,
    trace: AdaptiveRetrievalTrace | None,
) -> None:
    """Attach stage timings consistent with the optional recovery trace."""

    attempt_count = len(trace.attempts) if trace is not None else 1
    rewrite_count = 1 if trace is not None and trace.rewritten_query is not None else 0
    answer.attach_stage_timings(
        RAGStageTimings(
            retrieval_ms=float(4 * attempt_count),
            evidence_build_ms=float(attempt_count),
            sufficiency_ms=float(attempt_count),
            retrieval_attempt_count=attempt_count,
            query_rewrite_count=rewrite_count,
            total_ms=float(10 * attempt_count),
        )
    )


def protected_baseline(
    *,
    queries: list[GenerationEvaluationQuery],
    answers: dict[str, GroundedAnswer],
) -> dict[str, object]:
    """Build a baseline artifact that the paired run must exactly reproduce."""

    report = evaluate_grounded_generation(
        generator=FakeGenerator(answers),
        queries=queries,
        generation_provider="fake",
        generation_model="deterministic-test",
        reranker_model="test-reranker",
    )
    return report.model_dump(mode="json")


def evaluate_pair(
    *,
    queries: list[GenerationEvaluationQuery],
    single_pass_answers: dict[str, GroundedAnswer],
    adaptive_answers: dict[str, GroundedAnswer],
) -> object:
    """Evaluate one paired fixture with the normal Phase 26 API."""

    return evaluate_adaptive_retrieval(
        single_pass_generator=FakeGenerator(single_pass_answers),
        bounded_adaptive_generator=FakeGenerator(adaptive_answers),
        queries=queries,
        generation_provider="fake",
        generation_model="deterministic-test",
        reranker_model="test-reranker",
        protected_baseline=protected_baseline(
            queries=queries,
            answers=single_pass_answers,
        ),
        config=make_config(),
    )


def test_config_rejects_a_missing_pinned_protected_input() -> None:
    config = make_config()
    values = config.model_dump(mode="python")
    pins = values["pinned_input_sha256"]

    assert isinstance(pins, dict)
    del pins[Path("configs/generation.yaml")]

    with pytest.raises(ValueError, match="missing required Phase 26 inputs"):
        AdaptiveRetrievalEvaluationConfig.model_validate(values)


def test_evaluation_reports_a_valid_successful_recovery() -> None:
    answerable_query = GenerationEvaluationQuery(
        query_id="answerable",
        query="How does battery cooling work?",
        expected_answerable=True,
        expected_terms=["battery"],
    )
    unsupported_query = GenerationEvaluationQuery(
        query_id="unsupported",
        query="What fictional code was assigned to a SkyCell aircraft?",
        expected_answerable=False,
    )
    queries = [answerable_query, unsupported_query]
    single_pass_answers = {
        answerable_query.query: refusal_answer(answerable_query.query, trace=None),
        unsupported_query.query: refusal_answer(unsupported_query.query, trace=None),
    }
    adaptive_answers = {
        answerable_query.query: supported_answer(
            answerable_query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=successful_recovery_trace(answerable_query.query),
        ),
        unsupported_query.query: refusal_answer(
            unsupported_query.query,
            trace=one_pass_trace(
                unsupported_query.query,
                terminal_state="grounded_refusal",
            ),
        ),
    }

    report = evaluate_pair(
        queries=queries,
        single_pass_answers=single_pass_answers,
        adaptive_answers=adaptive_answers,
    )

    assert report.protected_baseline_parity.matched is True
    assert report.bounded_adaptive.recovery_trigger_count == 1
    assert report.bounded_adaptive.successful_recovery_count == 1
    assert report.bounded_adaptive.recovery_grounded_refusal_count == 0
    assert report.bounded_adaptive.total_retrieval_attempts == 3
    assert report.bounded_adaptive.total_query_rewrites == 1
    assert report.safety_checks.integrity_passed is True
    assert report.safety_checks.quality_non_regression_passed is True
    assert report.safety_checks.quality_improvement_observed is True
    assert report.verdict == "benefit_observed"


def test_evaluation_accepts_a_safe_run_without_recovery_activation() -> None:
    answerable_query = GenerationEvaluationQuery(
        query_id="answerable",
        query="How does battery cooling work?",
        expected_answerable=True,
        expected_terms=["battery"],
    )
    unsupported_query = GenerationEvaluationQuery(
        query_id="unsupported",
        query="What fictional code was assigned to a SkyCell aircraft?",
        expected_answerable=False,
    )
    queries = [answerable_query, unsupported_query]
    single_pass_answers = {
        answerable_query.query: supported_answer(
            answerable_query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=None,
        ),
        unsupported_query.query: refusal_answer(unsupported_query.query, trace=None),
    }
    adaptive_answers = {
        answerable_query.query: supported_answer(
            answerable_query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=one_pass_trace(answerable_query.query, terminal_state="generate"),
        ),
        unsupported_query.query: refusal_answer(
            unsupported_query.query,
            trace=one_pass_trace(
                unsupported_query.query,
                terminal_state="grounded_refusal",
            ),
        ),
    }

    report = evaluate_pair(
        queries=queries,
        single_pass_answers=single_pass_answers,
        adaptive_answers=adaptive_answers,
    )

    assert report.protected_baseline_parity.matched is True
    assert report.bounded_adaptive.recovery_trigger_count == 0
    assert report.safety_checks.integrity_passed is True
    assert report.verdict == "safe_no_recovery_activated"


def test_evaluation_does_not_claim_benefit_without_a_quality_improvement() -> None:
    query = GenerationEvaluationQuery(
        query_id="answerable",
        query="How does battery cooling work?",
        expected_answerable=True,
        expected_terms=["battery"],
    )
    answer_text = "Battery cooling removes heat from the battery system."
    single_pass_answers = {
        query.query: supported_answer(
            query.query,
            answer_text=answer_text,
            trace=None,
        )
    }
    adaptive_answers = {
        query.query: supported_answer(
            query.query,
            answer_text=answer_text,
            trace=successful_recovery_trace(query.query),
        )
    }

    report = evaluate_pair(
        queries=[query],
        single_pass_answers=single_pass_answers,
        adaptive_answers=adaptive_answers,
    )

    assert report.bounded_adaptive.successful_recovery_count == 1
    assert report.safety_checks.quality_improvement_observed is False
    assert report.verdict == "safe_no_measured_benefit"


def test_evaluation_rejects_missing_adaptive_trace_as_an_integrity_regression() -> None:
    query = GenerationEvaluationQuery(
        query_id="answerable",
        query="How does battery cooling work?",
        expected_answerable=True,
        expected_terms=["battery"],
    )
    single_pass_answers = {
        query.query: supported_answer(
            query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=None,
        )
    }
    adaptive_answers = {
        query.query: supported_answer(
            query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=None,
        )
    }

    report = evaluate_pair(
        queries=[query],
        single_pass_answers=single_pass_answers,
        adaptive_answers=adaptive_answers,
    )

    assert report.bounded_adaptive.missing_trace_count == 1
    assert report.safety_checks.all_adaptive_traces_valid is False
    assert report.verdict == "integrity_regression"


def test_baseline_parity_checks_the_full_existing_query_result() -> None:
    query = GenerationEvaluationQuery(
        query_id="answerable",
        query="How does battery cooling work?",
        expected_answerable=True,
        expected_terms=["battery"],
    )
    expected_answer = supported_answer(
        query.query,
        answer_text="Battery cooling removes heat from the battery system.",
        trace=None,
    )
    changed_answer = supported_answer(
        query.query,
        answer_text="Battery cooling uses a changed but still valid answer.",
        trace=None,
    )
    protected = protected_baseline(
        queries=[query],
        answers={query.query: expected_answer},
    )
    changed_report = evaluate_grounded_generation(
        generator=FakeGenerator({query.query: changed_answer}),
        queries=[query],
        generation_provider="fake",
        generation_model="deterministic-test",
        reranker_model="test-reranker",
    )

    parity = compare_protected_baseline(
        report=changed_report,
        protected_baseline=protected,
        protected_report_path=Path("artifacts/evaluation/baseline.json"),
    )

    assert parity.matched is False
    assert "query_results[answerable].answer" in parity.mismatched_items


def test_report_writers_render_a_completed_comparison(tmp_path: Path) -> None:
    query = GenerationEvaluationQuery(
        query_id="answerable",
        query="How does battery cooling work?",
        expected_answerable=True,
        expected_terms=["battery"],
    )
    single_pass_answers = {
        query.query: supported_answer(
            query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=None,
        )
    }
    adaptive_answers = {
        query.query: supported_answer(
            query.query,
            answer_text="Battery cooling removes heat from the battery system.",
            trace=one_pass_trace(query.query, terminal_state="generate"),
        )
    }
    report = evaluate_pair(
        queries=[query],
        single_pass_answers=single_pass_answers,
        adaptive_answers=adaptive_answers,
    )
    output_path = tmp_path / "comparison.json"

    write_adaptive_retrieval_evaluation_report(output_path, report)
    rendered = render_adaptive_retrieval_evaluation_markdown(report)

    assert json.loads(output_path.read_text(encoding="utf-8"))["verdict"] == (
        "safe_no_recovery_activated"
    )
    assert "# Phase 26 bounded adaptive-retrieval evaluation v0.1" in rendered
    assert "**Verdict: `safe_no_recovery_activated`**" in rendered
