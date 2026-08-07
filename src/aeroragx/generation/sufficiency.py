"""Deterministic evidence-sufficiency assessment."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
_SIMPLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "aboard",
    "as",
    "at",
    "be",
    "been",
    "being",
    "between",
    "by",
    "can",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "technically",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}

_TOKEN_ALIASES = {
    "batteries": "battery",
    "cells": "cell",
    "cooled": "cool",
    "cooling": "cool",
    "detected": "detect",
    "detecting": "detect",
    "detection": "detect",
    "fires": "fire",
    "challenging": "challenge",
    "issued": "issue",
    "mandated": "mandate",
    "assigned": "assign",
    "stored": "storage",
    "stores": "storage",
    "storing": "storage",
    "propagated": "propagate",
    "propagates": "propagate",
    "propagation": "propagate",
}

_CLAIM_QUALIFIER_ALIASES = {
    "assign": "assign",
    "assigned": "assign",
    "assigns": "assign",
    "certified": "certify",
    "certifies": "certify",
    "certify": "certify",
    "every": "every",
    "issued": "issue",
    "legal": "legal",
    "legally": "legal",
    "mandate": "mandate",
    "mandated": "mandate",
    "mandates": "mandate",
    "official": "official",
    "officially": "official",
    "require": "require",
    "required": "require",
    "requires": "require",
    "universal": "universal",
    "universally": "universal",
    "worldwide": "worldwide",
}


class SufficiencyEvidence(Protocol):
    """Minimal evidence interface required by the sufficiency assessor."""

    @property
    def text(self) -> str:
        """Return evidence text."""

        ...


class SufficiencyConfig(BaseModel):
    """Configuration for deterministic evidence-sufficiency checks."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    minimum_evidence_count: int = Field(default=1, ge=1, le=100)
    minimum_supported_terms: int = Field(default=2, ge=1, le=100)

    minimum_query_term_coverage: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
    )
    minimum_single_evidence_coverage: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
    )
    exact_query_minimum_coverage: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )

    require_all_numeric_terms: bool = True
    require_named_anchors: bool = True
    require_claim_qualifiers: bool = False

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        """Ensure stricter exact-query coverage is internally consistent."""

        if self.exact_query_minimum_coverage < self.minimum_query_term_coverage:
            raise ValueError(
                "exact_query_minimum_coverage must be greater than "
                "or equal to minimum_query_term_coverage."
            )

        return self


class EvidenceSufficiencyResult(BaseModel):
    """Auditable result returned by the evidence-sufficiency assessor."""

    model_config = ConfigDict(extra="forbid")

    sufficient: bool
    evidence_count: int = Field(ge=0)

    query_terms: list[str]
    supported_terms: list[str]
    unsupported_terms: list[str]
    query_term_coverage: float = Field(ge=0.0, le=1.0)
    single_evidence_coverage: float = Field(ge=0.0, le=1.0)

    required_numeric_terms: list[str]
    supported_numeric_terms: list[str]

    required_named_anchors: list[str]
    supported_named_anchors: list[str]

    required_claim_qualifiers: list[str] = Field(default_factory=list)
    supported_claim_qualifiers: list[str] = Field(default_factory=list)

    reasons: list[str]


