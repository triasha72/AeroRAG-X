#!/usr/bin/env python3
"""Run the frozen AeroRAG-X runtime on a collaborator-owned question set."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.evaluation.external import (
    load_external_questions,
    run_external_questions,
    write_external_run,
)
from aeroragx.runtime import RuntimeConfig, load_grounded_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--system-version", required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--chunks-input", type=Path, default=Path("data/processed/ntrs/v0_1/chunks.jsonl"))
    parser.add_argument("--embeddings-input", type=Path, default=Path("artifacts/embeddings/ntrs_v0_1.npy"))
    parser.add_argument("--metadata-input", type=Path, default=Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"))
    parser.add_argument("--manifest-input", type=Path, default=Path("artifacts/embeddings/ntrs_v0_1_manifest.json"))
    parser.add_argument("--generation-config", type=Path, default=Path("configs/generation_v0_1.yaml"))
    parser.add_argument("--sufficiency-config", type=Path, default=Path("configs/sufficiency_v0_2_1.yaml"))
    parser.add_argument("--provider-config", type=Path)
    parser.add_argument("--http-transport-config", type=Path)
    parser.add_argument("--provider-runtime-config", type=Path)
    parser.add_argument("--candidate-top-k", type=int)
    parser.add_argument("--evidence-top-k", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    questions = load_external_questions(args.questions)
    runtime = load_grounded_runtime(
        RuntimeConfig(
            chunks_input=args.chunks_input,
            embeddings_input=args.embeddings_input,
            metadata_input=args.metadata_input,
            manifest_input=args.manifest_input,
            generation_config=args.generation_config,
            sufficiency_config=args.sufficiency_config,
            provider_config=args.provider_config,
            http_transport_config=args.http_transport_config,
            provider_runtime_config=args.provider_runtime_config,
            candidate_top_k=args.candidate_top_k,
            evidence_top_k=args.evidence_top_k,
        )
    )
    records = run_external_questions(
        generator=runtime.generator,
        questions=questions,
        reranker_model=runtime.reranker_settings.model_name,
    )
    input_files = {
        "questions": args.questions,
        "chunks": args.chunks_input,
        "embedding_manifest": args.manifest_input,
        "bm25_config": Path("configs/bm25_v0_1.yaml"),
        "dense_config": Path("configs/dense_v0_1.yaml"),
        "hybrid_config": Path("configs/hybrid_v0_1.yaml"),
        "reranker_config": Path("configs/reranker_v0_1.yaml"),
        "generation_config": args.generation_config,
        "sufficiency_config": args.sufficiency_config,
    }
    if args.provider_config is not None:
        input_files["provider_config"] = args.provider_config
    if args.http_transport_config is not None:
        input_files["http_transport_config"] = args.http_transport_config
    if args.provider_runtime_config is not None:
        input_files["provider_runtime_config"] = args.provider_runtime_config
    for name, path in input_files.items():
        if not path.is_file():
            raise ValueError(f"Frozen input {name} is not a file: {path}")
    write_external_run(
        output_dir=args.output_dir,
        records=records,
        system_version=args.system_version,
        git_commit=args.git_commit,
        input_files=input_files,
    )


if __name__ == "__main__":
    main()
