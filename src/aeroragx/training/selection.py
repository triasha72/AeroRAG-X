"""Deterministic source-document selection for LoRA training."""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

type SelectionStatus = Literal[
    "selected",
    "duplicate_excluded",
    "not_selected",
]


class SourceSelectionConfig(BaseModel):
    """Configuration for deterministic LoRA source selection."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(
        min_length=1,
    )

    corpus_version: str = Field(
        min_length=1,
    )

    target_document_count: int = Field(
        ge=1,
    )

    minimum_chunks_per_document: int = Field(
        ge=1,
    )

    expected_corpus_document_count: int = Field(
        ge=1,
    )

    expected_protected_document_count: int = Field(
        ge=0,
    )

    expected_candidate_document_count: int = Field(
        ge=1,
    )

    expected_candidate_chunk_count: int = Field(
        ge=1,
    )

    deduplicate_exact_titles: bool = True

    source_query_minimums: dict[
        str,
        int,
    ] = Field(
        default_factory=dict,
    )

    type_priority: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_selection_config(
        self,
    ) -> Self:
        """Validate selection constraints."""

        if self.target_document_count > self.expected_candidate_document_count:
            raise ValueError(
                "target_document_count must not exceed expected_candidate_document_count."
            )

        if len(self.type_priority) != len(set(self.type_priority)):
            raise ValueError("type_priority must not contain duplicates.")

        for query, minimum in self.source_query_minimums.items():
            if not query.strip():
                raise ValueError("source_query_minimums contains a blank query.")

            if minimum < 0:
                raise ValueError("source-query minimums must be non-negative.")

        return self


class SourceDocumentMetadata(BaseModel):
    """Metadata needed to decide whether a document is selected."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int = Field(
        ge=1,
    )

    title: str = Field(
        min_length=1,
    )

    chunk_count: int = Field(
        ge=1,
    )

    source_queries: list[str] = Field(
        default_factory=list,
    )

    sti_type: str = "UNKNOWN"

    subject_categories: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_metadata(
        self,
    ) -> Self:
        """Validate list uniqueness."""

        if len(self.source_queries) != len(set(self.source_queries)):
            raise ValueError("source_queries must not contain duplicates.")

        if len(self.subject_categories) != len(set(self.subject_categories)):
            raise ValueError("subject_categories must not contain duplicates.")

        return self


