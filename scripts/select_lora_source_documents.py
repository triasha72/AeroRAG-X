#!/usr/bin/env python3
"""Freeze the clean NASA source-document set used for LoRA data construction."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from aeroragx.retrieval.bm25 import (
    load_chunk_records,
)
from aeroragx.training.protected import (
    load_protected_document_manifest,
)
from aeroragx.training.selection import (
    SourceDocumentMetadata,
    load_source_selection_config,
    select_source_documents,
    sha256_file,
    write_source_selection_manifest,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Select and freeze a deterministic, "
            "document-disjoint NASA source set "
            "for AeroRAG-X LoRA training data."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/training/source_selection_v0_1.yaml"),
    )

    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/manifests/ntrs_v0_1.jsonl"),
    )

    parser.add_argument(
        "--protected-manifest",
        type=Path,
        default=Path("data/evaluation/generation_v0_3_protected_documents.json"),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/training/manifests/source_documents_v0_1.json"),
    )

    return parser.parse_args()


def main() -> int:
    """Build and write the frozen LoRA source selection."""

    args = parse_args()

    config = load_source_selection_config(args.config)

    protected_manifest = load_protected_document_manifest(args.protected_manifest)

    chunks = load_chunk_records(args.chunks)

    chunk_counts = Counter(chunk.document_id for chunk in chunks)

    corpus_document_ids = set(chunk_counts)

    protected_document_ids = protected_manifest.protected_document_id_set

    unknown_protected = protected_document_ids - corpus_document_ids

    if unknown_protected:
        raise RuntimeError(
            "Protected manifest references "
            "documents absent from the processed corpus: "
            + ", ".join(str(document_id) for document_id in sorted(unknown_protected))
        )

    candidate_document_ids = sorted(corpus_document_ids - protected_document_ids)

    candidate_chunk_count = sum(chunk_counts[document_id] for document_id in candidate_document_ids)

    metadata_by_id = _load_metadata(args.metadata)

    missing_metadata = [
        document_id for document_id in candidate_document_ids if document_id not in metadata_by_id
    ]

    if missing_metadata:
        raise RuntimeError(
            "Candidate documents are missing "
            "metadata records: " + ", ".join(str(document_id) for document_id in missing_metadata)
        )

    candidates: list[SourceDocumentMetadata] = []

    for document_id in candidate_document_ids:
        metadata = metadata_by_id[document_id]

        candidates.append(
            SourceDocumentMetadata(
                document_id=(document_id),
                title=(
                    _required_string(
                        metadata,
                        "title",
                        document_id=(document_id),
                    )
                ),
                chunk_count=(chunk_counts[document_id]),
                source_queries=(
                    _string_list(
                        metadata.get("source_queries"),
                        field_name=("source_queries"),
                        document_id=(document_id),
                    )
                ),
                sti_type=(
                    _optional_string(
                        metadata.get("sti_type"),
                        fallback=("UNKNOWN"),
                    )
                ),
                subject_categories=(
                    _string_list(
                        metadata.get("subject_categories"),
                        field_name=("subject_categories"),
                        document_id=(document_id),
                    )
                ),
            )
        )

    manifest = select_source_documents(
        candidates,
        protected_document_ids=(protected_document_ids),
        config=config,
        corpus_document_count=(len(corpus_document_ids)),
        protected_document_count=(len(protected_document_ids)),
        candidate_chunk_count=(candidate_chunk_count),
        corpus_chunks_path=str(args.chunks),
        metadata_manifest_path=str(args.metadata),
        protected_manifest_path=str(args.protected_manifest),
        protected_manifest_sha256=(sha256_file(args.protected_manifest)),
        selection_config_path=str(args.config),
        selection_config_sha256=(sha256_file(args.config)),
    )

    write_source_selection_manifest(
        args.output,
        manifest,
    )

    _print_summary(manifest)

    return 0


def _load_metadata(
    path: Path,
) -> dict[int, dict[str, Any]]:
    """Load NASA metadata JSONL keyed by document ID."""

    records: dict[
        int,
        dict[str, Any],
    ] = {}

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        try:
            raw_value = json.loads(line)

        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid metadata JSON on line {line_number} of {path}.") from exc

        if not isinstance(
            raw_value,
            dict,
        ):
            raise ValueError(f"Metadata line {line_number} of {path} must contain a JSON object.")

        document_id_value = raw_value.get("document_id")

        if not isinstance(
            document_id_value,
            int,
        ):
            raise ValueError(f"Metadata line {line_number} of {path} has invalid document_id.")

        if document_id_value in records:
            raise ValueError(f"Duplicate metadata record for document {document_id_value}.")

        records[document_id_value] = raw_value

    return records


def _required_string(
    row: dict[str, Any],
    key: str,
    *,
    document_id: int,
) -> str:
    """Read a required nonblank metadata string."""

    value = row.get(key)

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(f"Document {document_id} has invalid {key}.")

    cleaned = value.strip()

    if not cleaned:
        raise ValueError(f"Document {document_id} has blank {key}.")

    return cleaned


def _optional_string(
    value: object,
    *,
    fallback: str,
) -> str:
    """Read an optional metadata string."""

    if value is None:
        return fallback

    if not isinstance(
        value,
        str,
    ):
        raise ValueError("Optional metadata string has invalid type.")

    cleaned = value.strip()

    return cleaned if cleaned else fallback


def _string_list(
    value: object,
    *,
    field_name: str,
    document_id: int,
) -> list[str]:
    """Validate one metadata string-list field."""

    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(f"Document {document_id} field {field_name} must be a list.")

    cleaned: list[str] = []

    for item in value:
        if not isinstance(
            item,
            str,
        ):
            raise ValueError(
                f"Document {document_id} field {field_name} contains a non-string value."
            )

        stripped = item.strip()

        if stripped:
            cleaned.append(stripped)

    return list(dict.fromkeys(cleaned))


def _print_summary(
    manifest: object,
) -> None:
    """Print frozen source-selection results."""

    from aeroragx.training.selection import (
        LoRASourceSelectionManifest,
    )

    if not isinstance(
        manifest,
        LoRASourceSelectionManifest,
    ):
        raise TypeError("Unexpected source-selection manifest type.")

    print()
    print("=== LORA SOURCE SELECTION ===")

    print(
        "Corpus documents:",
        manifest.corpus_document_count,
    )

    print(
        "Protected documents:",
        manifest.protected_document_count,
    )

    print(
        "Candidate documents:",
        manifest.candidate_document_count,
    )

    print(
        "Candidate chunks:",
        manifest.candidate_chunk_count,
    )

    print(
        "Deduplicated candidates:",
        manifest.deduplicated_candidate_count,
    )

    print(
        "Selected documents:",
        manifest.selected_document_count,
    )

    print(
        "Selected chunks:",
        manifest.selected_chunk_count,
    )

    print(
        "Duplicate exclusions:",
        manifest.duplicate_excluded_document_count,
    )

    print(
        "Not selected:",
        manifest.not_selected_document_count,
    )

    print(
        "Protected overlap:",
        manifest.protected_overlap_count,
    )

    print()

    print("=== SOURCE-QUERY COVERAGE ===")

    for query, count in manifest.source_query_selected_counts.items():
        print(
            query,
            "->",
            count,
        )

    print()

    print("=== SELECTED DOCUMENTS ===")

    for document in manifest.documents:
        if document.status != "selected":
            continue

        print(
            document.document_id,
            "| chunks=",
            document.chunk_count,
            "|",
            document.title,
        )

    print()

    print("=== DUPLICATE EXCLUSIONS ===")

    duplicate_count = 0

    for document in manifest.documents:
        if document.status != "duplicate_excluded":
            continue

        duplicate_count += 1

        print(
            document.document_id,
            "-> representative",
            document.representative_document_id,
            "|",
            document.title,
        )

    if duplicate_count == 0:
        print("No exact-title duplicate families were detected.")

    print()

    print("Manifest written successfully.")


if __name__ == "__main__":
    raise SystemExit(main())
