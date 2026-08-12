"""Tests for the deterministic Phase 25 bounded recovery controller."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from aeroragx.generation.adaptive_retrieval import (
    AdaptiveEvidenceAssessment,
    AdaptiveEvidenceProvenance,
    AdaptiveRetrievalConfig,
    AdaptiveRetrievalState,
    BoundedAdaptiveRetrievalController,
    DeterministicQueryRewriter,
    load_adaptive_retrieval_config,
)


@dataclass(frozen=True)
class FakeHitSet:
    """Minimal retrieval result used to exercise generic controller behavior."""

    name: str
    evidence: list[str]


def make_config(
    **overrides: object,
) -> AdaptiveRetrievalConfig:
    """Create one valid bounded policy."""

    values: dict[str, object] = {
        "version": "0.1",
        "maximum_retrieval_passes": 2,
        "maximum_query_rewrites": 1,
        "recovery_trigger": "insufficient_evidence",
        "rewrite_strategy": "append_domain_context",
        "rewrite_context_terms": ["NASA", "aerospace", "technical", "report"],
    }
    values.update(overrides)

    return AdaptiveRetrievalConfig.model_validate(values)


def make_provenance(
    attempt_number: int,
) -> AdaptiveEvidenceProvenance:
    """Create one complete retrieval provenance record."""

    return AdaptiveEvidenceProvenance(
        attempt_number=attempt_number,
        reranker_rank=1,
        chunk_id=f"chunk-{attempt_number}",
        document_id=1000 + attempt_number,
        page_start=1,
        page_end=1,
        citation_url=f"https://ntrs.nasa.gov/citations/{1000 + attempt_number}",
        source_url=f"https://ntrs.nasa.gov/documents/{1000 + attempt_number}.pdf",
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


def execute(
    controller: BoundedAdaptiveRetrievalController[FakeHitSet, str],
    hit_sets: list[FakeHitSet],
    assessments: list[AdaptiveEvidenceAssessment],
):
    """Execute the controller against deterministic retrieval fixtures."""

    received_queries: list[str] = []

    def retrieve(query: str) -> FakeHitSet:
        received_queries.append(query)
        return hit_sets[len(received_queries) - 1]

    assessment_index = 0

    def assess(evidence: list[str]) -> AdaptiveEvidenceAssessment:
        nonlocal assessment_index
        del evidence
        result = assessments[assessment_index]
        assessment_index += 1
        return result

    outcome = controller.execute(
        original_query="How does thermal runaway propagate?",
        retrieve=retrieve,
        build_evidence=lambda hit_set: hit_set.evidence,
        assess_evidence=assess,
        build_provenance=lambda hit_set, attempt_number: [make_provenance(attempt_number)],
        returned_evidence_count=lambda hit_set: 1,
    )

    return outcome, received_queries


def test_valid_config_enforces_one_rewrite_for_two_retrieval_passes() -> None:
    config = make_config()

    assert config.maximum_retrieval_passes == 2
    assert config.maximum_query_rewrites == 1


def test_config_rejects_a_third_retrieval_pass() -> None:
    with pytest.raises(ValueError, match="less than or equal to 2"):
        make_config(maximum_retrieval_passes=3, maximum_query_rewrites=2)


def test_config_rejects_inconsistent_rewrite_bound() -> None:
    with pytest.raises(ValueError, match="must equal maximum_retrieval_passes - 1"):
        make_config(maximum_query_rewrites=0)


def test_load_config(tmp_path: Path) -> None:
    path = tmp_path / "adaptive.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            "maximum_retrieval_passes: 2\n"
            "maximum_query_rewrites: 1\n"
            'recovery_trigger: "insufficient_evidence"\n'
            'rewrite_strategy: "append_domain_context"\n'
            "rewrite_context_terms:\n"
            "  - NASA\n"
        ),
        encoding="utf-8",
    )

    config = load_adaptive_retrieval_config(path)

    assert config.rewrite_context_terms == ["NASA"]


def test_sufficient_initial_evidence_generates_without_a_rewrite() -> None:
    controller = BoundedAdaptiveRetrievalController[FakeHitSet, str](make_config())
    outcome, received_queries = execute(
        controller,
        [FakeHitSet(name="initial", evidence=["supported evidence"])],
        [AdaptiveEvidenceAssessment(sufficient=True)],
    )

    assert received_queries == ["How does thermal runaway propagate?"]
    assert [hit_set.name for hit_set in outcome.hit_sets] == ["initial"]
    assert outcome.trace.rewritten_query is None
    assert outcome.trace.retrieval_terminal_state == "generate"
    assert outcome.trace.states == [
        AdaptiveRetrievalState.RETRIEVE_INITIAL,
        AdaptiveRetrievalState.ASSESS_INITIAL,
        AdaptiveRetrievalState.GENERATE,
    ]
    assert len(outcome.trace.attempts) == 1


def test_insufficient_initial_evidence_uses_exactly_one_recovery_pass() -> None:
    controller = BoundedAdaptiveRetrievalController[FakeHitSet, str](make_config())
    outcome, received_queries = execute(
        controller,
        [
            FakeHitSet(name="initial", evidence=["weak evidence"]),
            FakeHitSet(name="recovery", evidence=["supported evidence"]),
        ],
        [
            AdaptiveEvidenceAssessment(
                sufficient=False,
                reasons=["low_query_term_coverage"],
            ),
            AdaptiveEvidenceAssessment(sufficient=True),
        ],
    )

    assert received_queries == [
        "How does thermal runaway propagate?",
        "How does thermal runaway propagate? NASA aerospace technical report",
    ]
    assert [hit_set.name for hit_set in outcome.hit_sets] == ["initial", "recovery"]
    assert outcome.evidence == ["supported evidence"]
    assert outcome.trace.retrieval_terminal_state == "generate"
    assert outcome.trace.states == [
        AdaptiveRetrievalState.RETRIEVE_INITIAL,
        AdaptiveRetrievalState.ASSESS_INITIAL,
        AdaptiveRetrievalState.REWRITE_QUERY,
        AdaptiveRetrievalState.RETRIEVE_RECOVERY,
        AdaptiveRetrievalState.ASSESS_RECOVERY,
        AdaptiveRetrievalState.GENERATE,
    ]
    assert len(outcome.trace.attempts) == 2
    assert outcome.trace.attempts[0].evidence_provenance[0].chunk_id == "chunk-1"
    assert outcome.trace.attempts[1].evidence_provenance[0].chunk_id == "chunk-2"


def test_insufficient_second_pass_terminates_in_a_grounded_refusal() -> None:
    controller = BoundedAdaptiveRetrievalController[FakeHitSet, str](make_config())
    outcome, received_queries = execute(
        controller,
        [
            FakeHitSet(name="initial", evidence=["weak evidence"]),
            FakeHitSet(name="recovery", evidence=["still weak evidence"]),
        ],
        [
            AdaptiveEvidenceAssessment(
                sufficient=False,
                reasons=["low_query_term_coverage"],
            ),
            AdaptiveEvidenceAssessment(
                sufficient=False,
                reasons=["missing_named_anchor_support"],
            ),
        ],
    )

    assert len(received_queries) == 2
    assert outcome.trace.retrieval_terminal_state == "grounded_refusal"
    assert outcome.trace.states[-1] == AdaptiveRetrievalState.GROUNDED_REFUSAL
    assert outcome.assessment.reasons == ["missing_named_anchor_support"]


def test_single_pass_policy_refuses_without_rewrite() -> None:
    controller = BoundedAdaptiveRetrievalController[FakeHitSet, str](
        make_config(
            maximum_retrieval_passes=1,
            maximum_query_rewrites=0,
        )
    )
    outcome, received_queries = execute(
        controller,
        [FakeHitSet(name="initial", evidence=["weak evidence"])],
        [
            AdaptiveEvidenceAssessment(
                sufficient=False,
                reasons=["low_query_term_coverage"],
            )
        ],
    )

    assert len(received_queries) == 1
    assert outcome.trace.rewritten_query is None
    assert outcome.trace.retrieval_terminal_state == "grounded_refusal"


def test_rewriter_preserves_the_original_question() -> None:
    rewriter = DeterministicQueryRewriter(make_config())

    rewritten = rewriter.rewrite(
        original_query="What does NASA report about battery cooling?",
        assessment=AdaptiveEvidenceAssessment(sufficient=False),
    )

    assert rewritten == (
        "What does NASA report about battery cooling? NASA aerospace technical report"
    )
