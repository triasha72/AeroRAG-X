"""Deterministic, bounded recovery after an insufficient retrieval pass."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.generation.sufficiency import EvidenceSufficiencyResult


class AdaptiveRetrievalState(StrEnum):
    """The only valid states in a bounded adaptive-retrieval request."""

    RETRIEVE_INITIAL = "retrieve_initial"
    ASSESS_INITIAL = "assess_initial"
    REWRITE_QUERY = "rewrite_query"
    RETRIEVE_RECOVERY = "retrieve_recovery"
    ASSESS_RECOVERY = "assess_recovery"
    GENERATE = "generate"
    GROUNDED_REFUSAL = "grounded_refusal"


class AdaptiveRetrievalConfig(BaseModel):
    """Validated limits and deterministic rewrite settings."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(default="0.1", min_length=1)
    maximum_retrieval_passes: int = Field(default=2, ge=1, le=2)
    maximum_query_rewrites: int = Field(default=1, ge=0, le=1)
    recovery_trigger: Literal["insufficient_evidence"] = "insufficient_evidence"
    rewrite_strategy: Literal["append_domain_context"] = "append_domain_context"
    rewrite_context_terms: list[str] = Field(
        default_factory=lambda: ["NASA", "aerospace", "technical", "report"],
        min_length=1,
        max_length=8,
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        """Ensure the configured policy has one deterministic terminal path."""

        if self.maximum_query_rewrites != self.maximum_retrieval_passes - 1:
            raise ValueError("maximum_query_rewrites must equal maximum_retrieval_passes - 1.")

        normalized_terms = [term.casefold() for term in self.rewrite_context_terms]

        if any(not term for term in normalized_terms):
            raise ValueError("rewrite_context_terms must not contain blank values.")

        if len(normalized_terms) != len(set(normalized_terms)):
            raise ValueError("rewrite_context_terms must not contain duplicates.")

        return self


class AdaptiveEvidenceProvenance(BaseModel):
    """Provenance retained for one chunk returned by one retrieval attempt."""

    model_config = ConfigDict(extra="forbid")

    attempt_number: int = Field(ge=1, le=2)
    reranker_rank: int = Field(ge=1)
    chunk_id: str = Field(min_length=1)
    document_id: int
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    citation_url: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)
    reranker_score: float
    hybrid_rank: int = Field(ge=1)
    hybrid_score: float = Field(gt=0.0)
    retrieved_by: list[Literal["bm25", "dense"]] = Field(min_length=1)
    bm25_rank: int | None = Field(default=None, ge=1)
    bm25_score: float | None = Field(default=None, ge=0.0)
    dense_rank: int | None = Field(default=None, ge=1)
    dense_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        """Reject malformed or internally inconsistent source provenance."""

        if self.page_end < self.page_start:
            raise ValueError("page_end must not be smaller than page_start.")

        if len(self.retrieved_by) != len(set(self.retrieved_by)):
            raise ValueError("retrieved_by must not contain duplicates.")

        bm25_present = self.bm25_rank is not None or self.bm25_score is not None
        dense_present = self.dense_rank is not None or self.dense_score is not None

        if (self.bm25_rank is None) != (self.bm25_score is None):
            raise ValueError(
                "bm25_rank and bm25_score must either both be present or both be absent."
            )

        if (self.dense_rank is None) != (self.dense_score is None):
            raise ValueError(
                "dense_rank and dense_score must either both be present or both be absent."
            )

        sources = set(self.retrieved_by)

        if ("bm25" in sources) != bm25_present:
            raise ValueError("BM25 provenance does not match retrieved_by.")

        if ("dense" in sources) != dense_present:
            raise ValueError("Dense provenance does not match retrieved_by.")

        return self


