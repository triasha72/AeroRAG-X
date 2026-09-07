"""SciFact claim, document, and human-evidence contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SciFactDocument:
    doc_id: int
    title: str
    abstract: tuple[str, ...]


@dataclass(frozen=True)
class SciFactClaim:
    claim_id: int
    text: str
    evidence_doc_ids: tuple[int, ...]
    evidence_sentence_ids: dict[int, tuple[int, ...]]


def normalize_corpus(rows: Iterable[Mapping[str, Any]]) -> tuple[SciFactDocument, ...]:
    documents = []
    for row in rows:
        abstract = tuple(str(sentence).strip() for sentence in row.get("abstract", ()))
        if not abstract or any(not sentence for sentence in abstract):
            raise ValueError("SciFact documents require a non-empty sentence-level abstract")
        documents.append(SciFactDocument(int(row["doc_id"]), str(row["title"]).strip(), abstract))
    if not documents:
        raise ValueError("No SciFact documents found")
    if len({document.doc_id for document in documents}) != len(documents):
        raise ValueError("SciFact document IDs must be unique")
    return tuple(documents)


def normalize_claims(rows: Iterable[Mapping[str, Any]]) -> tuple[SciFactClaim, ...]:
    claims = []
    for row in rows:
        evidence = row.get("evidence", {})
        if not isinstance(evidence, Mapping) or not evidence:
            continue
        sentence_ids: dict[int, tuple[int, ...]] = {}
        for raw_doc_id, rationales in evidence.items():
            sentence_ids[int(raw_doc_id)] = tuple(
                sorted(
                    {
                        int(sentence_id)
                        for rationale in rationales
                        for sentence_id in rationale["sentences"]
                    }
                )
            )
        text = str(row.get("claim", "")).strip()
        if not text:
            raise ValueError("SciFact claims require claim text")
        claims.append(
            SciFactClaim(
                claim_id=int(row["id"]),
                text=text,
                evidence_doc_ids=tuple(sorted(sentence_ids)),
                evidence_sentence_ids=sentence_ids,
            )
        )
    if not claims:
        raise ValueError("No SciFact claims with human evidence found")
    return tuple(claims)
