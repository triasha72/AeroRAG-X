#!/usr/bin/env python3
"""Capture full grounded answers for claim-support evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.generation.evaluation import (
    load_generation_evaluation_queries,
)
from aeroragx.retrieval.bm25 import load_chunk_records
from aeroragx.runtime import RuntimeConfig, load_grounded_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the protected answerable-query benchmark and "
            "persist complete grounded claim/citation payloads."
        )
    )

    parser.add_argument(
        "--system",
        choices=("base_rag", "lora_rag"),
        required=True,
    )

    parser.add_argument(
        "--queries-input",
        type=Path,
        default=Path("data/evaluation/generation_queries_claim_support_v0_1.jsonl"),
    )

    parser.add_argument(
        "--chunks-input",
        type=Path,
        default=Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    )

    parser.add_argument(
        "--generation-config",
        type=Path,
        default=Path("configs/generation_transformers_v0_1.yaml"),
    )

    parser.add_argument(
        "--sufficiency-config",
        type=Path,
        default=Path("configs/sufficiency_v0_2_1.yaml"),
    )

    parser.add_argument(
        "--facet-retrieval-config",
        type=Path,
        default=Path("configs/facet_retrieval_v0_1.yaml"),
    )

    parser.add_argument(
        "--provider-runtime-config",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--reference-report",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
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
        "--require-reference-match",
        action="store_true",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    queries = load_generation_evaluation_queries(args.queries_input)

    if len(queries) != 20:
        raise RuntimeError("Claim-support benchmark must contain 20 queries.")

    if any(not query.expected_answerable for query in queries):
        raise RuntimeError("Claim-support capture must contain only answerable queries.")

    chunks = load_chunk_records(args.chunks_input)

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}

    if len(chunks_by_id) != len(chunks):
        raise RuntimeError("Corpus contains duplicate chunk IDs.")

    reference_report = json.loads(args.reference_report.read_text(encoding="utf-8"))

    reference_rows = {
        row["query_id"]: row
        for row in reference_report["query_results"]
        if row["expected_answerable"]
    }

    expected_query_ids = {query.query_id for query in queries}

    if set(reference_rows) != expected_query_ids:
        raise RuntimeError("Reference report answerable-query IDs do not match capture queries.")

    runtime = load_grounded_runtime(
        RuntimeConfig(
            chunks_input=args.chunks_input,
            generation_config=args.generation_config,
            sufficiency_config=args.sufficiency_config,
            facet_retrieval_config=(args.facet_retrieval_config),
            provider_runtime_config=(args.provider_runtime_config),
            candidate_top_k=(args.candidate_top_k),
            evidence_top_k=(args.evidence_top_k),
        )
    )

    query_results = []

    total_claim_count = 0
    total_citation_count = 0
    total_citation_reference_count = 0

    exact_answer_matches = 0
    claim_count_matches = 0
    citation_count_matches = 0
    source_document_count_matches = 0

    for index, query in enumerate(
        queries,
        start=1,
    ):
        print(f"[{index:02d}/{len(queries):02d}] {query.query_id}")

        answer = runtime.generator.generate(
            query.query,
            reranker_model=(runtime.reranker_settings.model_name),
        )

        reference = reference_rows[query.query_id]

        answer_matches_reference = answer.answer == reference["answer"]

        claim_count_matches_reference = len(answer.claims) == reference["claim_count"]

        citation_count_matches_reference = len(answer.citations) == reference["citation_count"]

        source_document_count_matches_reference = (
            len(answer.source_documents) == reference["source_document_count"]
        )

        exact_answer_matches += int(answer_matches_reference)

        claim_count_matches += int(claim_count_matches_reference)

        citation_count_matches += int(citation_count_matches_reference)

        source_document_count_matches += int(source_document_count_matches_reference)

        citation_payloads = []

        for citation in answer.citations:
            chunk = chunks_by_id.get(citation.chunk_id)

            if chunk is None:
                raise RuntimeError(
                    f"Citation chunk was not found in the frozen corpus: {citation.chunk_id}"
                )

            if chunk.document_id != citation.document_id:
                raise RuntimeError("Citation document ID does not match corpus provenance.")

            if chunk.document_sha256 != citation.document_sha256:
                raise RuntimeError("Citation document hash does not match corpus provenance.")

            payload = citation.model_dump(mode="json")

            payload["evidence_text"] = chunk.text

            citation_payloads.append(payload)

        claim_payloads = [claim.model_dump(mode="json") for claim in answer.claims]

        citation_reference_count = sum(len(claim.citation_ids) for claim in answer.claims)

        total_claim_count += len(answer.claims)

        total_citation_count += len(answer.citations)

        total_citation_reference_count += citation_reference_count

        query_results.append(
            {
                "query_id": (query.query_id),
                "query": query.query,
                "answer": answer.answer,
                "insufficient_evidence": (answer.insufficient_evidence),
                "answer_matches_reference": (answer_matches_reference),
                "claim_count_matches_reference": (claim_count_matches_reference),
                "citation_count_matches_reference": (citation_count_matches_reference),
                "source_document_count_matches_reference": (
                    source_document_count_matches_reference
                ),
                "reference_claim_count": (reference["claim_count"]),
                "reference_citation_count": (reference["citation_count"]),
                "claims": claim_payloads,
                "citations": (citation_payloads),
                "source_documents": [
                    item.model_dump(mode="json") for item in answer.source_documents
                ],
            }
        )

    query_count = len(queries)

    aggregate_counts_match = (
        total_claim_count == reference_report["total_claim_count"]
        and total_citation_count == reference_report["citation_count"]
        and total_citation_reference_count == reference_report["total_citation_reference_count"]
    )

    reference_alignment_pass = (
        exact_answer_matches == query_count
        and claim_count_matches == query_count
        and citation_count_matches == query_count
        and source_document_count_matches == query_count
        and aggregate_counts_match
    )

    report = {
        "version": "0.1",
        "capture_kind": ("claim_support_recapture"),
        "system": args.system,
        "query_count": query_count,
        "generation_provider": (runtime.generation_settings.provider),
        "generation_model": (runtime.generation_settings.model_name),
        "reranker_model": (runtime.reranker_settings.model_name),
        "source_reference_report": str(args.reference_report),
        "chunks_input": str(args.chunks_input),
        "summary": {
            "total_claim_count": (total_claim_count),
            "total_citation_count": (total_citation_count),
            "total_citation_reference_count": (total_citation_reference_count),
            "exact_answer_match_count": (exact_answer_matches),
            "claim_count_match_count": (claim_count_matches),
            "citation_count_match_count": (citation_count_matches),
            "source_document_count_match_count": (source_document_count_matches),
            "aggregate_counts_match": (aggregate_counts_match),
            "reference_alignment_pass": (reference_alignment_pass),
        },
        "query_results": query_results,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "system:",
        args.system,
    )
    print(
        "queries:",
        query_count,
    )
    print(
        "claims:",
        total_claim_count,
    )
    print(
        "citations:",
        total_citation_count,
    )
    print(
        "citation references:",
        total_citation_reference_count,
    )
    print(
        "exact answer matches:",
        f"{exact_answer_matches}/{query_count}",
    )
    print(
        "claim-count matches:",
        f"{claim_count_matches}/{query_count}",
    )
    print(
        "citation-count matches:",
        f"{citation_count_matches}/{query_count}",
    )
    print(
        "aggregate counts match:",
        aggregate_counts_match,
    )
    print(
        "reference alignment:",
        ("PASS" if reference_alignment_pass else "FAIL"),
    )
    print(
        "output:",
        args.output,
    )

    if args.require_reference_match and not reference_alignment_pass:
        raise SystemExit("Claim capture differs from the frozen v0.3 reference.")


if __name__ == "__main__":
    main()