class AdaptiveEvidenceAssessment(BaseModel):
    """Normalized evidence assessment used by the recovery controller."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    sufficient: bool
    reasons: list[str] = Field(default_factory=list)
    evidence_sufficiency: EvidenceSufficiencyResult | None = None

    @model_validator(mode="after")
    def validate_reasons(self) -> Self:
        """Ensure the trace contains concise, deterministic failure labels."""

        if any(not reason for reason in self.reasons):
            raise ValueError("reasons must not contain blank values.")

        if len(self.reasons) != len(set(self.reasons)):
            raise ValueError("reasons must not contain duplicates.")

        if self.evidence_sufficiency is not None:
            if self.sufficient != self.evidence_sufficiency.sufficient:
                raise ValueError(
                    "sufficient must match evidence_sufficiency.sufficient when supplied."
                )

            if self.reasons != self.evidence_sufficiency.reasons:
                raise ValueError("reasons must match evidence_sufficiency.reasons when supplied.")

        return self


class AdaptiveRetrievalAttempt(BaseModel):
    """Auditable result of one bounded retrieval attempt."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    attempt_number: int = Field(ge=1, le=2)
    retrieval_query: str = Field(min_length=1)
    returned_evidence_count: int = Field(ge=0)
    used_evidence_count: int = Field(ge=0)
    assessment: AdaptiveEvidenceAssessment
    evidence_provenance: list[AdaptiveEvidenceProvenance] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attempt(self) -> Self:
        """Ensure an attempt trace accounts for every retrieved chunk."""

        if self.used_evidence_count > self.returned_evidence_count:
            raise ValueError("used_evidence_count must not exceed returned_evidence_count.")

        if self.returned_evidence_count != len(self.evidence_provenance):
            raise ValueError(
                "returned_evidence_count must match the retained provenance record count."
            )

        if any(
            provenance.attempt_number != self.attempt_number
            for provenance in self.evidence_provenance
        ):
            raise ValueError("Evidence provenance must match its enclosing attempt number.")

        return self


