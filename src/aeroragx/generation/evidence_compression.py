"""Query-aware extractive compression that preserves every selected source."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.retrieval.reranker import RerankedSearchHit

_WORDS = re.compile(r"[a-z0-9]+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
}


class EvidenceCompressionConfig(BaseModel):
    """Frozen per-passage extractive limits."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1"
    max_sentences_per_evidence: int = Field(default=2, ge=1, le=20)
    max_characters_per_evidence: int = Field(default=1200, ge=100, le=10_000)
    minimum_sentence_characters: int = Field(default=20, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_limits(self) -> Self:
        if self.minimum_sentence_characters > self.max_characters_per_evidence:
            raise ValueError(
                "minimum_sentence_characters must not exceed max_characters_per_evidence."
            )
        return self


class EvidenceCompressionDecision(BaseModel):
    """Per-query character accounting for extractive compression."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    evidence_count: int = Field(ge=0)
    original_characters: int = Field(ge=0)
    compressed_characters: int = Field(ge=0)
    removed_characters: int = Field(ge=0)
    relative_character_reduction: float = Field(ge=0.0, le=1.0)
    source_chunk_ids: list[str]


class EvidenceSearchIndex(Protocol):
    def search(self, query: str, top_k: int = 10) -> Sequence[RerankedSearchHit]: ...


def _terms(text: str) -> set[str]:
    return {word for word in _WORDS.findall(text.casefold()) if word not in _STOP}


def compress_evidence_text(*, query: str, text: str, config: EvidenceCompressionConfig) -> str:
    """Select query-relevant complete sentences while retaining a non-empty excerpt."""

    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY.split(text.strip())
        if len(sentence.strip()) >= config.minimum_sentence_characters
    ]
    if not sentences:
        return text[: config.max_characters_per_evidence].strip()
    query_terms = _terms(query)
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (
            -len(query_terms & _terms(item[1])),
            -len(query_terms & _terms(item[1])) / max(1, len(_terms(item[1]))),
            item[0],
        ),
    )
    chosen_indices = sorted(index for index, _ in ranked[: config.max_sentences_per_evidence])
    selected: list[str] = []
    used = 0
    for index in chosen_indices:
        sentence = sentences[index]
        separator = 1 if selected else 0
        remaining = config.max_characters_per_evidence - used - separator
        if remaining <= 0:
            break
        excerpt = sentence[:remaining].strip()
        if excerpt:
            selected.append(excerpt)
            used += len(excerpt) + separator
    return " ".join(selected).strip() or text[: config.max_characters_per_evidence].strip()


class CompressedEvidenceIndex:
    """Compress hit text without removing hits or changing source identity."""

    def __init__(self, index: EvidenceSearchIndex, config: EvidenceCompressionConfig) -> None:
        self._index = index
        self._config = config
        self._decisions: list[EvidenceCompressionDecision] = []

    @property
    def decisions(self) -> list[EvidenceCompressionDecision]:
        return [decision.model_copy(deep=True) for decision in self._decisions]

    def search(self, query: str, top_k: int = 10) -> Sequence[RerankedSearchHit]:
        hits = list(self._index.search(query=query, top_k=top_k))
        compressed: list[RerankedSearchHit] = []
        original_characters = 0
        compressed_characters = 0
        chunk_ids: list[str] = []
        for hit in hits:
            original = hit.chunk.text
            excerpt = compress_evidence_text(query=query, text=original, config=self._config)
            if not excerpt:
                raise ValueError("Evidence compression produced an empty passage.")
            original_characters += len(original)
            compressed_characters += len(excerpt)
            chunk_ids.append(hit.chunk.chunk_id)
            compressed_chunk = hit.chunk.model_copy(
                update={
                    "text": excerpt,
                    "word_count": max(1, len(excerpt.split())),
                    "character_count": len(excerpt),
                    "token_estimate": max(1, (len(excerpt) + 3) // 4),
                }
            )
            compressed.append(hit.model_copy(update={"chunk": compressed_chunk}))
        removed = original_characters - compressed_characters
        self._decisions.append(
            EvidenceCompressionDecision(
                query=query,
                evidence_count=len(compressed),
                original_characters=original_characters,
                compressed_characters=compressed_characters,
                removed_characters=removed,
                relative_character_reduction=(
                    removed / original_characters if original_characters else 0.0
                ),
                source_chunk_ids=chunk_ids,
            )
        )
        return compressed

    def __getattr__(self, name: str) -> Any:
        return getattr(self._index, name)


def load_evidence_compression_config(path: Path) -> EvidenceCompressionConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Evidence-compression configuration must contain a YAML mapping.")
    return EvidenceCompressionConfig.model_validate(raw)
