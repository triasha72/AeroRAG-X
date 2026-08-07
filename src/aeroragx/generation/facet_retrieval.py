"""Deterministic facet-aware evidence selection for synthesis queries."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.retrieval.reranker import RerankedSearchHit

_SHARED_BY_RE = re.compile(
    r"^\s*(?:what\s+)?(?P<topic>.+?)\s+are\s+shared\s+by\s+"
    r"(?P<left>.+?)\s+and\s+(?P<right>.+?)[?.!]*\s*$",
    re.IGNORECASE,
)
_SIMPLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_GENERIC_FACET_TERMS = {
    "a",
    "an",
    "and",
    "aircraft",
    "aircrafts",
    "system",
    "systems",
    "propulsion",
    "the",
}


class FacetSearchIndex(Protocol):
    def search(self, query: str, top_k: int = 10) -> Sequence[RerankedSearchHit]: ...


class FacetRetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: str = "0.1"
    enabled: bool = True
    facet_search_top_k: int = Field(default=15, ge=1, le=100)
    per_facet_quota: int = Field(default=2, ge=1, le=20)
    original_quota: int = Field(default=1, ge=0, le=20)
    minimum_semantic_matches_per_facet: int = Field(default=1, ge=1, le=20)

    @model_validator(mode="after")
    def validate_quotas(self) -> Self:
        if self.minimum_semantic_matches_per_facet > self.per_facet_quota:
            raise ValueError("minimum_semantic_matches_per_facet must not exceed per_facet_quota.")
        if self.per_facet_quota > self.facet_search_top_k:
            raise ValueError("per_facet_quota must not exceed facet_search_top_k.")
        return self


class QueryFacet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    text: str = Field(min_length=1)
    search_query: str = Field(min_length=1)
    required_terms: list[str] = Field(min_length=1)


class FacetPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_query: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    facets: list[QueryFacet] = Field(min_length=2)


def load_facet_retrieval_config(path: Path) -> FacetRetrievalConfig:
    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise ValueError("Facet retrieval configuration must contain a YAML mapping.")
    return FacetRetrievalConfig.model_validate(raw_data)


def plan_shared_facets(query: str) -> FacetPlan | None:
    normalized = query.strip()
    if not normalized:
        raise ValueError("query must not be blank.")
    match = _SHARED_BY_RE.match(normalized)
    if match is None:
        return None
    topic = match.group("topic").strip()
    facet_texts = [match.group("left").strip(), match.group("right").strip()]
    facets: list[QueryFacet] = []
    for number, facet_text in enumerate(facet_texts, start=1):
        required_terms = _facet_terms(facet_text)
        if not required_terms:
            return None
        facets.append(
            QueryFacet(
                name=f"facet_{number}",
                text=facet_text,
                search_query=f"{facet_text} {topic}",
                required_terms=required_terms,
            )
        )
    return FacetPlan(original_query=normalized, topic=topic, facets=facets)


class FacetAwareEvidenceIndex:
    def __init__(self, base_index: FacetSearchIndex, config: FacetRetrievalConfig) -> None:
        self._base_index = base_index
        self._config = config
        self._last_plan: FacetPlan | None = None
        self._last_facet_match_counts: dict[str, int] = {}
        self._last_used_facets = False

    @property
    def last_plan(self) -> FacetPlan | None:
        return self._last_plan

    @property
    def last_facet_match_counts(self) -> dict[str, int]:
        return dict(self._last_facet_match_counts)

    @property
    def last_used_facets(self) -> bool:
        return self._last_used_facets

    def search(self, query: str, top_k: int = 10) -> list[RerankedSearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        self._last_plan = None
        self._last_facet_match_counts = {}
        self._last_used_facets = False

        if not self._config.enabled:
            return list(self._base_index.search(query=query, top_k=top_k))

        plan = plan_shared_facets(query)
        if plan is None:
            return list(self._base_index.search(query=query, top_k=top_k))

        self._last_plan = plan
        search_top_k = max(top_k, self._config.facet_search_top_k)
        original_hits = list(self._base_index.search(query=query, top_k=search_top_k))

        facet_buckets: list[tuple[QueryFacet, list[RerankedSearchHit]]] = []
        for facet in plan.facets:
            hits = list(self._base_index.search(query=facet.search_query, top_k=search_top_k))
            matching_hits = [
                hit
                for hit in hits
                if _contains_required_terms(hit.chunk.text, facet.required_terms)
            ]
            self._last_facet_match_counts[facet.name] = len(matching_hits)
            if len(matching_hits) < self._config.minimum_semantic_matches_per_facet:
                return _renumber_hits(original_hits[:top_k])
            facet_buckets.append((facet, matching_hits))

        selected: list[RerankedSearchHit] = []
        seen_chunk_ids: set[str] = set()

        for position in range(self._config.per_facet_quota):
            for _, bucket in facet_buckets:
                if position >= len(bucket):
                    continue
                hit = bucket[position]
                if hit.chunk.chunk_id in seen_chunk_ids:
                    continue
                selected.append(hit)
                seen_chunk_ids.add(hit.chunk.chunk_id)
                if len(selected) >= top_k:
                    self._last_used_facets = True
                    return _renumber_hits(selected[:top_k])

        original_added = 0
        for hit in original_hits:
            if hit.chunk.chunk_id in seen_chunk_ids:
                continue
            selected.append(hit)
            seen_chunk_ids.add(hit.chunk.chunk_id)
            original_added += 1
            if original_added >= self._config.original_quota or len(selected) >= top_k:
                break

        if len(selected) < top_k:
            for hit in original_hits:
                if hit.chunk.chunk_id in seen_chunk_ids:
                    continue
                selected.append(hit)
                seen_chunk_ids.add(hit.chunk.chunk_id)
                if len(selected) >= top_k:
                    break

        self._last_used_facets = True
        return _renumber_hits(selected[:top_k])


def _facet_terms(facet_text: str) -> list[str]:
    terms: list[str] = []
    for token in _SIMPLE_TOKEN_RE.findall(facet_text.casefold()):
        if token in _GENERIC_FACET_TERMS:
            continue
        if token not in terms:
            terms.append(token)
    return terms


def _normalized_token_set(text: str) -> set[str]:
    return {token.casefold() for token in _SIMPLE_TOKEN_RE.findall(text)}


def _contains_required_terms(text: str, required_terms: Sequence[str]) -> bool:
    tokens = _normalized_token_set(text)
    return all(term.casefold() in tokens for term in required_terms)


def _renumber_hits(hits: Sequence[RerankedSearchHit]) -> list[RerankedSearchHit]:
    return [hit.model_copy(update={"rank": rank}) for rank, hit in enumerate(hits, start=1)]