class AdaptiveRetrievalTrace(BaseModel):
    """Validated trace showing a request followed the bounded state machine."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    mode: Literal["bounded_adaptive"] = "bounded_adaptive"
    original_query: str = Field(min_length=1)
    rewritten_query: str | None = None
    states: list[AdaptiveRetrievalState] = Field(min_length=3, max_length=6)
    attempts: list[AdaptiveRetrievalAttempt] = Field(min_length=1, max_length=2)
    retrieval_terminal_state: Literal["generate", "grounded_refusal"]

    @model_validator(mode="after")
    def validate_state_machine(self) -> Self:
        """Reject traces that diverge from the fixed two-pass transition graph."""

        attempt_numbers = [attempt.attempt_number for attempt in self.attempts]

        if attempt_numbers != list(range(1, len(self.attempts) + 1)):
            raise ValueError("attempt numbers must start at one and be consecutive.")

        terminal_state = (
            AdaptiveRetrievalState.GENERATE
            if self.retrieval_terminal_state == "generate"
            else AdaptiveRetrievalState.GROUNDED_REFUSAL
        )

        if len(self.attempts) == 1:
            first_attempt = self.attempts[0]
            expected_states = [
                AdaptiveRetrievalState.RETRIEVE_INITIAL,
                AdaptiveRetrievalState.ASSESS_INITIAL,
                terminal_state,
            ]

            if self.states != expected_states:
                raise ValueError("Single-pass trace contains an invalid state transition.")

            if self.rewritten_query is not None:
                raise ValueError("Single-pass trace must not include a rewritten query.")

            if first_attempt.assessment.sufficient != (self.retrieval_terminal_state == "generate"):
                raise ValueError("Single-pass terminal state does not match the assessment.")

            return self

        first_attempt, second_attempt = self.attempts
        expected_states = [
            AdaptiveRetrievalState.RETRIEVE_INITIAL,
            AdaptiveRetrievalState.ASSESS_INITIAL,
            AdaptiveRetrievalState.REWRITE_QUERY,
            AdaptiveRetrievalState.RETRIEVE_RECOVERY,
            AdaptiveRetrievalState.ASSESS_RECOVERY,
            terminal_state,
        ]

        if self.states != expected_states:
            raise ValueError("Two-pass trace contains an invalid state transition.")

        if first_attempt.assessment.sufficient:
            raise ValueError("A sufficient first attempt must not trigger recovery retrieval.")

        if self.rewritten_query is None:
            raise ValueError("Two-pass trace must retain the rewritten retrieval query.")

        if second_attempt.retrieval_query != self.rewritten_query:
            raise ValueError("Recovery attempt query must equal rewritten_query.")

        if second_attempt.assessment.sufficient != (self.retrieval_terminal_state == "generate"):
            raise ValueError("Recovery terminal state does not match the assessment.")

        return self


class QueryRewriter(Protocol):
    """Minimal deterministic rewrite interface required by the controller."""

    def rewrite(
        self,
        *,
        original_query: str,
        assessment: AdaptiveEvidenceAssessment,
    ) -> str:
        """Return one non-empty recovery retrieval query."""

        ...


class DeterministicQueryRewriter:
    """Preserve the question and append fixed domain-retrieval context."""

    def __init__(
        self,
        config: AdaptiveRetrievalConfig,
    ) -> None:
        self._config = config

    def rewrite(
        self,
        *,
        original_query: str,
        assessment: AdaptiveEvidenceAssessment,
    ) -> str:
        """Create a reproducible retrieval-only rewrite without an LLM call."""

        del assessment

        normalized_query = original_query.strip()

        if not normalized_query:
            raise ValueError("original_query must not be blank.")

        suffix = " ".join(self._config.rewrite_context_terms)
        rewritten_query = f"{normalized_query} {suffix}".strip()

        if rewritten_query.casefold() == normalized_query.casefold():
            raise ValueError("Deterministic recovery rewrite must change the retrieval query.")

        return rewritten_query


@dataclass(frozen=True, slots=True)
class BoundedRetrievalOutcome[HitT, EvidenceT]:
    """Final evidence selected by the controller plus its auditable trace."""

    hit_sets: list[HitT]
    evidence: list[EvidenceT]
    assessment: AdaptiveEvidenceAssessment
    trace: AdaptiveRetrievalTrace


class BoundedAdaptiveRetrievalController[HitT, EvidenceT]:
    """Execute one deterministic recovery path and then terminate."""

    def __init__(
        self,
        config: AdaptiveRetrievalConfig,
        *,
        rewriter: QueryRewriter | None = None,
    ) -> None:
        self._config = config
        self._rewriter = DeterministicQueryRewriter(config) if rewriter is None else rewriter

    @property
    def config(self) -> AdaptiveRetrievalConfig:
        """Return the validated bounded-retrieval configuration."""

        return self._config

    def execute(
        self,
        *,
        original_query: str,
        retrieve: Callable[[str], HitT],
        build_evidence: Callable[[HitT], Sequence[EvidenceT]],
        assess_evidence: Callable[[Sequence[EvidenceT]], AdaptiveEvidenceAssessment],
        build_provenance: Callable[[HitT, int], Sequence[AdaptiveEvidenceProvenance]],
        returned_evidence_count: Callable[[HitT], int],
    ) -> BoundedRetrievalOutcome[HitT, EvidenceT]:
        """Run at most two retrieval passes and return the terminal evidence state."""

        normalized_query = original_query.strip()

        if not normalized_query:
            raise ValueError("original_query must not be blank.")

        first_hit_set = retrieve(normalized_query)
        first_evidence = list(build_evidence(first_hit_set))
        first_assessment = assess_evidence(first_evidence)
        first_attempt = self._build_attempt(
            attempt_number=1,
            retrieval_query=normalized_query,
            returned_evidence_count=returned_evidence_count(first_hit_set),
            evidence=first_evidence,
            assessment=first_assessment,
            provenance=build_provenance(first_hit_set, 1),
        )

        if first_assessment.sufficient:
            return BoundedRetrievalOutcome(
                hit_sets=[first_hit_set],
                evidence=first_evidence,
                assessment=first_assessment,
                trace=self._build_trace(
                    original_query=normalized_query,
                    rewritten_query=None,
                    attempts=[first_attempt],
                    retrieval_terminal_state="generate",
                ),
            )

        if self._config.maximum_retrieval_passes == 1:
            return BoundedRetrievalOutcome(
                hit_sets=[first_hit_set],
                evidence=first_evidence,
                assessment=first_assessment,
                trace=self._build_trace(
                    original_query=normalized_query,
                    rewritten_query=None,
                    attempts=[first_attempt],
                    retrieval_terminal_state="grounded_refusal",
                ),
            )

        rewritten_query = self._rewriter.rewrite(
            original_query=normalized_query,
            assessment=first_assessment,
        ).strip()

        if not rewritten_query:
            raise ValueError("Deterministic recovery rewrite must not be blank.")

        if rewritten_query.casefold() == normalized_query.casefold():
            raise ValueError("Deterministic recovery rewrite must change the retrieval query.")

        second_hit_set = retrieve(rewritten_query)
        second_evidence = list(build_evidence(second_hit_set))
        second_assessment = assess_evidence(second_evidence)
        second_attempt = self._build_attempt(
            attempt_number=2,
            retrieval_query=rewritten_query,
            returned_evidence_count=returned_evidence_count(second_hit_set),
            evidence=second_evidence,
            assessment=second_assessment,
            provenance=build_provenance(second_hit_set, 2),
        )

        retrieval_terminal_state: Literal["generate", "grounded_refusal"] = (
            "generate" if second_assessment.sufficient else "grounded_refusal"
        )

        return BoundedRetrievalOutcome(
            hit_sets=[first_hit_set, second_hit_set],
            evidence=second_evidence,
            assessment=second_assessment,
            trace=self._build_trace(
                original_query=normalized_query,
                rewritten_query=rewritten_query,
                attempts=[first_attempt, second_attempt],
                retrieval_terminal_state=retrieval_terminal_state,
            ),
        )

    @staticmethod
    def _build_attempt(
        *,
        attempt_number: int,
        retrieval_query: str,
        returned_evidence_count: int,
        evidence: Sequence[EvidenceT],
        assessment: AdaptiveEvidenceAssessment,
        provenance: Sequence[AdaptiveEvidenceProvenance],
    ) -> AdaptiveRetrievalAttempt:
        """Create one validated attempt record."""

        return AdaptiveRetrievalAttempt(
            attempt_number=attempt_number,
            retrieval_query=retrieval_query,
            returned_evidence_count=returned_evidence_count,
            used_evidence_count=len(evidence),
            assessment=assessment,
            evidence_provenance=list(provenance),
        )

    @staticmethod
    def _build_trace(
        *,
        original_query: str,
        rewritten_query: str | None,
        attempts: list[AdaptiveRetrievalAttempt],
        retrieval_terminal_state: Literal["generate", "grounded_refusal"],
    ) -> AdaptiveRetrievalTrace:
        """Create a trace whose exact transition sequence is model-validated."""

        terminal_state = (
            AdaptiveRetrievalState.GENERATE
            if retrieval_terminal_state == "generate"
            else AdaptiveRetrievalState.GROUNDED_REFUSAL
        )

        if len(attempts) == 1:
            states = [
                AdaptiveRetrievalState.RETRIEVE_INITIAL,
                AdaptiveRetrievalState.ASSESS_INITIAL,
                terminal_state,
            ]
        else:
            states = [
                AdaptiveRetrievalState.RETRIEVE_INITIAL,
                AdaptiveRetrievalState.ASSESS_INITIAL,
                AdaptiveRetrievalState.REWRITE_QUERY,
                AdaptiveRetrievalState.RETRIEVE_RECOVERY,
                AdaptiveRetrievalState.ASSESS_RECOVERY,
                terminal_state,
            ]

        return AdaptiveRetrievalTrace(
            original_query=original_query,
            rewritten_query=rewritten_query,
            states=states,
            attempts=attempts,
            retrieval_terminal_state=retrieval_terminal_state,
        )


def load_adaptive_retrieval_config(
    path: Path,
) -> AdaptiveRetrievalConfig:
    """Load and validate a bounded adaptive-retrieval YAML configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Adaptive-retrieval configuration must contain a YAML mapping.")

    return AdaptiveRetrievalConfig.model_validate(raw_data)
