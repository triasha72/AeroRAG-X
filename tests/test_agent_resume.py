"""Tests for Phase 38 resume semantics."""

from aeroragx.agent.human_review import HumanReviewResponse
from aeroragx.agent.resume import apply_human_review
from aeroragx.agent.state import AgentState


def paused_state() -> AgentState:
    return AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
        human_review_required=True,
        termination_reason="human_review_required",
    )


def test_approve_resumes_without_overwriting_original_state() -> None:
    original = paused_state()
    resumed = apply_human_review(
        original,
        HumanReviewResponse(
            review_id="review-1",
            decision="approve",
            rationale="Evidence conflict resolved.",
        ),
    )

    assert original.termination_reason == "human_review_required"
    assert resumed.termination_reason is None
    assert resumed.human_review_required is False


def test_reject_converts_pause_to_grounded_refusal() -> None:
    terminal = apply_human_review(
        paused_state(),
        HumanReviewResponse(
            review_id="review-1",
            decision="reject",
            rationale="Evidence is not adequate.",
        ),
    )
    assert terminal.termination_reason == "grounded_refusal"
