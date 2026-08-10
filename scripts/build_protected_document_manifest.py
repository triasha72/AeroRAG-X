#!/usr/bin/env python3
"""Rebuild the frozen generation-v0.3 protected document/chunk manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
)
from aeroragx.generation.facet_retrieval import (
    FacetAwareEvidenceIndex,
    load_facet_retrieval_config,
)
from aeroragx.runtime import (
    RuntimeConfig,
    load_reranker_index,
)
from aeroragx.training.protected import (
    ProtectedDocumentManifest,
    ProtectedQueryEvidence,
    write_protected_document_manifest,
)

_DEFAULT_QUERY_COUNT = 32

_DEFAULT_PROTECTED_DOCUMENT_COUNT = 45

_DEFAULT_PROTECTED_CHUNK_COUNT = 111


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct every source "
            "document and chunk retrieved "
            "into the frozen AeroRAG-X "
            "generation-v0.3 evidence context."
        )
    )

    parser.add_argument(
        "--queries-input",
        type=Path,
        default=Path("data/evaluation/generation_queries_v0_3.jsonl"),
    )

    parser.add_argument(
        "--facet-retrieval-config",
        type=Path,
        default=Path("configs/facet_retrieval_v0_1.yaml"),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/generation_v0_3_protected_documents.json"),
    )

    parser.add_argument(
        "--candidate-top-k",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--evidence-top-k",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--expected-query-count",
        type=int,
        default=(_DEFAULT_QUERY_COUNT),
    )

    parser.add_argument(
        "--expected-protected-document-count",
        type=int,
        default=(_DEFAULT_PROTECTED_DOCUMENT_COUNT),
    )

    parser.add_argument(
        "--expected-protected-chunk-count",
        type=int,
        default=(_DEFAULT_PROTECTED_CHUNK_COUNT),
    )

    return parser.parse_args()


def main() -> int:
    """Rebuild and validate the frozen protected-evidence boundary."""

    args = parse_args()

    if args.candidate_top_k < 1:
        raise ValueError("--candidate-top-k must be at least 1.")

    if args.evidence_top_k < 1:
        raise ValueError("--evidence-top-k must be at least 1.")

    if args.evidence_top_k > args.candidate_top_k:
        raise ValueError("--evidence-top-k must not exceed --candidate-top-k.")

    queries = load_generation_evaluation_queries(args.queries_input)

    query_ids = [query.query_id for query in queries]

    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Protected evaluation query IDs must be unique.")

    runtime_config = RuntimeConfig(
        dense_backend="numpy",
        candidate_top_k=(args.candidate_top_k),
        evidence_top_k=(args.evidence_top_k),
    )

    (
        reranker_index,
        reranker_settings,
    ) = load_reranker_index(runtime_config)

    facet_index = FacetAwareEvidenceIndex(
        reranker_index,
        load_facet_retrieval_config(args.facet_retrieval_config),
    )

    protected_queries: list[ProtectedQueryEvidence] = []

    all_document_ids: set[int] = set()

    all_chunk_ids: set[str] = set()

    print()

    print("=== PROTECTED BENCHMARK EVIDENCE RECONSTRUCTION ===")

    print()

    print(
        "Queries:",
        len(queries),
    )

    print("Dense backend: numpy")

    print(
        "Reranker:",
        reranker_settings.model_name,
    )

    print(
        "Candidate top-k:",
        args.candidate_top_k,
    )

    print(
        "Evidence top-k:",
        args.evidence_top_k,
    )

    print()

    for query in queries:
        hits = list(
            facet_index.search(
                query.query,
                top_k=(args.evidence_top_k),
            )
        )

        if len(hits) != (args.evidence_top_k):
            raise RuntimeError(
                f"{query.query_id}: "
                f"expected "
                f"{args.evidence_top_k} "
                f"evidence hits but "
                f"received {len(hits)}."
            )

        chunk_ids = [hit.chunk.chunk_id for hit in hits]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise RuntimeError(
                f"{query.query_id}: duplicate chunks appeared in protected evidence."
            )

        document_ids = sorted({hit.chunk.document_id for hit in hits})

        protected_queries.append(
            ProtectedQueryEvidence(
                query_id=(query.query_id),
                expected_answerable=(query.expected_answerable),
                document_ids=(document_ids),
                chunk_ids=(chunk_ids),
            )
        )

        all_document_ids.update(document_ids)

        all_chunk_ids.update(chunk_ids)

        print(
            query.query_id,
            "| answerable=",
            query.expected_answerable,
            "| docs=",
            document_ids,
            "| chunks=",
            len(chunk_ids),
        )

    manifest = ProtectedDocumentManifest(
        version="0.1",
        purpose=(
            "Protect every source "
            "document and chunk retrieved "
            "into the frozen generation "
            "v0.3 benchmark evidence context."
        ),
        source_evaluation=str(args.queries_input),
        dense_backend="numpy",
        candidate_top_k=(args.candidate_top_k),
        evidence_top_k=(args.evidence_top_k),
        query_count=len(protected_queries),
        protected_document_count=len(all_document_ids),
        protected_chunk_count=len(all_chunk_ids),
        protected_document_ids=sorted(all_document_ids),
        protected_chunk_ids=sorted(all_chunk_ids),
        queries=(protected_queries),
    )

    _assert_expected_counts(
        manifest,
        expected_query_count=(args.expected_query_count),
        expected_document_count=(args.expected_protected_document_count),
        expected_chunk_count=(args.expected_protected_chunk_count),
    )

    write_protected_document_manifest(
        args.output,
        manifest,
    )

    print()

    print("=== SUMMARY ===")

    print(
        "Queries:",
        manifest.query_count,
    )

    print(
        "Protected documents:",
        manifest.protected_document_count,
    )

    print(
        "Protected chunks:",
        manifest.protected_chunk_count,
    )

    print(
        "Manifest:",
        args.output,
    )

    return 0


def _assert_expected_counts(
    manifest: ProtectedDocumentManifest,
    *,
    expected_query_count: int,
    expected_document_count: int,
    expected_chunk_count: int,
) -> None:
    """Fail if the frozen evidence boundary changes unexpectedly."""

    observed = (
        manifest.query_count,
        manifest.protected_document_count,
        manifest.protected_chunk_count,
    )

    expected = (
        expected_query_count,
        expected_document_count,
        expected_chunk_count,
    )

    if observed == expected:
        return

    raise RuntimeError(
        "Frozen protected-evidence "
        "counts changed. "
        "Expected "
        "queries/documents/chunks="
        f"{expected}, observed={observed}. "
        "Review retrieval changes before "
        "accepting a new protected boundary."
    )


if __name__ == "__main__":
    raise SystemExit(main())
