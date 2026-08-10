"""Protected evaluation-document manifest schemas and helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


class ProtectedQueryEvidence(BaseModel):
    """Protected evidence identifiers for one frozen evaluation query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(
        min_length=1,
    )

    expected_answerable: bool

    document_ids: list[int] = Field(
        min_length=1,
    )

    chunk_ids: list[str] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_query_evidence(
        self,
    ) -> Self:
        """Validate uniqueness and identifier ranges within one query."""

        if any(document_id < 1 for document_id in self.document_ids):
            raise ValueError("Protected document IDs must be positive integers.")

        if len(self.document_ids) != len(set(self.document_ids)):
            raise ValueError(f"Protected query {self.query_id!r} contains duplicate document IDs.")

        if len(self.chunk_ids) != len(set(self.chunk_ids)):
            raise ValueError(f"Protected query {self.query_id!r} contains duplicate chunk IDs.")

        return self


class ProtectedDocumentManifest(BaseModel):
    """Frozen document/chunk boundary for generation evaluation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(
        min_length=1,
    )

    purpose: str = Field(
        min_length=1,
    )

    source_evaluation: str = Field(
        min_length=1,
    )

    dense_backend: str = Field(
        min_length=1,
    )

    candidate_top_k: int = Field(
        ge=1,
    )

    evidence_top_k: int = Field(
        ge=1,
    )

    query_count: int = Field(
        ge=1,
    )

    protected_document_count: int = Field(
        ge=1,
    )

    protected_chunk_count: int = Field(
        ge=1,
    )

    protected_document_ids: list[int] = Field(
        min_length=1,
    )

    protected_chunk_ids: list[str] = Field(
        min_length=1,
    )

    queries: list[ProtectedQueryEvidence] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_manifest_consistency(
        self,
    ) -> Self:
        """Validate counts, uniqueness, and global/query-set consistency."""

        if any(document_id < 1 for document_id in self.protected_document_ids):
            raise ValueError("Protected document IDs must be positive integers.")

        if len(self.protected_document_ids) != len(set(self.protected_document_ids)):
            raise ValueError("Protected document IDs must be unique.")

        if len(self.protected_chunk_ids) != len(set(self.protected_chunk_ids)):
            raise ValueError("Protected chunk IDs must be unique.")

        query_ids = [query.query_id for query in self.queries]

        if len(query_ids) != len(set(query_ids)):
            raise ValueError("Protected query IDs must be unique.")

        if self.query_count != len(self.queries):
            raise ValueError("query_count does not match the number of protected query records.")

        if self.protected_document_count != len(self.protected_document_ids):
            raise ValueError("protected_document_count does not match protected_document_ids.")

        if self.protected_chunk_count != len(self.protected_chunk_ids):
            raise ValueError("protected_chunk_count does not match protected_chunk_ids.")

        global_document_ids = set(self.protected_document_ids)

        global_chunk_ids = set(self.protected_chunk_ids)

        query_document_ids: set[int] = set()

        query_chunk_ids: set[str] = set()

        for query in self.queries:
            if len(query.chunk_ids) != self.evidence_top_k:
                raise ValueError(
                    f"Protected query "
                    f"{query.query_id!r} "
                    f"contains "
                    f"{len(query.chunk_ids)} "
                    f"chunks; expected "
                    f"{self.evidence_top_k}."
                )

            unknown_documents = set(query.document_ids) - global_document_ids

            if unknown_documents:
                raise ValueError(
                    f"Protected query "
                    f"{query.query_id!r} "
                    "references document IDs "
                    "missing from the global "
                    "protected set: " + ", ".join(str(value) for value in sorted(unknown_documents))
                )

            unknown_chunks = set(query.chunk_ids) - global_chunk_ids

            if unknown_chunks:
                raise ValueError(
                    f"Protected query "
                    f"{query.query_id!r} "
                    "references chunk IDs "
                    "missing from the global "
                    "protected set: " + ", ".join(sorted(unknown_chunks))
                )

            query_document_ids.update(query.document_ids)

            query_chunk_ids.update(query.chunk_ids)

        if query_document_ids != global_document_ids:
            raise ValueError(
                "Global "
                "protected_document_ids "
                "must exactly equal the union "
                "of per-query document IDs."
            )

        if query_chunk_ids != global_chunk_ids:
            raise ValueError(
                "Global protected_chunk_ids must exactly equal the union of per-query chunk IDs."
            )

        return self

    @property
    def protected_document_id_set(
        self,
    ) -> set[int]:
        """Return protected document IDs as a defensive set."""

        return set(self.protected_document_ids)

    @property
    def protected_chunk_id_set(
        self,
    ) -> set[str]:
        """Return protected chunk IDs as a defensive set."""

        return set(self.protected_chunk_ids)


def load_protected_document_manifest(
    path: Path,
) -> ProtectedDocumentManifest:
    """Load and validate a protected-document manifest."""

    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))

    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid protected-document JSON in {path}.") from exc

    try:
        return ProtectedDocumentManifest.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid protected-document manifest {path}.") from exc


def write_protected_document_manifest(
    path: Path,
    manifest: ProtectedDocumentManifest,
) -> None:
    """Write a deterministic protected-document JSON artifact."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
