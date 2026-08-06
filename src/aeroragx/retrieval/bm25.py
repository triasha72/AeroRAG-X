"""Deterministic BM25 retrieval over AeroRAG-X chunks."""

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aeroragx.processing.chunking import ChunkRecord

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")


class BM25Config(BaseModel):
    """Configuration for the BM25 lexical baseline."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    k1: float = Field(
        default=1.5,
        gt=0.0,
        le=5.0,
    )
    b: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )
    default_top_k: int = Field(
        default=10,
        ge=1,
        le=100,
    )


class SearchHit(BaseModel):
    """One ranked retrieval result."""

    model_config = ConfigDict(
        extra="forbid",
    )

    rank: int = Field(ge=1)
    score: float = Field(ge=0.0)
    chunk: ChunkRecord


def tokenize(text: str) -> list[str]:
    """Normalize text into deterministic lexical tokens."""

    return _TOKEN_PATTERN.findall(text.lower())


def load_bm25_config(
    path: Path,
) -> BM25Config:
    """Load and validate BM25 YAML configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("BM25 configuration must contain a YAML mapping.")

    return BM25Config.model_validate(raw_data)


def load_chunk_records(
    path: Path,
) -> list[ChunkRecord]:
    """Load retrieval chunks from JSON Lines."""

    chunks: list[ChunkRecord] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            chunk = ChunkRecord.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid chunk row {line_number}: {exc}") from exc

        chunks.append(chunk)

    return chunks


class BM25Index:
    """In-memory BM25 inverted index."""

    def __init__(
        self,
        chunks: Sequence[ChunkRecord],
        config: BM25Config | None = None,
    ) -> None:
        self._chunks = list(chunks)
        self._config = config or BM25Config()

        tokenized_documents = [tokenize(chunk.text) for chunk in self._chunks]

        self._document_lengths = [len(tokens) for tokens in tokenized_documents]

        if self._document_lengths:
            self._average_document_length = sum(self._document_lengths) / len(
                self._document_lengths
            )
        else:
            self._average_document_length = 0.0

        postings: defaultdict[
            str,
            list[tuple[int, int]],
        ] = defaultdict(list)

        for document_index, tokens in enumerate(tokenized_documents):
            frequencies: Counter[str] = Counter(tokens)

            for term, frequency in frequencies.items():
                postings[term].append(
                    (
                        document_index,
                        frequency,
                    )
                )

        self._postings = dict(postings)

    @property
    def document_count(self) -> int:
        """Return the number of indexed chunks."""

        return len(self._chunks)

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchHit]:
        """Return the highest-scoring chunks for a query."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        query_terms = tokenize(query)

        if not query_terms or not self._chunks or self._average_document_length == 0:
            return []

        scores = [0.0 for _ in self._chunks]

        unique_query_terms = dict.fromkeys(query_terms)

        for term in unique_query_terms:
            term_postings = self._postings.get(term)

            if not term_postings:
                continue

            document_frequency = len(term_postings)

            inverse_document_frequency = math.log(
                1.0 + (len(self._chunks) - document_frequency + 0.5) / (document_frequency + 0.5)
            )

            for document_index, frequency in term_postings:
                document_length = self._document_lengths[document_index]

                length_normalization = (
                    1.0
                    - self._config.b
                    + self._config.b * (document_length / self._average_document_length)
                )

                denominator = frequency + self._config.k1 * length_normalization

                scores[document_index] += (
                    inverse_document_frequency * frequency * (self._config.k1 + 1.0) / denominator
                )

        ranked_results = sorted(
            (
                (
                    score,
                    self._chunks[document_index],
                )
                for document_index, score in enumerate(scores)
                if score > 0.0
            ),
            key=lambda result: (
                -result[0],
                result[1].chunk_id,
            ),
        )

        return [
            SearchHit(
                rank=rank,
                score=round(score, 8),
                chunk=chunk,
            )
            for rank, (score, chunk) in enumerate(
                ranked_results[:top_k],
                start=1,
            )
        ]


def write_search_results(
    path: Path,
    hits: Sequence[SearchHit],
) -> None:
    """Write ranked results to JSON Lines."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = [
        json.dumps(
            hit.model_dump(mode="json"),
            sort_keys=True,
        )
        for hit in hits
    ]

    content = "\n".join(rows)

    if content:
        content += "\n"

    path.write_text(
        content,
        encoding="utf-8",
    )
