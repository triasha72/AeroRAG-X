"""Stateful TRL environment for bounded grounded tool-use rollouts."""

from __future__ import annotations

from collections.abc import Sequence

from aeroragx.training.grpo.config import RewardWeights
from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase
from aeroragx.training.grpo.rewards import (
    GroundedRewardInput,
    score_grounded_rollout,
)


class GroundedAgentEnvironment:
    """Self-sampling environment exposing bounded evidence tools to GRPO."""

    def __init__(
        self,
        *,
        cases: Sequence[GroundedAgentTrainingCase],
        reward_weights: RewardWeights,
    ) -> None:
        if not cases:
            raise ValueError("GroundedAgentEnvironment requires training cases.")
        self._cases = list(cases)
        self._weights = reward_weights
        self._cursor = -1
        self._case = self._cases[0]
        self._retrieved = False
        self._sufficiency_checked = False
        self._submitted_answer: str | None = None
        self._submitted_citations: list[str] = []
        self._refused = False
        self._tool_calls = 0

    def reset(self, **kwargs: object) -> str:
        """Reset one rollout and return the next user prompt."""

        del kwargs
        self._cursor = (self._cursor + 1) % len(self._cases)
        self._case = self._cases[self._cursor]
        self._retrieved = False
        self._sufficiency_checked = False
        self._submitted_answer = None
        self._submitted_citations = []
        self._refused = False
        self._tool_calls = 0
        return self._case.query

    def retrieve(self) -> list[dict[str, object]]:
        """Return the frozen evidence records for the active training case.

        Returns:
            A list of provenance-preserving evidence mappings.
        """

        self._tool_calls += 1
        self._retrieved = True
        return [item.model_dump(mode="json") for item in self._case.evidence]

    def check_sufficiency(self) -> bool:
        """Return whether the frozen case contains enough support to answer.

        Returns:
            True when the active training case is labeled answerable.
        """

        self._tool_calls += 1
        self._sufficiency_checked = True
        return self._case.answerable and bool(self._case.evidence)

    def submit_answer(
        self,
        answer: str,
        cited_evidence_ids: list[str],
    ) -> str:
        """Submit the final grounded answer and citations.

        Args:
            answer: Candidate final answer.
            cited_evidence_ids: Evidence identifiers used to support the answer.

        Returns:
            A stable acknowledgement string.
        """

        self._tool_calls += 1
        self._submitted_answer = answer.strip()
        self._submitted_citations = list(cited_evidence_ids)
        self._refused = False
        return "submitted"

    def refuse(self) -> str:
        """Terminate the rollout with a grounded refusal.

        Returns:
            A stable acknowledgement string.
        """

        self._tool_calls += 1
        self._submitted_answer = None
        self._submitted_citations = []
        self._refused = True
        return "refused"

    def get_reward(self) -> float:
        """Calculate deterministic reward from observable environment state."""

        expected_ids = set(self._case.expected_citation_ids)
        cited_ids = set(self._submitted_citations)

        answered = bool(self._submitted_answer)
        answer_correct = (
            answered
            and self._case.reference_answer is not None
            and self._submitted_answer is not None
            and self._case.reference_answer.casefold()
            in self._submitted_answer.casefold()
        )
        citation_valid = cited_ids.issubset(
            {item.evidence_id for item in self._case.evidence}
        ) and (
            not expected_ids or expected_ids.issubset(cited_ids)
        )
        evidence_supported = (
            answered
            and self._retrieved
            and citation_valid
            and bool(self._case.evidence)
        )
        necessary_tool_calls = (
            1 if not self._case.answerable else 3
        )

        score = score_grounded_rollout(
            GroundedRewardInput(
                answerable=self._case.answerable,
                answered=answered,
                refused=self._refused,
                answer_correct=bool(answer_correct),
                citation_valid=citation_valid,
                evidence_supported=bool(evidence_supported),
                structured_output_valid=answered or self._refused,
                required_tool_selected=(
                    self._retrieved
                    and (
                        self._sufficiency_checked
                        or not self._case.answerable
                    )
                ),
                tool_call_count=self._tool_calls,
                necessary_tool_calls=necessary_tool_calls,
            ),
            weights=self._weights,
        )
        return score.total