class SourceDocumentSelection(BaseModel):
    """Selection decision for one clean candidate document."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int = Field(
        ge=1,
    )

    title: str = Field(
        min_length=1,
    )

    chunk_count: int = Field(
        ge=1,
    )

    source_queries: list[str]

    sti_type: str

    subject_categories: list[str]

    status: SelectionStatus

    reason: str = Field(
        min_length=1,
    )

    duplicate_family_id: str | None = None

    representative_document_id: int | None = None


class LoRASourceSelectionManifest(BaseModel):
    """Frozen source-document boundary for LoRA dataset construction."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(
        min_length=1,
    )

    corpus_version: str = Field(
        min_length=1,
    )

    corpus_chunks_path: str = Field(
        min_length=1,
    )

    metadata_manifest_path: str = Field(
        min_length=1,
    )

    protected_manifest_path: str = Field(
        min_length=1,
    )

    protected_manifest_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    selection_config_path: str = Field(
        min_length=1,
    )

    selection_config_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    corpus_document_count: int = Field(
        ge=1,
    )

    protected_document_count: int = Field(
        ge=0,
    )

    candidate_document_count: int = Field(
        ge=1,
    )

    candidate_chunk_count: int = Field(
        ge=1,
    )

    deduplicated_candidate_count: int = Field(
        ge=1,
    )

    selected_document_count: int = Field(
        ge=1,
    )

    selected_chunk_count: int = Field(
        ge=1,
    )

    duplicate_excluded_document_count: int = Field(
        ge=0,
    )

    not_selected_document_count: int = Field(
        ge=0,
    )

    protected_overlap_count: int = Field(
        ge=0,
    )

    selected_document_ids: list[int] = Field(
        min_length=1,
    )

    source_query_selected_counts: dict[
        str,
        int,
    ]

    documents: list[SourceDocumentSelection] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_manifest_consistency(
        self,
    ) -> Self:
        """Validate all frozen source-selection counts."""

        document_ids = [document.document_id for document in self.documents]

        if len(document_ids) != len(set(document_ids)):
            raise ValueError("Source-selection document IDs must be unique.")

        if self.candidate_document_count != len(self.documents):
            raise ValueError(
                "candidate_document_count does not match the number of document records."
            )

        observed_candidate_chunks = sum(document.chunk_count for document in self.documents)

        if self.candidate_chunk_count != observed_candidate_chunks:
            raise ValueError("candidate_chunk_count does not match document chunk counts.")

        selected_documents = [
            document for document in self.documents if document.status == "selected"
        ]

        duplicate_documents = [
            document for document in self.documents if document.status == "duplicate_excluded"
        ]

        not_selected_documents = [
            document for document in self.documents if document.status == "not_selected"
        ]

        if self.selected_document_count != len(selected_documents):
            raise ValueError("selected_document_count mismatch.")

        if self.duplicate_excluded_document_count != len(duplicate_documents):
            raise ValueError("duplicate_excluded_document_count mismatch.")

        if self.not_selected_document_count != len(not_selected_documents):
            raise ValueError("not_selected_document_count mismatch.")

        expected_deduplicated = (
            self.candidate_document_count - self.duplicate_excluded_document_count
        )

        if self.deduplicated_candidate_count != expected_deduplicated:
            raise ValueError("deduplicated_candidate_count mismatch.")

        selected_ids = sorted(document.document_id for document in selected_documents)

        if self.selected_document_ids != selected_ids:
            raise ValueError(
                "selected_document_ids must be sorted and exactly match selected document records."
            )

        observed_selected_chunks = sum(document.chunk_count for document in selected_documents)

        if self.selected_chunk_count != observed_selected_chunks:
            raise ValueError("selected_chunk_count mismatch.")

        if self.protected_overlap_count != 0:
            raise ValueError("A frozen LoRA source selection must have zero protected overlap.")

        observed_query_counts = _source_query_counts(selected_documents)

        if self.source_query_selected_counts != observed_query_counts:
            raise ValueError("source_query_selected_counts mismatch.")

        return self

    @property
    def selected_document_id_set(
        self,
    ) -> set[int]:
        """Return selected IDs as a defensive set."""

        return set(self.selected_document_ids)


def load_source_selection_config(
    path: Path,
) -> SourceSelectionConfig:
    """Load and validate source-selection YAML."""

    try:
        raw_value = yaml.safe_load(path.read_text(encoding="utf-8"))

    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid source-selection YAML in {path}.") from exc

    try:
        return SourceSelectionConfig.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid source-selection config {path}.") from exc


def load_source_selection_manifest(
    path: Path,
) -> LoRASourceSelectionManifest:
    """Load and validate a frozen source-selection manifest."""

    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))

    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid source-selection JSON in {path}.") from exc

    try:
        return LoRASourceSelectionManifest.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid source-selection manifest {path}.") from exc


def write_source_selection_manifest(
    path: Path,
    manifest: LoRASourceSelectionManifest,
) -> None:
    """Write deterministic source-selection JSON."""

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


