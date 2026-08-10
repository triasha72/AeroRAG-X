#!/usr/bin/env python3
"""Build the frozen evidence plan for AeroRAG-X LoRA dataset generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.retrieval.bm25 import (
    load_chunk_records,
)
from aeroragx.training.planning import (
    LoRAExamplePlanManifest,
    build_example_plan,
    load_example_plan_config,
    write_example_plan_manifest,
)
from aeroragx.training.protected import (
    load_protected_document_manifest,
)
from aeroragx.training.selection import (
    load_source_selection_manifest,
    sha256_file,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic 120-example "
            "evidence plan from the frozen clean "
            "LoRA source-document selection."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/training/dataset_plan_v0_1.yaml"),
    )

    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    )

    parser.add_argument(
        "--source-selection",
        type=Path,
        default=Path("data/training/manifests/source_documents_v0_1.json"),
    )

    parser.add_argument(
        "--protected-manifest",
        type=Path,
        default=Path("data/evaluation/generation_v0_3_protected_documents.json"),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/training/manifests/example_plan_v0_1.json"),
    )

    return parser.parse_args()


def main() -> int:
    """Build, validate, and write the frozen example plan."""

    args = parse_args()

    config = load_example_plan_config(args.config)

    source_selection = load_source_selection_manifest(args.source_selection)

    protected_manifest = load_protected_document_manifest(args.protected_manifest)

    chunks = load_chunk_records(args.chunks)

    manifest = build_example_plan(
        chunks,
        source_selection=(source_selection),
        protected_document_ids=(protected_manifest.protected_document_id_set),
        config=config,
        corpus_chunks_path=str(args.chunks),
        corpus_chunks_sha256=(sha256_file(args.chunks)),
        source_selection_manifest_path=str(args.source_selection),
        source_selection_manifest_sha256=(sha256_file(args.source_selection)),
        protected_manifest_path=str(args.protected_manifest),
        protected_manifest_sha256=(sha256_file(args.protected_manifest)),
        plan_config_path=str(args.config),
        plan_config_sha256=(sha256_file(args.config)),
    )

    write_example_plan_manifest(
        args.output,
        manifest,
    )

    _print_summary(manifest)

    print()
    print(
        "Manifest:",
        args.output,
    )

    return 0


def _print_summary(
    manifest: LoRAExamplePlanManifest,
) -> None:
    """Print the frozen example-plan summary."""

    print()
    print("=== LORA EXAMPLE PLAN ===")

    print(
        "Selected documents:",
        manifest.selected_document_count,
    )

    print(
        "Selected source chunks:",
        manifest.selected_source_chunk_count,
    )

    print(
        "Ordinary:",
        manifest.ordinary_example_count,
    )

    print(
        "Synthesis:",
        manifest.synthesis_example_count,
    )

    print(
        "Refusal:",
        manifest.refusal_example_count,
    )

    print(
        "Total:",
        manifest.planned_example_count,
    )

    print(
        "Unique planned chunks:",
        manifest.unique_planned_chunk_count,
    )

    print(
        "Protected overlap:",
        manifest.protected_overlap_count,
    )

    print()
    print("=== PER-DOCUMENT ALLOCATION ===")

    for document in manifest.documents:
        print()
        print(
            document.document_id,
            "|",
            document.title,
        )

        print(
            "  available chunks:",
            document.available_chunk_count,
        )

        print(
            "  eligible chunks:",
            document.eligible_chunk_count,
        )

        print(
            "  ordinary:",
            document.ordinary_count,
        )

        print(
            "  synthesis:",
            document.synthesis_count,
        )

        print(
            "  refusal:",
            document.refusal_count,
        )

        print(
            "  total:",
            document.total_count,
        )


if __name__ == "__main__":
    raise SystemExit(main())
