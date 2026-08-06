"""Provider-agnostic schemas for grounded answer generation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderEvidence(BaseModel):
    """Minimal evidence record exposed to a generation provider."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    evidence_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ProviderClaim(BaseModel):
    """One provider-authored claim referencing supplied evidence IDs."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class ProviderResponse(BaseModel):
    """Structured draft returned by a generation provider."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    answer: str = Field(min_length=1)
    claims: list[ProviderClaim] = Field(default_factory=list)
    insufficient_evidence: bool = False


class GenerationProvider(Protocol):
    """Interface implemented by local or API-based generation backends."""

    def generate(
        self,
        *,
        query: str,
        evidence: Sequence[ProviderEvidence],
        max_claims: int,
    ) -> ProviderResponse:
        """Generate a structured response from only the supplied evidence."""

        ...


class StaticGenerationProvider:
    """Deterministic provider used by unit tests and local smoke tests."""

    def __init__(self, response: ProviderResponse) -> None:
        self._response = response
        self.received_queries: list[str] = []
        self.received_evidence: list[list[ProviderEvidence]] = []
        self.received_max_claims: list[int] = []

    @property
    def call_count(self) -> int:
        """Return the number of generation calls received."""

        return len(self.received_queries)

    def generate(
        self,
        *,
        query: str,
        evidence: Sequence[ProviderEvidence],
        max_claims: int,
    ) -> ProviderResponse:
        """Return a deep copy of the configured deterministic response."""

        self.received_queries.append(query)
        self.received_evidence.append([item.model_copy(deep=True) for item in evidence])
        self.received_max_claims.append(max_claims)

        return self._response.model_copy(deep=True)