def select_source_documents(
    candidates: Sequence[SourceDocumentMetadata],
    *,
    protected_document_ids: Collection[int],
    config: SourceSelectionConfig,
    corpus_document_count: int,
    protected_document_count: int,
    candidate_chunk_count: int,
    corpus_chunks_path: str,
    metadata_manifest_path: str,
    protected_manifest_path: str,
    protected_manifest_sha256: str,
    selection_config_path: str,
    selection_config_sha256: str,
) -> LoRASourceSelectionManifest:
    """Select a deterministic diverse subset of clean source documents."""

    candidate_documents = list(candidates)

    candidate_ids = [document.document_id for document in candidate_documents]

    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Candidate source documents contain duplicate document IDs.")

    if corpus_document_count != config.expected_corpus_document_count:
        raise ValueError(
            "Corpus document count changed: "
            f"expected "
            f"{config.expected_corpus_document_count}, "
            f"observed {corpus_document_count}."
        )

    if protected_document_count != config.expected_protected_document_count:
        raise ValueError(
            "Protected document count changed: "
            f"expected "
            f"{config.expected_protected_document_count}, "
            f"observed {protected_document_count}."
        )

    if len(candidate_documents) != config.expected_candidate_document_count:
        raise ValueError(
            "Candidate document count changed: "
            f"expected "
            f"{config.expected_candidate_document_count}, "
            f"observed {len(candidate_documents)}."
        )

    observed_candidate_chunks = sum(document.chunk_count for document in candidate_documents)

    if candidate_chunk_count != observed_candidate_chunks:
        raise ValueError("candidate_chunk_count does not match candidate metadata.")

    if candidate_chunk_count != config.expected_candidate_chunk_count:
        raise ValueError(
            "Candidate chunk count changed: "
            f"expected "
            f"{config.expected_candidate_chunk_count}, "
            f"observed {candidate_chunk_count}."
        )

    protected = set(protected_document_ids)

    protected_overlap = sorted(set(candidate_ids) & protected)

    if protected_overlap:
        raise ValueError(
            "Protected documents appeared in "
            "the LoRA candidate pool: "
            + ", ".join(str(document_id) for document_id in protected_overlap)
        )

    type_rank = {sti_type: index for index, sti_type in enumerate(config.type_priority)}

    duplicate_excluded_ids: set[int] = set()

    family_by_document: dict[
        int,
        str,
    ] = {}

    representative_by_excluded: dict[
        int,
        int,
    ] = {}

    if config.deduplicate_exact_titles:
        title_groups: dict[
            str,
            list[SourceDocumentMetadata],
        ] = {}

        for document in candidate_documents:
            normalized_title = normalize_source_title(document.title)

            title_groups.setdefault(
                normalized_title,
                [],
            ).append(document)

        for (
            normalized_title,
            members,
        ) in title_groups.items():
            if len(members) < 2:
                continue

            family_id = _duplicate_family_id(normalized_title)

            representative = min(
                members,
                key=lambda document: _document_rank(
                    document,
                    type_rank=type_rank,
                ),
            )

            for document in members:
                family_by_document[document.document_id] = family_id

                if document.document_id == representative.document_id:
                    continue

                duplicate_excluded_ids.add(document.document_id)

                representative_by_excluded[document.document_id] = representative.document_id

    deduplicated_candidates = [
        document
        for document in candidate_documents
        if document.document_id not in duplicate_excluded_ids
    ]

    eligible = [
        document
        for document in deduplicated_candidates
        if (document.chunk_count >= config.minimum_chunks_per_document)
    ]

    if len(eligible) < config.target_document_count:
        raise ValueError(
            "Not enough eligible source documents "
            "remain after deduplication and "
            "minimum-chunk filtering: "
            f"need {config.target_document_count}, "
            f"have {len(eligible)}."
        )

    eligible.sort(
        key=lambda document: _document_rank(
            document,
            type_rank=type_rank,
        )
    )

    selected_ids: set[int] = set()

    selection_reasons: dict[
        int,
        str,
    ] = {}

    for (
        source_query,
        minimum,
    ) in config.source_query_minimums.items():
        while (
            _selected_query_count(
                eligible,
                selected_ids=selected_ids,
                source_query=source_query,
            )
            < minimum
        ):
            choices = [
                document
                for document in eligible
                if (
                    document.document_id not in selected_ids
                    and source_query in document.source_queries
                )
            ]

            if not choices:
                raise ValueError(
                    "Unable to satisfy "
                    "source-query coverage for "
                    f"{source_query!r}; "
                    f"minimum={minimum}."
                )

            chosen = choices[0]

            selected_ids.add(chosen.document_id)

            selection_reasons[chosen.document_id] = (
                f"selected to satisfy source-query coverage: {source_query}"
            )

    if len(selected_ids) > config.target_document_count:
        raise ValueError("Source-query minimums require more documents than target_document_count.")

    for document in eligible:
        if len(selected_ids) >= config.target_document_count:
            break

        if document.document_id in selected_ids:
            continue

        selected_ids.add(document.document_id)

        selection_reasons[document.document_id] = "selected by deterministic quality-ranking fill"

    if len(selected_ids) != config.target_document_count:
        raise RuntimeError("Source selection did not produce the configured target document count.")

    decisions: list[SourceDocumentSelection] = []

    for document in sorted(
        candidate_documents,
        key=lambda value: value.document_id,
    ):
        document_id = document.document_id

        if document_id in duplicate_excluded_ids:
            status: SelectionStatus = "duplicate_excluded"

            representative_id = representative_by_excluded[document_id]

            reason = (
                "excluded as an exact-title "
                "duplicate; richer deterministic "
                "representative is "
                f"{representative_id}"
            )

        elif document_id in selected_ids:
            status = "selected"

            representative_id = None

            reason = selection_reasons[document_id]

        else:
            status = "not_selected"

            representative_id = None

            if document.chunk_count < config.minimum_chunks_per_document:
                reason = "not selected because chunk_count is below minimum_chunks_per_document"

            else:
                reason = (
                    "eligible but outside the "
                    "frozen target after coverage "
                    "and deterministic ranking"
                )

        decisions.append(
            SourceDocumentSelection(
                document_id=(document.document_id),
                title=document.title,
                chunk_count=(document.chunk_count),
                source_queries=(document.source_queries),
                sti_type=(document.sti_type),
                subject_categories=(document.subject_categories),
                status=status,
                reason=reason,
                duplicate_family_id=(family_by_document.get(document_id)),
                representative_document_id=(representative_id),
            )
        )

    selected_documents = [document for document in decisions if document.status == "selected"]

    query_counts = _source_query_counts(selected_documents)

    for (
        query,
        minimum,
    ) in config.source_query_minimums.items():
        observed = query_counts.get(
            query,
            0,
        )

        if observed < minimum:
            raise RuntimeError(
                "Frozen selection failed "
                "source-query coverage: "
                f"{query!r} expected "
                f">={minimum}, observed "
                f"{observed}."
            )

    duplicate_count = len(duplicate_excluded_ids)

    not_selected_count = len(candidate_documents) - len(selected_documents) - duplicate_count

    return LoRASourceSelectionManifest(
        version=config.version,
        corpus_version=(config.corpus_version),
        corpus_chunks_path=(corpus_chunks_path),
        metadata_manifest_path=(metadata_manifest_path),
        protected_manifest_path=(protected_manifest_path),
        protected_manifest_sha256=(protected_manifest_sha256),
        selection_config_path=(selection_config_path),
        selection_config_sha256=(selection_config_sha256),
        corpus_document_count=(corpus_document_count),
        protected_document_count=(protected_document_count),
        candidate_document_count=len(candidate_documents),
        candidate_chunk_count=(candidate_chunk_count),
        deduplicated_candidate_count=(len(candidate_documents) - duplicate_count),
        selected_document_count=len(selected_documents),
        selected_chunk_count=sum(document.chunk_count for document in selected_documents),
        duplicate_excluded_document_count=(duplicate_count),
        not_selected_document_count=(not_selected_count),
        protected_overlap_count=0,
        selected_document_ids=sorted(selected_ids),
        source_query_selected_counts=(query_counts),
        documents=decisions,
    )


