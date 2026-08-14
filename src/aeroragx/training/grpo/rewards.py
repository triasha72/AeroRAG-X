"""Deterministic multi-objective rewards for grounded agent behavior."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.training.grpo.config import RewardWeights


class GroundedRewardInput(BaseModel):
    """Observable behavior required to calculate reward."""

    model_config = ConfigDict(extra="forbid")

    answerable: bool
    answered: bool
    refused: bool
    answer_correct: bool
    citation_valid: bool
    evidence_supported: bool
    structured_output_valid: bool
    required_tool_selected: bool
    tool_call_count: int = Field(ge=0)
    necessary_tool_calls: int = Field(ge=0)


class RewardBreakdown(BaseModel):
    """Transparent reward components and final scalar."""

    model_config = ConfigDict(extra="forbid")

    supported_answer: float
    refusal_correctness: float
    citation_validity: float
    evidence_support: float
    structured_output: float
    tool_selection: float
    unnecessary_tool_penalty: float
    total: float


def score_grounded_rollout(
    item: GroundedRewardInput,
    *,
    weights: RewardWeights,
) -> RewardBreakdown:
    """Calculate a bounded engineering reward from externally observable outcomes."""

    supported_answer = (
        weights.supported_answer
        if item.answerable and item.answered and item.answer_correct and item.evidence_supported
        else 0.0
    )
    refusal_correctness = (
        weights.refusal_correctness if (not item.answerable and item.refused) else 0.0
    )
    citation_validity = weights.citation_validity if item.answered and item.citation_valid else 0.0
    evidence_support = (
        weights.evidence_support if item.answered and item.evidence_supported else 0.0
    )
    structured_output = weights.structured_output if item.structured_output_valid else 0.0
    tool_selection = weights.tool_selection if item.required_tool_selected else 0.0

    unnecessary_calls = max(
        item.tool_call_count - item.necessary_tool_calls,
        0,
    )
    unnecessary_tool_penalty = weights.unnecessary_tool_penalty * unnecessary_calls

    total = (
        supported_answer
        + refusal_correctness
        + citation_validity
        + evidence_support
        + structured_output
        + tool_selection
        - unnecessary_tool_penalty
    )

    # Strong anti-hacking gate: unsupported asserted answers cannot receive a
    # positive total merely through formatting/tool behavior.
    if not item.answerable and item.answered and not item.refused:
        total = min(total, 0.0)

    # Fake/invalid citations cap an otherwise correct-looking answer.
    if item.answered and not item.citation_valid:
        total = min(total, weights.structured_output)

    return RewardBreakdown(
        supported_answer=supported_answer,
        refusal_correctness=refusal_correctness,
        citation_validity=citation_validity,
        evidence_support=evidence_support,
        structured_output=structured_output,
        tool_selection=tool_selection,
        unnecessary_tool_penalty=unnecessary_tool_penalty,
        total=total,
    )
