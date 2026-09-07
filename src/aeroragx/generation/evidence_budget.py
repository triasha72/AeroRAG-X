"""Deterministic evidence-budget selection before grounded generation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.generation.sufficiency import EvidenceSufficiencyAssessor
from aeroragx.retrieval.reranker import RerankedSearchHit


class EvidenceBudgetConfig(BaseModel):
    """Bounds and reasons for expanding the final evidence set."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"
    initial_top_k: int = Field(default=3, ge=1, le=100)
    maximum_top_k: int = Field(default=5, ge=1, le=100)
    expandable_reasons: list[str] = Field(
        default_factory=lambda: [
            "insufficient_evidence_count",
            "insufficient_supported_terms",
            "low_query_term_coverage",
            "low_single_evidence_coverage",
        ]
    )
    blocking_reasons: list[str] = Field(
        default_factory=lambda: [
            "no_informative_query_terms",
            "missing_numeric_support",
            "missing_named_anchor_support",
            "missing_claim_qualifier_support",
            "missing_scope_qualifier_support",
        ]
    )

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if self.initial_top_k >= self.maximum_top_k:
            raise ValueError("initial_top_k must be smaller than maximum_top_k.")
        if len(self.expandable_reasons) != len(set(self.expandable_reasons)):
            raise ValueError("expandable_reasons must not contain duplicates.")
        if len(self.blocking_reasons) != len(set(self.blocking_reasons)):
            raise ValueError("blocking_reasons must not contain duplicates.")
        overlap = set(self.expandable_reasons) & set(self.blocking_reasons)
        if overlap:
            raise ValueError(f"Expansion and blocking reasons overlap: {sorted(overlap)}")
        return self


class EvidenceBudgetDecision(BaseModel):
    """Auditable selection made without inspecting generated output."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    requested_top_k: int = Field(ge=1)
    available_hit_count: int = Field(ge=0)
    initial_top_k: int = Field(ge=1)
    selected_top_k: int = Field(ge=0)
    expanded: bool
    initial_sufficient: bool
    initial_reasons: list[str]
    maximum_sufficient: bool
    maximum_reasons: list[str]
    expansion_reason: str


class EvidenceSearchIndex(Protocol):
    def search(self, query: str, top_k: int = 10) -> Sequence[RerankedSearchHit]: ...


class AdaptiveEvidenceBudgetIndex:
    """Select three or five hits using only the frozen sufficiency assessor."""

    def __init__(
        self,
        index: EvidenceSearchIndex,
        assessor: EvidenceSufficiencyAssessor,
        config: EvidenceBudgetConfig,
    ) -> None:
        self._index = index
        self._assessor = assessor
        self._config = config
        self._decisions: list[EvidenceBudgetDecision] = []

    @property
    def decisions(self) -> list[EvidenceBudgetDecision]:
        return [decision.model_copy(deep=True) for decision in self._decisions]

    def search(self, query: str, top_k: int = 10) -> Sequence[RerankedSearchHit]:
        if top_k != self._config.maximum_top_k:
            raise ValueError(
                "Adaptive evidence budget requires requested top_k to equal maximum_top_k."
            )
        hits = list(self._index.search(query=query, top_k=self._config.maximum_top_k))
        initial = hits[: self._config.initial_top_k]
        assessment = self._assessor.assess(query=query, evidence=[hit.chunk for hit in initial])
        reasons = set(assessment.reasons)
        if set(assessment.required_numeric_terms) != set(assessment.supported_numeric_terms):
            reasons.add("missing_numeric_support")
        if set(assessment.required_named_anchors) != set(assessment.supported_named_anchors):
            reasons.add("missing_named_anchor_support")
        if set(assessment.required_claim_qualifiers) != set(assessment.supported_claim_qualifiers):
            reasons.add("missing_claim_qualifier_support")
        if set(assessment.required_scope_qualifiers) != set(assessment.supported_scope_qualifiers):
            reasons.add("missing_scope_qualifier_support")
        maximum_assessment = self._assessor.assess(
            query=query,
            evidence=[hit.chunk for hit in hits],
        )
        maximum_reasons = set(maximum_assessment.reasons)
        has_expandable_gap = bool(reasons & set(self._config.expandable_reasons))
        has_blocker = bool(reasons & set(self._config.blocking_reasons))
        expanded = (
            not assessment.sufficient
            and maximum_assessment.sufficient
            and has_expandable_gap
            and not has_blocker
        )
        selected = hits if expanded else initial
        if has_blocker:
            expansion_reason = "blocked_by_unsupported_signal"
        elif assessment.sufficient:
            expansion_reason = "initial_evidence_sufficient"
        elif expanded:
            expansion_reason = "recoverable_coverage_gap"
        elif not maximum_assessment.sufficient:
            expansion_reason = "maximum_evidence_still_insufficient"
        else:
            expansion_reason = "no_expandable_reason"
        self._decisions.append(
            EvidenceBudgetDecision(
                query=query,
                requested_top_k=top_k,
                available_hit_count=len(hits),
                initial_top_k=len(initial),
                selected_top_k=len(selected),
                expanded=expanded,
                initial_sufficient=assessment.sufficient,
                initial_reasons=sorted(reasons),
                maximum_sufficient=maximum_assessment.sufficient,
                maximum_reasons=sorted(maximum_reasons),
                expansion_reason=expansion_reason,
            )
        )
        return selected

    def __getattr__(self, name: str) -> Any:
        return getattr(self._index, name)


def load_evidence_budget_config(path: Path) -> EvidenceBudgetConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Evidence-budget configuration must contain a YAML mapping.")
    return EvidenceBudgetConfig.model_validate(raw)