def normalize_source_title(
    title: str,
) -> str:
    """Normalize a title for deterministic duplicate-family detection."""

    without_tags = re.sub(
        r"<[^>]+>",
        "",
        title,
    )

    decoded = html.unescape(without_tags)

    return " ".join(decoded.casefold().split())


def sha256_file(
    path: Path,
) -> str:
    """Calculate a file SHA-256 digest."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _duplicate_family_id(
    normalized_title: str,
) -> str:
    """Return a compact deterministic title-family identifier."""

    digest = hashlib.sha256(normalized_title.encode("utf-8")).hexdigest()

    return "title-" + digest[:12]


def _document_rank(
    document: SourceDocumentMetadata,
    *,
    type_rank: dict[str, int],
) -> tuple[int, int, int]:
    """Rank richer documents first with deterministic tie-breaking."""

    fallback_type_rank = len(type_rank) + 1

    return (
        -document.chunk_count,
        type_rank.get(
            document.sti_type,
            fallback_type_rank,
        ),
        document.document_id,
    )


def _selected_query_count(
    documents: Sequence[SourceDocumentMetadata],
    *,
    selected_ids: set[int],
    source_query: str,
) -> int:
    """Count selected documents associated with one source query."""

    return sum(
        1
        for document in documents
        if (document.document_id in selected_ids and source_query in document.source_queries)
    )


def _source_query_counts(
    documents: Sequence[SourceDocumentSelection],
) -> dict[str, int]:
    """Count selected documents associated with each source query."""

    queries = sorted({query for document in documents for query in document.source_queries})

    return {
        query: sum(1 for document in documents if query in document.source_queries)
        for query in queries
    }
