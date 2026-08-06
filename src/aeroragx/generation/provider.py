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
    """Deterministic provider used by unit tests and fixed smoke tests."""

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


class DeterministicGenerationProvider:
    """Create an extractive answer without calling an external model."""

    def __init__(
        self,
        *,
        maximum_claim_characters: int = 420,
    ) -> None:
        if maximum_claim_characters < 1:
            raise ValueError("maximum_claim_characters must be at least 1.")

        self._maximum_claim_characters = maximum_claim_characters
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
        """Build cited extractive claims in the supplied evidence order."""

        if max_claims < 1:
            raise ValueError("max_claims must be at least 1.")

        copied_evidence = [item.model_copy(deep=True) for item in evidence]

        self.received_queries.append(query)
        self.received_evidence.append(copied_evidence)
        self.received_max_claims.append(max_claims)

        if not copied_evidence:
            return ProviderResponse(
                answer=("The supplied evidence is insufficient to answer this question reliably."),
                claims=[],
                insufficient_evidence=True,
            )

        selected = copied_evidence[:max_claims]

        claims = [
            ProviderClaim(
                text=_extract_statement(
                    item.text,
                    maximum_characters=(self._maximum_claim_characters),
                ),
                evidence_ids=[item.evidence_id],
            )
            for item in selected
        ]

        answer = " ".join(claim.text for claim in claims)

        return ProviderResponse(
            answer=answer,
            claims=claims,
            insufficient_evidence=False,
        )


def _extract_statement(
    text: str,
    *,
    maximum_characters: int,
) -> str:
    """Return one normalized, bounded extractive statement."""

    normalized = " ".join(text.split())

    if not normalized:
        raise ValueError("Evidence text must not be blank.")

    bounded = normalized[:maximum_characters]

    if len(normalized) <= maximum_characters:
        return bounded

    sentence_positions = [
        bounded.rfind(terminator)
        for terminator in (
            ".",
            "!",
            "?",
        )
    ]
    sentence_end = max(sentence_positions)

    if sentence_end >= 0:
        return bounded[: sentence_end + 1].strip()

    word_end = bounded.rfind(" ")

    if word_end > 0:
        return bounded[:word_end].rstrip() + "…"

    return bounded.rstrip() + "…"


def create_generation_provider(
    provider_name: str,
) -> GenerationProvider:
    """Create one supported local generation provider by name."""

    normalized = provider_name.strip().lower()

    if normalized in {
        "fake",
        "deterministic",
        "extractive",
    }:
        return DeterministicGenerationProvider()

    raise ValueError(
        "Unsupported generation provider "
        f"{provider_name!r}. Supported local "
        "providers are: fake, deterministic, "
        "extractive."
    )