class EvidenceSufficiencyAssessor:
    """Assess whether retrieved text plausibly supports a query."""

    def __init__(
        self,
        config: SufficiencyConfig,
    ) -> None:
        self._config = config

    @property
    def config(self) -> SufficiencyConfig:
        """Return the validated sufficiency configuration."""

        return self._config

    def assess(
        self,
        *,
        query: str,
        evidence: Sequence[SufficiencyEvidence],
    ) -> EvidenceSufficiencyResult:
        """Return an auditable deterministic sufficiency decision."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query must not be blank.")

        query_terms = _informative_query_terms(normalized_query)
        evidence_token_sets = [
            set(_normalized_tokens(item.text)) for item in evidence if item.text.strip()
        ]
        combined_evidence_terms = (
            set().union(*evidence_token_sets) if evidence_token_sets else set()
        )

        supported_terms = [term for term in query_terms if term in combined_evidence_terms]
        unsupported_terms = [term for term in query_terms if term not in combined_evidence_terms]

        query_term_coverage = _safe_ratio(
            len(supported_terms),
            len(query_terms),
        )

        single_evidence_coverage = max(
            (
                _safe_ratio(
                    sum(term in evidence_terms for term in query_terms),
                    len(query_terms),
                )
                for evidence_terms in evidence_token_sets
            ),
            default=0.0,
        )

        required_numeric_terms = _numeric_terms(normalized_query)
        supported_numeric_terms = [
            term for term in required_numeric_terms if term in combined_evidence_terms
        ]

        required_named_anchors = _named_anchors(normalized_query)
        supported_named_anchors = [
            term for term in required_named_anchors if term in combined_evidence_terms
        ]

        required_claim_qualifiers = _claim_qualifiers(normalized_query)
        supported_claim_qualifiers = [
            term for term in required_claim_qualifiers if term in combined_evidence_terms
        ]

        required_coverage = (
            self._config.exact_query_minimum_coverage
            if "exact" in query_terms
            else self._config.minimum_query_term_coverage
        )

        reasons: list[str] = []

        if len(evidence_token_sets) < self._config.minimum_evidence_count:
            reasons.append("insufficient_evidence_count")

        if not query_terms:
            reasons.append("no_informative_query_terms")

        if len(supported_terms) < self._config.minimum_supported_terms:
            reasons.append("insufficient_supported_terms")

        if query_term_coverage < required_coverage:
            reasons.append("low_query_term_coverage")

        if single_evidence_coverage < self._config.minimum_single_evidence_coverage:
            reasons.append("low_single_evidence_coverage")

        if self._config.require_all_numeric_terms and set(required_numeric_terms) != set(
            supported_numeric_terms
        ):
            reasons.append("missing_numeric_support")

        if self._config.require_named_anchors and set(required_named_anchors) != set(
            supported_named_anchors
        ):
            reasons.append("missing_named_anchor_support")

        if self._config.require_claim_qualifiers and set(required_claim_qualifiers) != set(
            supported_claim_qualifiers
        ):
            reasons.append("missing_claim_qualifier_support")

        return EvidenceSufficiencyResult(
            sufficient=not reasons,
            evidence_count=len(evidence_token_sets),
            query_terms=query_terms,
            supported_terms=supported_terms,
            unsupported_terms=unsupported_terms,
            query_term_coverage=query_term_coverage,
            single_evidence_coverage=single_evidence_coverage,
            required_numeric_terms=required_numeric_terms,
            supported_numeric_terms=supported_numeric_terms,
            required_named_anchors=required_named_anchors,
            supported_named_anchors=supported_named_anchors,
            required_claim_qualifiers=(required_claim_qualifiers),
            supported_claim_qualifiers=(supported_claim_qualifiers),
            reasons=reasons,
        )


def load_sufficiency_config(
    path: Path,
) -> SufficiencyConfig:
    """Load and validate a YAML sufficiency configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Sufficiency configuration must contain a YAML mapping.")

    return SufficiencyConfig.model_validate(raw_data)


def _informative_query_terms(
    query: str,
) -> list[str]:
    """Return normalized, unique, non-stopword query terms."""

    terms: list[str] = []

    for token in _normalized_tokens(query):
        if token in _STOP_WORDS:
            continue

        if token.isalpha() and len(token) == 1:
            continue

        if token not in terms:
            terms.append(token)

    return terms


def _normalized_tokens(
    value: str,
) -> list[str]:
    """Tokenize and normalize text deterministically."""

    return [
        _normalize_token(token)
        for token in _SIMPLE_TOKEN_RE.findall(value.casefold())
        if _normalize_token(token)
    ]


def _normalize_token(
    token: str,
) -> str:
    """Normalize common aerospace-query morphology."""

    normalized = token.casefold().strip()

    if not normalized:
        return ""

    alias = _TOKEN_ALIASES.get(normalized)

    if alias is not None:
        return alias

    if normalized.isdigit():
        return normalized

    if len(normalized) > 5 and normalized.endswith("ies"):
        return normalized[:-3] + "y"

    if len(normalized) > 5 and normalized.endswith("ing"):
        stem = normalized[:-3]

        if stem.endswith(stem[-1:]):
            return stem

        return stem

    if len(normalized) > 4 and normalized.endswith("ed"):
        return normalized[:-2]

    if len(normalized) > 4 and normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]

    return normalized


def _numeric_terms(
    query: str,
) -> list[str]:
    """Return unique numeric tokens that require exact support."""

    terms: list[str] = []

    for token in _SIMPLE_TOKEN_RE.findall(query):
        if token.isdigit() and token not in terms:
            terms.append(token)

    return terms


def _named_anchors(
    query: str,
) -> list[str]:
    """Return acronyms and mixed-case hyphenated names from a query."""

    anchors: list[str] = []

    for token in _TOKEN_RE.findall(query):
        parts = _SIMPLE_TOKEN_RE.findall(token)

        if token.isupper() and token.isalpha() and len(token) >= 2:
            normalized = _normalize_token(token)

            if normalized not in anchors:
                anchors.append(normalized)

            continue

        has_internal_uppercase = any(character.isupper() for character in token[1:])
        has_digit = any(character.isdigit() for character in token)

        if "-" in token:
            if not (has_internal_uppercase or has_digit):
                continue
        elif not has_internal_uppercase:
            continue

        for part in parts:
            normalized = _normalize_token(part)

            if len(normalized) >= 2 and normalized not in anchors:
                anchors.append(normalized)

    return anchors


def _claim_qualifiers(
    query: str,
) -> list[str]:
    """Return assertion-defining terms requiring support."""

    qualifiers: list[str] = []

    for token in _SIMPLE_TOKEN_RE.findall(query.casefold()):
        qualifier = _CLAIM_QUALIFIER_ALIASES.get(token)

        if qualifier is not None and qualifier not in qualifiers:
            qualifiers.append(qualifier)

    return qualifiers


def _safe_ratio(
    numerator: int,
    denominator: int,
) -> float:
    """Return a deterministic ratio for possibly empty collections."""

    if denominator == 0:
        return 0.0

    return numerator / denominator
